"""Step 5 - Reconcile: cross-document identity checks (names, parentage, DOB)."""
from itertools import combinations
from typing import List

from . import config
from .models import DocResult, Issue
from .utils import normalize_name, parse_date, similarity


def reconcile(docs: List[DocResult]) -> List[Issue]:
    issues: List[Issue] = []
    for a, b in combinations(docs, 2):
        for key, label in (("name", "Name"), ("father_name", "Father's name"), ("mother_name", "Mother's name")):
            if key in a.fields and key in b.fields:
                fa, fb = a.fields[key], b.fields[key]
                score = similarity(normalize_name(fa.value), normalize_name(fb.value))
                conf = min(fa.conf, fb.conf)
                if score >= config.NAME_MATCH_OK:
                    continue
                low = conf < config.MIN_FIELD_CONF
                if low:
                    sev, rescan = "warning", True
                    msg = (f"{label} may differ ('{fa.value}' vs '{fb.value}') but OCR confidence is low "
                           f"({conf:.0f}%). Re-scan before judging.")
                elif score >= config.NAME_MATCH_WARN:
                    sev, rescan = "warning", False
                    msg = f"{label} is a close but not exact match ({score:.0f}%): '{fa.value}' vs '{fb.value}'."
                else:
                    sev, rescan = "error", False
                    msg = f"{label} mismatch ({score:.0f}%): '{fa.value}' in {a.filename} vs '{fb.value}' in {b.filename}."
                issues.append(Issue(sev, f"{key.upper()}_MISMATCH", msg, key, f"{a.filename} / {b.filename}", conf, rescan))
        if "dob" in a.fields and "dob" in b.fields:
            da, db = parse_date(a.fields["dob"].value), parse_date(b.fields["dob"].value)
            conf = min(a.fields["dob"].conf, b.fields["dob"].conf)
            if da and db and da != db:
                if conf < config.MIN_FIELD_CONF:
                    issues.append(Issue("warning", "DOB_MISMATCH_LOWCONF",
                                        f"DOB differs ({da:%d-%m-%Y} vs {db:%d-%m-%Y}) but OCR confidence is low.",
                                        "dob", f"{a.filename} / {b.filename}", conf, True))
                else:
                    issues.append(Issue("error", "DOB_MISMATCH",
                                        f"Date of birth mismatch: {da:%d-%m-%Y} in {a.filename} vs "
                                        f"{db:%d-%m-%Y} in {b.filename}.", "dob", f"{a.filename} / {b.filename}", conf))
    return issues
