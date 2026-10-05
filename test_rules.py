"""Unit tests for the rule engine - no OCR or images required.  Run: pytest -q"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.models import OcrLine
from backend.pipeline import analyse_lines, build_result
from backend.utils import normalize_name, verhoeff_valid


def L(text, conf=95.0):
    return OcrLine(text, conf)


def marksheet(total="270", conf=95.0, name="Harini Sundar", dob="14/03/2006"):
    return [
        L("SAMPLE STATE UNIVERSITY", conf), L("STATEMENT OF MARKS", conf),
        L(f"Name: {name}", conf), L(f"Date of Birth: {dob}", conf),
        L("Register No: 21CS10458", conf),
        L("Mathematics 85", conf), L("Physics 90", conf), L("Programming 95", conf),
        L(f"Total Marks: {total}", conf), L("Controller of Examinations", conf),
    ]


def test_clean_marksheet_is_verified():
    d = analyse_lines("a.png", marksheet(), 95)
    assert build_result([d])["status"] == "VERIFIED"


def test_total_mismatch_goes_to_review():
    d = analyse_lines("a.png", marksheet(total="280"), 95)
    r = build_result([d])
    assert r["status"] == "REVIEW REQUIRED"
    assert any("270" in i["message"] and "280" in i["message"] for i in r["issues"])


def test_low_confidence_is_rescan_never_forgery():
    d = analyse_lines("a.png", marksheet(total="280", conf=30.0), 30)
    r = build_result([d])
    assert r["status"] == "REQUEST RE-SCAN"
    assert not any(i["severity"] == "error" for i in r["issues"])


def test_cross_document_name_mismatch():
    a = analyse_lines("a.png", marksheet(), 95)
    b = analyse_lines("b.png", marksheet(name="Ramesh Kumar"), 95)
    assert build_result([a, b])["status"] == "REVIEW REQUIRED"


def test_small_ocr_name_variation_is_not_error():
    a = analyse_lines("a.png", marksheet(name="Harini Sundar"), 95)
    b = analyse_lines("b.png", marksheet(name="Mrs. HARINI SUNDAR"), 95)
    assert build_result([a, b])["status"] == "VERIFIED"


def test_dob_mismatch():
    a = analyse_lines("a.png", marksheet(), 95)
    b = analyse_lines("b.png", marksheet(dob="15/03/2006"), 95)
    assert any(i["code"] == "DOB_MISMATCH" for i in build_result([a, b])["issues"])


def test_helpers():
    assert normalize_name("Dr. harini  S.") == "HARINI S"
    assert verhoeff_valid("2363")        # known valid Verhoeff example
    assert not verhoeff_valid("2364")
