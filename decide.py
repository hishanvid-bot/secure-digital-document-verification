"""Step 6 - Decide: triage into VERIFIED / REVIEW REQUIRED / REQUEST RE-SCAN.
The officer always makes the final call; this only prioritises their attention."""
from typing import List, Tuple

from .models import Issue

VERIFIED = "VERIFIED"
REVIEW = "REVIEW REQUIRED"
RESCAN = "REQUEST RE-SCAN"


def triage(issues: List[Issue]) -> Tuple[str, str]:
    real = [i for i in issues if not i.rescan and i.severity in ("error", "warning")]
    rescans = [i for i in issues if i.rescan]
    errors = [i for i in real if i.severity == "error"]
    if errors:
        return REVIEW, f"{len(errors)} discrepancy(ies) need officer attention: " + "; ".join(e.message for e in errors[:3])
    if rescans:
        return RESCAN, "Scan quality is too low to judge some fields. Ask the applicant to re-upload."
    if real:
        return REVIEW, f"{len(real)} warning(s) to check: " + "; ".join(w.message for w in real[:3])
    return VERIFIED, "No major issues found. One-click approval."
