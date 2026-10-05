"""Step 4 - Validate: deterministic, explainable rules on a single document.

Design rule: if the evidence behind a finding has low OCR confidence, the finding is
downgraded to a *re-scan hint* (rescan=True). A bad scan is never branded a forgery.
"""
import re
from datetime import date
from typing import List, Optional

from . import config
from .models import DocResult, Issue
from .utils import parse_date, verhoeff_valid

SIGNATORY_RE = re.compile(r"controller|registrar|principal|vice[\s-]*chancellor|director|signature|signed", re.I)


def _issue(severity, code, message, field, doc, conf=None) -> Issue:
    """Downgrade to a re-scan hint when the supporting OCR confidence is low."""
    if conf is not None and conf < config.MIN_FIELD_CONF and severity in ("error", "warning"):
        return Issue("warning", code + "_LOWCONF",
                     f"Could not reliably check '{field}' (OCR confidence {conf:.0f}%). "
                     f"Original finding: {message} Please re-scan this part.",
                     field, doc, conf, rescan=True)
    return Issue(severity, code, message, field, doc, conf)


def validate_document(d: DocResult, today: Optional[date] = None) -> List[Issue]:
    today = today or date.today()
    issues: List[Issue] = []
    name = d.filename
    f = d.fields

    # --- scan quality ------------------------------------------------------
    if d.blur_score < config.MIN_BLUR_SCORE:
        issues.append(Issue("warning", "BLURRY", f"Image looks blurry (sharpness {d.blur_score:.0f}). "
                            "Please re-scan in good light.", "image", name, rescan=True))
    if d.ocr_conf < config.MIN_DOC_OCR_CONF:
        issues.append(Issue("warning", "LOW_OCR", f"Overall OCR confidence is only {d.ocr_conf:.0f}%.",
                            "document", name, d.ocr_conf, rescan=True))

    # --- required fields ---------------------------------------------------
    for req in config.REQUIRED_FIELDS.get(d.doc_type, config.REQUIRED_FIELDS["unknown"]):
        if req not in f:
            sev = "warning" if d.ocr_conf < config.MIN_DOC_OCR_CONF else "error"
            issues.append(Issue(sev, "MISSING_FIELD", f"Required field '{req}' was not found on this "
                                f"{d.doc_type}.", req, name, rescan=(sev == "warning")))

    # --- arithmetic: sum of subjects vs printed total ---------------------------
    if d.subjects and "total" in f:
        s = sum(x["marks"] for x in d.subjects)
        printed = int(f["total"].value)
        conf = min([f["total"].conf] + [x["conf"] for x in d.subjects])
        if s != printed:
            issues.append(_issue("error", "TOTAL_MISMATCH",
                                 f"Total mismatch: {s} \u2260 {printed} (sum of {len(d.subjects)} subject "
                                 f"marks vs printed total).", "total", name, conf))
        mx = f["max_total"].value if "max_total" in f else None
        if mx is None and all(x["max"] for x in d.subjects):
            mx = str(sum(x["max"] for x in d.subjects))
        if mx and "percentage" in f:
            computed = 100.0 * printed / int(mx)
            shown = float(f["percentage"].value)
            if abs(computed - shown) > config.PERCENT_TOLERANCE:
                issues.append(_issue("error", "PERCENT_MISMATCH",
                                     f"Percentage mismatch: printed {shown:.2f}% but {printed}/{mx} = "
                                     f"{computed:.2f}%.", "percentage", name,
                                     min(conf, f["percentage"].conf)))

    # --- dates -----------------------------------------------------------------
    dob = parse_date(f["dob"].value) if "dob" in f else None
    if "dob" in f and dob is None:
        issues.append(_issue("warning", "DOB_UNREADABLE", f"Date of birth '{f['dob'].value}' could not be "
                             "parsed.", "dob", name, f["dob"].conf))
    if dob:
        age = (today - dob).days / 365.25
        if not (config.MIN_AGE_YEARS <= age <= config.MAX_AGE_YEARS):
            issues.append(_issue("error", "DOB_IMPLAUSIBLE", f"Date of birth {dob:%d-%m-%Y} gives an "
                                 f"implausible age ({age:.0f} years).", "dob", name, f["dob"].conf))
    issued = parse_date(f["issue_date"].value) if "issue_date" in f else None
    if issued:
        if issued > today:
            issues.append(_issue("error", "ISSUE_FUTURE", f"Issue date {issued:%d-%m-%Y} is in the future.",
                                 "issue_date", name, f["issue_date"].conf))
        if dob and issued < dob:
            issues.append(_issue("error", "ISSUE_BEFORE_DOB", "Issue date is earlier than the date of birth.",
                                 "issue_date", name, min(f["issue_date"].conf, f["dob"].conf)))

    # --- serial format (institution template) ------------------------------------
    if "serial" in f and "institution" in f:
        inst = f["institution"].value.lower()
        for key, pattern in config.SERIAL_PATTERNS.items():
            if key in inst and not re.match(pattern, f["serial"].value):
                issues.append(_issue("error", "SERIAL_FORMAT", f"Serial '{f['serial'].value}' does not match "
                                     f"the expected format for {key}.", "serial", name, f["serial"].conf))

    # --- seal / signatory (presence checks only) -----------------------------------
    if d.doc_type in ("marksheet", "degree"):
        if not d.seal_found:
            issues.append(Issue("warning", "NO_SEAL", "No seal-like circular stamp was detected. "
                                "Check the original or re-scan the stamp area.", "seal", name))
        if not SIGNATORY_RE.search(d.text):
            issues.append(Issue("info", "NO_SIGNATORY", "No signatory title (e.g. Controller/Registrar) "
                                "was read from the document.", "signatory", name))

    # --- ID checksum ---------------------------------------------------------------
    if "id_number" in f and len(f["id_number"].value) == 12:
        if not verhoeff_valid(f["id_number"].value):
            issues.append(_issue("error", "ID_CHECKSUM", "ID number fails its checksum (possible typo or "
                                 "tampering).", "id_number", name, f["id_number"].conf))
    return issues
