"""Orchestrates: Upload -> Preprocess -> Extract -> Validate -> Reconcile -> Decide."""
from dataclasses import asdict
from typing import List, Tuple

from . import config
from .decide import triage
from .extract import extract_fields
from .models import DocResult, Issue, OcrLine
from .ocr import run_ocr
from .preprocess import blur_score, detect_seal, load_pages, preprocess
from .reconcile import reconcile
from .validate import validate_document


def analyse_lines(filename: str, lines: List[OcrLine], ocr_conf: float, blur: float = 999.0,
                  seal: bool = True) -> DocResult:
    """Everything after OCR - handy for unit tests without images."""
    fields, subjects, doc_type = extract_fields(lines)
    d = DocResult(filename=filename, doc_type=doc_type, ocr_conf=ocr_conf, blur_score=blur,
                  seal_found=seal, fields=fields, subjects=subjects,
                  text="\n".join(l.text for l in lines))
    d.issues = validate_document(d)
    return d


def analyse_document(filename: str, data: bytes, lang: str = "eng") -> DocResult:
    pages = load_pages(filename, data)
    all_lines: List[OcrLine] = []
    confs, blurs, seal = [], [], False
    for bgr in pages:
        clean = preprocess(bgr)
        lines, mean = run_ocr(clean, lang=lang)
        all_lines.extend(lines)
        confs.append(mean)
        blurs.append(blur_score(clean))
        seal = seal or detect_seal(bgr)
    return analyse_lines(filename, all_lines, sum(confs) / len(confs), min(blurs), seal)


def process_packet(files: List[Tuple[str, bytes]], lang: str = "eng") -> dict:
    docs: List[DocResult] = []
    for name, data in files:
        try:
            docs.append(analyse_document(name, data, lang))
        except Exception as exc:  # one bad file must not kill the whole packet
            bad = DocResult(filename=name)
            bad.issues.append(Issue("warning", "UNREADABLE", f"Could not process file: {exc}",
                                    "document", name, rescan=True))
            docs.append(bad)
    return build_result(docs)


def build_result(docs: List[DocResult]) -> dict:
    cross = reconcile(docs)
    all_issues = [i for d in docs for i in d.issues] + cross
    status, summary = triage(all_issues)
    return {
        "status": status,
        "summary": summary,
        "documents": [_doc_dict(d) for d in docs],
        "issues": [asdict(i) for i in all_issues],
    }


def _doc_dict(d: DocResult) -> dict:
    out = d.to_dict()
    out["fields"] = {k: asdict(v) for k, v in d.fields.items()}
    return out
