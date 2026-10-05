"""Step 3b / Understand - map OCR lines to entities (name, DOB, totals, subjects...)."""
import re
from typing import Dict, List, Tuple

from .models import Field_, OcrLine
from .utils import mask_id

DATE = r"(\d{1,2}\s*[/\-.]\s*\d{1,2}\s*[/\-.]\s*\d{2,4}|\d{1,2}\s+[A-Za-z]{3,9},?\s+\d{4})"

PATTERNS = {
    "father_name": re.compile(r"(?:father|guardian)(?:'s|s)?\s*(?:name)?\s*[:\-]\s*(.+)$", re.I),
    "mother_name": re.compile(r"mother(?:'s|s)?\s*(?:name)?\s*[:\-]\s*(.+)$", re.I),
    "dob": re.compile(r"(?:date\s+of\s+birth|d\.?\s?o\.?\s?b\.?)\s*[:\-]?\s*" + DATE, re.I),
    "reg_no": re.compile(r"(?:reg(?:ister|istration)?\.?|roll|enrol+ment|hall\s*ticket)\s*"
                         r"(?:no\.?|number)?\s*[:\-]?\s*([A-Z0-9][A-Z0-9/\-]{4,})", re.I),
    "serial": re.compile(r"(?:certificate|serial|sl\.?)\s*(?:no\.?|number)\s*[:\-]?\s*"
                         r"([A-Z0-9][A-Z0-9/\-]{4,})", re.I),
    "issue_date": re.compile(r"(?:date\s+of\s+issue|issued\s+on|issue\s+date|dated?)\b\s*[:\-]?\s*" + DATE, re.I),
    "total": re.compile(r"(?:grand\s+)?total(?:\s+marks)?(?:\s+obtained)?\D{0,15}?(\d{1,4})\b", re.I),
    "percentage": re.compile(r"(?:percentage|per\s*cent|%)\D{0,10}(\d{1,3}(?:\.\d+)?)", re.I),
}
NAME_RE = re.compile(r"(?:candidate'?s?\s+|student'?s?\s+)?name(?:\s+of\s+(?:the\s+)?(?:candidate|student))?\s*[:\-]\s*(.+)$", re.I)
MAXMARKS_RE = re.compile(r"(?:out\s+of|max(?:imum)?(?:\s+marks)?)\s*[:\-]?\s*(\d{2,4})", re.I)
INSTITUTION_RE = re.compile(r"(university|college|board|institute|school|council)", re.I)
AADHAAR_RE = re.compile(r"\b(\d{4})\s?(\d{4})\s?(\d{4})\b")
SUBJECT_RE = re.compile(
    r"^\s*(?:\d+[.)]?\s+)?([A-Za-z][A-Za-z &/\-\.]{2,40}?)\s+(\d{1,3})(?:\s+(\d{1,3}))?\s*(?:[A-Z]{1,2}\+?)?\s*$")
SKIP_SUBJECT = re.compile(r"total|grand|percent|date|name|birth|reg|roll|serial|class|result|year|semester", re.I)

DOC_TYPE_KEYWORDS = {
    "marksheet": ["statement of marks", "marksheet", "mark sheet", "marks obtained", "grade card", "subject"],
    "degree": ["degree", "convocation", "hereby certif", "conferred", "diploma"],
    "id": ["aadhaar", "identity card", "id card", "passport", "driving licen", "permanent account"],
}


def classify(text: str) -> str:
    low = text.lower()
    scores = {t: sum(k in low for k in kws) for t, kws in DOC_TYPE_KEYWORDS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "unknown"


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip(" .:-_|")


def extract_fields(lines: List[OcrLine]) -> Tuple[Dict[str, Field_], list, str]:
    """Return (fields, subjects, doc_type)."""
    text = "\n".join(l.text for l in lines)
    doc_type = classify(text)
    fields: Dict[str, Field_] = {}

    def put(name, value, line):
        if name not in fields and value:
            fields[name] = Field_(name, _clean(value), line.conf, line.text)

    # institution: first matching line near the top
    for line in lines[:10]:
        if INSTITUTION_RE.search(line.text) and len(line.text) > 8:
            put("institution", line.text, line)
            break

    for line in lines:
        t = line.text
        low = t.lower()
        for key in ("father_name", "mother_name"):
            m = PATTERNS[key].search(t)
            if m:
                put(key, m.group(1), line)
        if not re.search(r"father|mother|guardian|school|institution|university|college", low):
            m = NAME_RE.search(t)
            if m:
                put("name", m.group(1), line)
        m = PATTERNS["dob"].search(t)
        if m:
            put("dob", m.group(1), line)
        if "birth" not in low:
            m = PATTERNS["issue_date"].search(t)
            if m:
                put("issue_date", m.group(1), line)
        m = PATTERNS["serial"].search(t)
        if m:
            put("serial", m.group(1).upper(), line)
        m = PATTERNS["reg_no"].search(t)
        if m and "serial" not in low and "certificate" not in low:
            put("reg_no", m.group(1).upper(), line)
        if "total" in low:
            m = PATTERNS["total"].search(t)
            if m:
                put("total", m.group(1), line)
                mm = MAXMARKS_RE.search(t)
                if mm:
                    put("max_total", mm.group(1), line)
        if "percent" in low or "%" in t:
            m = PATTERNS["percentage"].search(t)
            if m:
                put("percentage", m.group(1), line)
        m = AADHAAR_RE.search(t)
        if m and doc_type == "id":
            number = "".join(m.groups())
            f = Field_("id_number", number, line.conf, mask_id(number))  # source masked
            fields.setdefault("id_number", f)

    subjects = []
    for line in lines:
        if SKIP_SUBJECT.search(line.text):
            continue
        m = SUBJECT_RE.match(line.text)
        if m:
            marks = int(m.group(2))
            mx = int(m.group(3)) if m.group(3) and int(m.group(3)) >= marks else None
            subjects.append({"subject": _clean(m.group(1)), "marks": marks,
                             "max": mx, "conf": line.conf, "source": line.text})
    return fields, subjects, doc_type
