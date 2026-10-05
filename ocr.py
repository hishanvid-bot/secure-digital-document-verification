"""Step 3a - OCR with per-line confidence (Tesseract)."""
from typing import List, Tuple

import numpy as np
import pytesseract
from pytesseract import Output

from .models import OcrLine


def run_ocr(gray: np.ndarray, lang: str = "eng") -> Tuple[List[OcrLine], float]:
    """Return (lines, mean_confidence). Languages such as 'eng+tam+hin' work if
    the matching Tesseract traineddata files are installed."""
    data = pytesseract.image_to_data(gray, lang=lang, config="--oem 3 --psm 6",
                                     output_type=Output.DICT)
    groups = {}
    for i, word in enumerate(data["text"]):
        word = (word or "").strip()
        try:
            conf = float(data["conf"][i])
        except (ValueError, TypeError):
            conf = -1.0
        if not word or conf < 0:
            continue
        key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
        groups.setdefault(key, []).append((data["left"][i], word, conf))

    lines: List[OcrLine] = []
    for key in sorted(groups):
        words = sorted(groups[key])
        text = " ".join(w for _, w, _ in words)
        conf = sum(c for _, _, c in words) / len(words)
        lines.append(OcrLine(text=text, conf=round(conf, 1)))

    all_conf = [l.conf for l in lines]
    mean = round(sum(all_conf) / len(all_conf), 1) if all_conf else 0.0
    return lines, mean
