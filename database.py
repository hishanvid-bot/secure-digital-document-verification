"""Storage & audit trail (SQLite). Only extracted fields are stored - never the images."""
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    applicant_ref TEXT,
    status TEXT NOT NULL,
    summary TEXT,
    n_docs INTEGER
);
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    submission_id INTEGER NOT NULL REFERENCES submissions(id),
    filename TEXT, doc_type TEXT, ocr_conf REAL, blur_score REAL,
    fields_json TEXT, subjects_json TEXT
);
CREATE TABLE IF NOT EXISTS issues (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    submission_id INTEGER NOT NULL REFERENCES submissions(id),
    severity TEXT, code TEXT, message TEXT, field TEXT, doc TEXT, conf REAL, rescan INTEGER
);
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    submission_id INTEGER NOT NULL REFERENCES submissions(id),
    ts TEXT NOT NULL, actor TEXT, action TEXT, note TEXT
);
"""


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def connect(path: str = None):
    con = sqlite3.connect(path or config.DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    try:
        yield con
        con.commit()
    finally:
        con.close()


def init_db(path: str = None):
    with connect(path) as con:
        con.executescript(SCHEMA)


def save_submission(result: dict, applicant_ref: str = "", path: str = None) -> int:
    with connect(path) as con:
        cur = con.execute(
            "INSERT INTO submissions(created_at, applicant_ref, status, summary, n_docs) VALUES (?,?,?,?,?)",
            (_now(), applicant_ref, result["status"], result["summary"], len(result["documents"])))
        sid = cur.lastrowid
        for d in result["documents"]:
            safe_fields = {k: {"value": v["value"], "conf": v["conf"]} for k, v in d["fields"].items()}
            con.execute(
                "INSERT INTO documents(submission_id, filename, doc_type, ocr_conf, blur_score, fields_json, subjects_json)"
                " VALUES (?,?,?,?,?,?,?)",
                (sid, d["filename"], d["doc_type"], d["ocr_conf"], d["blur_score"],
                 json.dumps(safe_fields), json.dumps([{k: s[k] for k in ("subject", "marks", "max")} for s in d["subjects"]])))
        for i in result["issues"]:
            con.execute(
                "INSERT INTO issues(submission_id, severity, code, message, field, doc, conf, rescan) VALUES (?,?,?,?,?,?,?,?)",
                (sid, i["severity"], i["code"], i["message"], i["field"], i["doc"], i["conf"], int(i["rescan"])))
        con.execute("INSERT INTO audit_log(submission_id, ts, actor, action, note) VALUES (?,?,?,?,?)",
                    (sid, _now(), "system", "AUTO_TRIAGE", f"{result['status']}: {result['summary']}"))
    return sid


def record_decision(submission_id: int, actor: str, action: str, note: str = "", path: str = None):
    """action: APPROVED | FLAGGED | RESCAN_REQUESTED. Final decision belongs to the human."""
    with connect(path) as con:
        con.execute("INSERT INTO audit_log(submission_id, ts, actor, action, note) VALUES (?,?,?,?,?)",
                    (submission_id, _now(), actor, action, note))
        con.execute("UPDATE submissions SET status=? WHERE id=?", (action, submission_id))


def list_submissions(path: str = None):
    with connect(path) as con:
        return [dict(r) for r in con.execute("SELECT * FROM submissions ORDER BY id DESC")]


def get_submission(submission_id: int, path: str = None):
    with connect(path) as con:
        sub = con.execute("SELECT * FROM submissions WHERE id=?", (submission_id,)).fetchone()
        docs = [dict(r) for r in con.execute("SELECT * FROM documents WHERE submission_id=?", (submission_id,))]
        issues = [dict(r) for r in con.execute("SELECT * FROM issues WHERE submission_id=?", (submission_id,))]
        audit = [dict(r) for r in con.execute("SELECT * FROM audit_log WHERE submission_id=? ORDER BY id", (submission_id,))]
    return (dict(sub) if sub else None), docs, issues, audit
