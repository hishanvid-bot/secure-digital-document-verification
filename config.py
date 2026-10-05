"""Central configuration: thresholds and optional per-institution templates."""

# --- OCR / image quality ---------------------------------------------------
MIN_DOC_OCR_CONF = 60.0      # mean OCR confidence below this -> RE-SCAN
MIN_FIELD_CONF = 55.0        # a field below this is "unreliable", never "fake"
MIN_BLUR_SCORE = 60.0        # variance of Laplacian; lower = blurrier

# --- Name / identity matching ---------------------------------------------
NAME_MATCH_OK = 90           # >= this similarity: same person
NAME_MATCH_WARN = 75         # between WARN and OK: REVIEW; below WARN: mismatch

# --- Plausibility ------------------------------------------------------------
MIN_AGE_YEARS = 10
MAX_AGE_YEARS = 100
PERCENT_TOLERANCE = 0.6      # allowed difference between printed and computed %

# --- Required fields per document type -------------------------------------
REQUIRED_FIELDS = {
    "marksheet": ["name", "dob", "reg_no", "total"],
    "degree": ["name", "institution"],
    "id": ["name", "dob"],
    "unknown": ["name"],
}

# --- Optional serial-number formats per institution (configurable templates)
# Key: lowercase keyword found in the institution line. Value: regex.
SERIAL_PATTERNS = {
    # "anna university": r"^[A-Z]{2}\d{6,8}$",
}

DB_PATH = "verification.db"
