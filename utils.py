import re
from datetime import date, datetime
from typing import Optional

try:  # better fuzzy matching when rapidfuzz is installed
    from rapidfuzz import fuzz

    def similarity(a: str, b: str) -> float:
        return float(fuzz.token_sort_ratio(a, b))
except Exception:  # fallback keeps the project dependency-light
    from difflib import SequenceMatcher

    def similarity(a: str, b: str) -> float:
        a = " ".join(sorted(a.split()))
        b = " ".join(sorted(b.split()))
        return 100.0 * SequenceMatcher(None, a, b).ratio()


_DATE_FORMATS = [
    "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%d/%m/%y", "%d-%m-%y", "%d.%m.%y",
    "%d %B %Y", "%d %b %Y", "%d %B, %Y", "%d %b, %Y", "%Y-%m-%d",
]


def parse_date(text: str) -> Optional[date]:
    """Parse common Indian certificate date formats (day first)."""
    if not text:
        return None
    t = re.sub(r"\s+", " ", text.strip())
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(t, fmt).date()
        except ValueError:
            continue
    return None


_TITLES = re.compile(r"\b(mr|mrs|ms|miss|dr|shri|smt|kumari|late|selvi|thiru)\b\.?", re.I)


def normalize_name(name: str) -> str:
    n = _TITLES.sub(" ", name or "")
    n = re.sub(r"[^A-Za-z ]", " ", n)
    return re.sub(r"\s+", " ", n).strip().upper()


# --- Verhoeff checksum (used by Aadhaar numbers) ---------------------------
_D = [[0,1,2,3,4,5,6,7,8,9],[1,2,3,4,0,6,7,8,9,5],[2,3,4,0,1,7,8,9,5,6],
      [3,4,0,1,2,8,9,5,6,7],[4,0,1,2,3,9,5,6,7,8],[5,9,8,7,6,0,4,3,2,1],
      [6,5,9,8,7,1,0,4,3,2],[7,6,5,9,8,2,1,0,4,3],[8,7,6,5,9,3,2,1,0,4],
      [9,8,7,6,5,4,3,2,1,0]]
_P = [[0,1,2,3,4,5,6,7,8,9],[1,5,7,6,2,8,3,0,9,4],[5,8,0,3,7,9,6,1,4,2],
      [8,9,1,6,0,4,3,5,2,7],[9,4,5,3,1,2,6,8,7,0],[4,2,8,6,5,7,3,9,0,1],
      [2,7,9,3,8,0,6,4,1,5],[7,0,4,6,9,1,3,2,5,8]]


def verhoeff_valid(number: str) -> bool:
    c = 0
    for i, ch in enumerate(reversed(number)):
        c = _D[c][_P[i % 8][int(ch)]]
    return c == 0


def mask_id(number: str) -> str:
    digits = re.sub(r"\D", "", number)
    return "XXXX XXXX " + digits[-4:] if len(digits) >= 4 else "XXXX"
