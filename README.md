# Secure Digital Document Verification

**Smart, explainable, human-assisted certificate verification** — idea submission by **HCUBE SQUAD**
(Harini S, Hishanvi D, Harini G).

Verifies marksheets, degree certificates and IDs from noisy phone scans. It does **not** just output a
"fake / genuine" score: every warning names the exact field, shows the evidence line, and a human
officer always makes the final decision.

```
Upload → Preprocess → Extract → Validate → Reconcile → Decide
```

| Stage | What happens | Code |
|---|---|---|
| 1 Upload | PDFs / camera images | `app.py` |
| 2 Preprocess | denoise, deskew, CLAHE contrast, blur score, seal detection (OpenCV) | `backend/preprocess.py` |
| 3 Extract | Tesseract OCR with per-line confidence, regex entity mapping | `backend/ocr.py`, `backend/extract.py` |
| 4 Validate | sum of marks, percentage, date plausibility, serial format, ID checksum, seal/signatory | `backend/validate.py` |
| 5 Reconcile | fuzzy match of name, parents' names, DOB across the whole packet | `backend/reconcile.py` |
| 6 Decide | triage + officer approve / flag / re-scan, full audit log (SQLite) | `backend/decide.py`, `backend/database.py` |

## Triage outcomes
- **VERIFIED** – no major issues; one-click approval
- **REVIEW REQUIRED** – discrepancies highlighted for the officer
- **REQUEST RE-SCAN** – low-confidence scan; applicant asked to re-upload

**Key design rule:** if the evidence behind a finding has low OCR confidence, it becomes a *re-scan hint*,
never a forgery flag. A bad scan is never branded a fake.

## Setup
1. Install Python 3.10+ and the **Tesseract OCR engine**
   - Windows: installer from <https://github.com/UB-Mannheim/tesseract/wiki> (tick the Tamil/Hindi/Telugu data if needed), then add it to PATH
   - Ubuntu/Debian: `sudo apt install tesseract-ocr tesseract-ocr-tam tesseract-ocr-hin tesseract-ocr-tel`
   - macOS: `brew install tesseract tesseract-lang`
2. Install Python packages:
   ```bash
   python -m venv .venv
   source .venv/bin/activate        # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Run:
   ```bash
   streamlit run app.py
   ```

## Try it with the demo documents
```bash
python samples/make_samples.py      # creates synthetic marksheets + an ID (no real data)
```
Upload `samples/marksheet_tampered.png` → **REVIEW REQUIRED: Total mismatch: 270 ≠ 280**.
Upload `samples/marksheet_clean.png` → **VERIFIED**.
Upload `marksheet_clean.png` + `id_name_mismatch.png` → name difference flagged for review.

## Tests
```bash
pytest -q
```

## Configuration
Thresholds (OCR confidence, name-match similarity, age limits, required fields, per-institution serial
patterns) live in `backend/config.py`.

## Assumptions & limitations
- Subject rows are expected as `Subject  marks` (optionally `marks max`) on one line. Real boards differ, so
  add institution-specific layout templates for production use.
- Seal detection only checks that a circular stamp is *present*; it does not authenticate it.
- This is a decision-support tool. It cannot prove authenticity; official verification (DigiLocker, NAD,
  the issuing board) remains the source of truth.
- Privacy: processing is local; images are never stored, only extracted fields and findings. ID numbers
  are masked.

## Roadmap
Connectors to DigiLocker / National Academic Depository / state boards, Hindi-Tamil-Telugu OCR tuning,
migration / domicile / employment records, layout templates per institution.
