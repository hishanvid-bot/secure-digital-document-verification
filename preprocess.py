"""Step 2 - Preprocess: load pages, denoise, deskew, CLAHE contrast, quality metrics."""
from typing import List

import cv2
import numpy as np


def load_pages(filename: str, data: bytes) -> List[np.ndarray]:
    """Return a list of BGR images (one per PDF page, or a single image)."""
    if filename.lower().endswith(".pdf"):
        import fitz  # PyMuPDF - no poppler needed

        pages = []
        with fitz.open(stream=data, filetype="pdf") as pdf:
            for page in pdf:
                pix = page.get_pixmap(dpi=200)
                img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
                if pix.n == 4:
                    img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
                elif pix.n == 3:
                    img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
                else:
                    img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
                pages.append(img)
        return pages
    arr = np.frombuffer(data, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError(f"Could not decode image: {filename}")
    return [img]


def _resize_for_ocr(gray: np.ndarray, target_w: int = 1800) -> np.ndarray:
    h, w = gray.shape[:2]
    if w < target_w:
        scale = target_w / w
        return cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    return gray


def blur_score(gray: np.ndarray) -> float:
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def _rotate(img: np.ndarray, angle: float) -> np.ndarray:
    h, w = img.shape[:2]
    M = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    return cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_CUBIC,
                          borderMode=cv2.BORDER_REPLICATE)


def estimate_skew(gray: np.ndarray, max_angle: float = 10.0, step: float = 0.5) -> float:
    """Projection-profile method: the angle whose row-sums are 'sharpest' (text lines
    line up) is the correct one. More robust than minAreaRect when stamps/borders exist."""
    scale = 600 / max(gray.shape)
    small = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA) if scale < 1 else gray
    bw = cv2.threshold(cv2.bitwise_not(small), 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
    if cv2.countNonZero(bw) < 200:
        return 0.0
    best_angle, best_score = 0.0, -1.0
    for a in np.arange(-max_angle, max_angle + step, step):
        profile = _rotate(bw, a).sum(axis=1).astype(np.float64)
        score = float(np.sum(np.diff(profile) ** 2))
        if score > best_score:
            best_angle, best_score = float(a), score
    return best_angle


def deskew(gray: np.ndarray) -> np.ndarray:
    angle = estimate_skew(gray)
    return gray if abs(angle) < 0.4 else _rotate(gray, angle)


def preprocess(bgr: np.ndarray) -> np.ndarray:
    """Grayscale -> upscale -> denoise -> deskew -> CLAHE. Returns a clean gray image."""
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    gray = _resize_for_ocr(gray)
    # light denoise: strong settings smear thin strokes and hurt OCR on clean scans
    gray = cv2.fastNlMeansDenoising(gray, None, h=4, templateWindowSize=7, searchWindowSize=21)
    gray = deskew(gray)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return clahe.apply(gray)


def detect_seal(bgr: np.ndarray) -> bool:
    """Heuristic: look for a large circular stamp/seal (Hough circles).
    This only checks that a seal-like shape is *present*; it does not
    authenticate it - a human reviewer still decides."""
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    scale = 800 / max(h, w)
    small = cv2.resize(gray, None, fx=scale, fy=scale) if scale < 1 else gray
    small = cv2.medianBlur(small, 5)
    sh, sw = small.shape
    circles = cv2.HoughCircles(
        small, cv2.HOUGH_GRADIENT, dp=1.2, minDist=sh // 8,
        param1=120, param2=40, minRadius=int(min(sh, sw) * 0.04),
        maxRadius=int(min(sh, sw) * 0.2),
    )
    return circles is not None
