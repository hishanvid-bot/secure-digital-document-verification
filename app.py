"""Streamlit front end: upload portal + reviewer dashboard + audit log.
Run:  streamlit run app.py"""
import pandas as pd
import streamlit as st

from backend import database as db
from backend.pipeline import process_packet

st.set_page_config(page_title="Secure Digital Document Verification", page_icon="✅", layout="wide")
db.init_db()

BADGE = {
    "VERIFIED": ("#2e9e5b", "VERIFIED"),
    "REVIEW REQUIRED": ("#f5a623", "REVIEW REQUIRED"),
    "REQUEST RE-SCAN": ("#7b8ba6", "REQUEST RE-SCAN"),
    "APPROVED": ("#2e9e5b", "APPROVED (officer)"),
    "FLAGGED": ("#d64545", "FLAGGED (officer)"),
    "RESCAN_REQUESTED": ("#7b8ba6", "RE-SCAN REQUESTED (officer)"),
}
SEV_ICON = {"error": "🔴", "warning": "🟠", "info": "🔵"}


def badge(status: str) -> str:
    colour, label = BADGE.get(status, ("#555", status))
    return (f"<span style='background:{colour};color:white;padding:4px 14px;border-radius:6px;"
            f"font-weight:700'>{label}</span>")


def show_issues(issues):
    if not issues:
        st.success("No issues found.")
    for i in issues:
        tag = " — scan-quality issue, **not** a forgery signal" if i.get("rescan") else ""
        st.markdown(f"{SEV_ICON.get(i['severity'], '•')} **{i['field'] or i['code']}** "
                    f"({i['doc']}): {i['message']}{tag}")


st.title("Secure Digital Document Verification")
st.caption("Read · Understand · Compare · Explain — a human officer makes the final decision.")

tab_upload, tab_review, tab_audit = st.tabs(["📤 Upload portal", "🧑‍⚖️ Reviewer dashboard", "📜 Audit log"])

# ---------------------------------------------------------------- Upload portal
with tab_upload:
    st.subheader("Upload a document packet")
    ref = st.text_input("Applicant reference (optional, e.g. application number)")
    lang = st.selectbox("OCR language", ["eng", "eng+tam", "eng+hin", "eng+tel"],
                        help="Needs the matching Tesseract language data installed.")
    files = st.file_uploader("Marksheets, degrees, IDs (PDF / JPG / PNG)",
                             type=["pdf", "png", "jpg", "jpeg"], accept_multiple_files=True)
    if st.button("Verify packet", type="primary", disabled=not files):
        with st.spinner("Preprocessing, reading and checking…"):
            result = process_packet([(f.name, f.getvalue()) for f in files], lang=lang)
            sid = db.save_submission(result, applicant_ref=ref)
        st.session_state["last"] = (sid, result)

    if "last" in st.session_state:
        sid, result = st.session_state["last"]
        st.markdown(f"### Result for submission #{sid}")
        st.markdown(badge(result["status"]), unsafe_allow_html=True)
        st.write(result["summary"])
        show_issues(result["issues"])
        for d in result["documents"]:
            with st.expander(f"{d['filename']} — {d['doc_type']} (OCR {d['ocr_conf']:.0f}%)"):
                rows = [{"field": k, "value": v["value"] if k != "id_number" else v["source"],
                         "confidence %": round(v["conf"]), "evidence line": v["source"] if k != "id_number" else "(masked)"}
                        for k, v in d["fields"].items()]
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
                if d["subjects"]:
                    st.write("Subjects read:")
                    st.dataframe(pd.DataFrame(d["subjects"])[["subject", "marks", "max", "conf"]],
                                 use_container_width=True, hide_index=True)

# ---------------------------------------------------------------- Reviewer dashboard
with tab_review:
    st.subheader("Submissions")
    subs = db.list_submissions()
    if not subs:
        st.info("No submissions yet. Upload a packet first.")
    else:
        order = {"REVIEW REQUIRED": 0, "REQUEST RE-SCAN": 1, "VERIFIED": 2}
        subs.sort(key=lambda s: (order.get(s["status"], 3), -s["id"]))   # risky first
        st.dataframe(pd.DataFrame(subs)[["id", "created_at", "applicant_ref", "status", "n_docs"]],
                     use_container_width=True, hide_index=True)
        sid = st.selectbox("Open submission", [s["id"] for s in subs])
        sub, docs, issues, audit = db.get_submission(sid)
        st.markdown(badge(sub["status"]), unsafe_allow_html=True)
        st.write(sub["summary"])
        show_issues(issues)
        for d in docs:
            import json
            with st.expander(f"{d['filename']} — {d['doc_type']}"):
                fields = json.loads(d["fields_json"])
                st.dataframe(pd.DataFrame([{"field": k, "value": v["value"], "confidence %": round(v["conf"])}
                                           for k, v in fields.items()]),
                             use_container_width=True, hide_index=True)
        st.markdown("#### Officer decision")
        officer = st.text_input("Your name / ID", key="officer")
        note = st.text_area("Note (recommended, goes into the audit log)")
        c1, c2, c3 = st.columns(3)
        if c1.button("✅ Approve", use_container_width=True, disabled=not officer):
            db.record_decision(sid, officer, "APPROVED", note); st.rerun()
        if c2.button("🚩 Flag", use_container_width=True, disabled=not officer):
            db.record_decision(sid, officer, "FLAGGED", note); st.rerun()
        if c3.button("🔁 Ask for re-scan", use_container_width=True, disabled=not officer):
            db.record_decision(sid, officer, "RESCAN_REQUESTED", note); st.rerun()
        if not officer:
            st.caption("Enter your name to enable the decision buttons.")

# ---------------------------------------------------------------- Audit log
with tab_audit:
    st.subheader("Audit trail")
    subs = db.list_submissions()
    if subs:
        sid = st.selectbox("Submission", [s["id"] for s in subs], key="audit_sid")
        _, _, _, audit = db.get_submission(sid)
        st.dataframe(pd.DataFrame(audit)[["ts", "actor", "action", "note"]],
                     use_container_width=True, hide_index=True)
    else:
        st.info("Nothing to show yet.")
    st.caption("Privacy: images are processed locally and never stored; only extracted fields and "
               "findings are kept. ID numbers are masked.")
