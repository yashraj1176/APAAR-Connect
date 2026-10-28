from __future__ import annotations
import io, json, sqlite3
from datetime import datetime
from pathlib import Path
import pandas as pd
import streamlit as st
from core import REQUIRED_COLUMNS, seed_records, normalize_records, validate_records, quality_score, mask_apaar, chain_event, verify_audit_chain, demo_intake

ROOT = Path(__file__).parent
DB_PATH = ROOT / "apaar_connect_demo.sqlite3"

st.set_page_config(page_title="APAAR-Connect | SIH 26263", page_icon="🎓", layout="wide", initial_sidebar_state="expanded")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"] {font-family:'DM Sans',sans-serif;}
.stApp {background:linear-gradient(135deg,#f7f9ff 0%,#f4f7fb 48%,#f7f5ff 100%);}
.block-container {padding-top:1.3rem;max-width:1440px;}
.hero {background:linear-gradient(120deg,#101a3a,#243e75 58%,#3e52a3);border-radius:22px;padding:28px 32px;color:white;box-shadow:0 12px 30px #18264c20;margin-bottom:20px;}
.hero h1 {font-family:Manrope,sans-serif;font-size:2.15rem;line-height:1.15;margin:6px 0 10px;color:#fff;font-weight:800;}
.hero p {color:#dce6ff;margin:0;font-size:1rem;max-width:850px;}
.pill {display:inline-block;padding:5px 10px;border-radius:100px;font-size:.72rem;font-weight:700;letter-spacing:.05em;background:#ffffff20;color:#e9efff;border:1px solid #ffffff35;}
.metric {background:#fff;border:1px solid #e3e9f4;border-radius:16px;padding:16px 18px;box-shadow:0 4px 14px #14264b08;min-height:112px;}
.metric .label {font-size:.83rem;color:#66728b;font-weight:600;}
.metric .value {font-family:Manrope,sans-serif;font-size:1.85rem;font-weight:800;color:#15254a;line-height:1.45;}
.metric .hint {font-size:.76rem;color:#78849a;}
.section-title {font-family:Manrope,sans-serif;font-size:1.2rem;font-weight:800;color:#1b2a4c;margin:.3rem 0 .8rem;}
.note {background:#fff;border:1px solid #e3e9f4;border-left:4px solid #7186df;padding:12px 15px;border-radius:10px;color:#34415c;font-size:.9rem;}
.small-muted {color:#72809a;font-size:.83rem;}
div[data-testid="stSidebar"] {background:#f0f3fb;border-right:1px solid #e1e7f2;}
.stButton>button {border-radius:10px;font-weight:650;}
</style>
""", unsafe_allow_html=True)


def connect():
    con = sqlite3.connect(DB_PATH, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("CREATE TABLE IF NOT EXISTS students (student_ref TEXT PRIMARY KEY, student_name TEXT, apaar_id TEXT, institution TEXT, program TEXT, academic_year TEXT, admission_date TEXT, seat_category TEXT, nri TEXT, oci TEXT, foreign_national TEXT, status TEXT DEFAULT 'Submitted', created_at TEXT)")
    con.execute("CREATE TABLE IF NOT EXISTS audit (id INTEGER PRIMARY KEY AUTOINCREMENT, event_json TEXT NOT NULL, previous_hash TEXT NOT NULL, event_hash TEXT NOT NULL)")
    con.execute("CREATE TABLE IF NOT EXISTS review_cases (id INTEGER PRIMARY KEY AUTOINCREMENT, student_ref TEXT, rule_code TEXT, finding TEXT, status TEXT DEFAULT 'Open', reviewer_note TEXT DEFAULT '', updated_at TEXT)")
    con.commit()
    return con


def add_audit(con, action, detail, actor):
    event = {"timestamp": datetime.now().astimezone().isoformat(timespec="seconds"), "action": action, "detail": detail, "actor": actor}
    last = con.execute("SELECT event_hash FROM audit ORDER BY id DESC LIMIT 1").fetchone()
    prev = last[0] if last else "GENESIS"
    digest = chain_event(prev, event)
    con.execute("INSERT INTO audit(event_json,previous_hash,event_hash) VALUES(?,?,?)", (json.dumps(event, ensure_ascii=False), prev, digest))
    con.commit()


def load_students(con):
    df = pd.read_sql_query("SELECT student_ref,student_name,apaar_id,institution,program,academic_year,admission_date,seat_category,nri,oci,foreign_national,status,created_at FROM students ORDER BY student_ref", con)
    if df.empty:
        return pd.DataFrame(columns=REQUIRED_COLUMNS + ["status", "created_at"])
    return df


def seed_if_empty(con):
    if con.execute("SELECT COUNT(*) FROM students").fetchone()[0] == 0:
        df = pd.DataFrame(seed_records())
        for _, r in df.iterrows():
            con.execute("INSERT OR IGNORE INTO students(student_ref,student_name,apaar_id,institution,program,academic_year,admission_date,seat_category,nri,oci,foreign_national,status,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", tuple(str(r.get(k,"")) for k in ["student_ref","student_name","apaar_id","institution","program","academic_year","admission_date","seat_category","nri","oci","foreign_national"]) + ("Submitted", datetime.now().astimezone().isoformat(timespec="seconds")))
        con.commit()
        add_audit(con, "DEMO_SEED_CREATED", f"Loaded {len(df)} synthetic student records", "system-demo")

con = connect()
seed_if_empty(con)

with st.sidebar:
    st.markdown("## 🎓 APAAR-Connect")
    st.caption("SIH 2026 · Problem Statement 26263")
    st.markdown("---")
    role = st.selectbox("Demo role", ["AICTE Admin", "Institution Admin", "Student", "Authorised Verifier", "Auditor"], help="Role switch is for demonstration only, not production authentication.")
    pages = ["Overview", "Student Registry", "Upload & Validate", "Review Queue", "Seat Ledger Lab", "Correction Impact Lab", "Verification Portal", "Reports & Audit", "About & Limitations"]
    page = st.radio("Workspace", pages, label_visibility="collapsed")
    st.markdown("---")
    st.markdown("<span class='pill' style='background:#fff3d6;color:#855c0b;border-color:#f4d995'>DEMO MODE · SYNTHETIC DATA</span>", unsafe_allow_html=True)
    st.caption("No official APAAR / AICTE API connection.")

students = load_students(con)
if not students.empty:
    for c in ["nri", "oci", "foreign_national"]:
        students[c] = students[c].astype(str).str.lower().isin(["true", "1", "yes"])
    students["apaar_masked"] = students["apaar_id"].map(mask_apaar)
findings = validate_records(students, demo_intake()) if not students.empty else pd.DataFrame(columns=["student_ref","rule_code","severity","finding","suggested_action"])
quality = quality_score(students, findings)

st.markdown("<div class='hero'><span class='pill'>SMART INDIA HACKATHON · SIH 26263</span><h1>One academic identity.<br>More trustworthy student records.</h1><p>A privacy-first, explainable student data governance prototype for AICTE-approved institutions — built for validation, review and authorised verification.</p></div>", unsafe_allow_html=True)

if page == "Overview":
    st.markdown("<div class='section-title'>Governance overview</div>", unsafe_allow_html=True)
    total = len(students)
    critical = int((findings["severity"] == "High").sum()) if not findings.empty else 0
    open_cases = con.execute("SELECT COUNT(*) FROM review_cases WHERE status='Open'").fetchone()[0]
    duplicate_count = int((findings["rule_code"] == "DUPLICATE_APAAR").sum()) if not findings.empty else 0
    cols = st.columns(4)
    for col, label, value, hint in zip(cols, ["Student records", "Quality passport", "Findings to review", "Open review cases"], [f"{total:,}", f"{quality}/100", f"{len(findings):,}", f"{open_cases:,}"], ["Synthetic demo dataset", "Rule-based, explainable score", "Not a fraud determination", "Require human decision"]):
        col.markdown(f"<div class='metric'><div class='label'>{label}</div><div class='value'>{value}</div><div class='hint'>{hint}</div></div>", unsafe_allow_html=True)
    st.write("")
    left, right = st.columns([1.15, 1])
    with left:
        st.markdown("<div class='section-title'>Data quality passport</div>", unsafe_allow_html=True)
        st.progress(quality / 100, text=f"Current demo quality score: {quality}/100")
        if not findings.empty:
            counts = findings.groupby(["severity"]).size().reset_index(name="count")
            st.bar_chart(counts.set_index("severity"), height=200)
        st.markdown("<div class='note'>The score prioritises data cleanup; it is not an institutional ranking, fraud score, or official compliance decision.</div>", unsafe_allow_html=True)
    with right:
        st.markdown("<div class='section-title'>Signal monitor</div>", unsafe_allow_html=True)
        if findings.empty:
            st.success("No validation findings in the current data.")
        else:
            display = findings[["student_ref", "rule_code", "severity", "finding"]].head(7)
            st.dataframe(display, hide_index=True, use_container_width=True)
        st.markdown("<div class='section-title'>What makes this different?</div>", unsafe_allow_html=True)
        st.markdown("- **Explainable alerts:** each issue has a rule code and next action.\n- **Seat Ledger Lab:** test capacity scenarios before deciding.\n- **Quality Passport:** compare upload batches over time.\n- **Tamper-evident audit:** verify whether logged events were altered.\n- **Privacy preview:** see the minimum data a verifier receives.")

elif page == "Student Registry":
    st.markdown("<div class='section-title'>Student registry</div>", unsafe_allow_html=True)
    st.caption("Fictional records only. APAAR-like values are synthetic placeholders, not real identifiers.")
    search = st.text_input("Search by reference, name, program or last four digits", placeholder="e.g. STU-2026-001")
    filtered = students.copy()
    if search:
        mask = filtered[["student_ref","student_name","program","apaar_masked"]].astype(str).apply(lambda col: col.str.contains(search, case=False, na=False)).any(axis=1)
        filtered = filtered[mask]
    show = filtered[["student_ref","student_name","apaar_masked","institution","program","academic_year","admission_date","seat_category","status"]].rename(columns={"apaar_masked":"APAAR (masked)"})
    st.dataframe(show, hide_index=True, use_container_width=True)
    with st.expander("Add a synthetic demo record"):
        with st.form("add_student"):
            a,b,c = st.columns(3)
            ref = a.text_input("Student reference", value=f"STU-2026-{len(students)+1:03d}")
            name = b.text_input("Student name", value="Demo Student New")
            aid = c.text_input("Synthetic APAAR-like ID", value=f"99990000{len(students)+1:04d}")
            d,e,f = st.columns(3)
            program = d.selectbox("Program", ["Computer Science", "Information Technology", "Electronics"])
            date = e.text_input("Admission date (YYYY-MM-DD)", value="2026-08-01")
            category = f.selectbox("Seat category", sorted(["regular", "supernumerary", "nri", "oci", "foreign_national"]))
            submitted = st.form_submit_button("Save demo record", type="primary")
        if submitted:
            try:
                con.execute("INSERT INTO students(student_ref,student_name,apaar_id,institution,program,academic_year,admission_date,seat_category,nri,oci,foreign_national,status,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", (ref.strip(),name.strip(),aid.strip(),"Demo Institute of Technology",program,"2026-27",date.strip(),category,"false","false","false","Submitted",datetime.now().astimezone().isoformat(timespec="seconds")))
                con.commit(); add_audit(con,"STUDENT_CREATED",ref,role); st.success("Demo record saved. Refresh the page to see updated metrics."); st.rerun()
            except sqlite3.IntegrityError:
                st.error("That student reference already exists. Choose a unique reference.")

elif page == "Upload & Validate":
    st.markdown("<div class='section-title'>Upload and validate records</div>", unsafe_allow_html=True)
    st.markdown("Upload CSV data, inspect row-level findings, then explicitly commit clean/accepted rows. The APAAR adapter is simulated.")
    sample = pd.DataFrame(seed_records()).head(5)
    st.download_button("Download CSV template + sample", sample.to_csv(index=False).encode("utf-8"), file_name="apaar_connect_synthetic_template.csv", mime="text/csv")
    uploaded = st.file_uploader("Choose CSV", type=["csv"])
    if uploaded:
        try:
            raw = pd.read_csv(uploaded, dtype=str).fillna("")
            normalized = normalize_records(raw)
            new_findings = validate_records(normalized, demo_intake())
            st.markdown("#### Preview")
            st.dataframe(normalized.head(30), hide_index=True, use_container_width=True)
            st.markdown(f"**Rows:** {len(normalized)} · **Findings:** {len(new_findings)} · **Quality score:** {quality_score(normalized,new_findings)}/100")
            if not new_findings.empty:
                st.dataframe(new_findings, hide_index=True, use_container_width=True)
                st.download_button("Download findings report", new_findings.to_csv(index=False).encode("utf-8"), file_name="validation_findings.csv", mime="text/csv")
            else:
                st.success("No rule-based findings detected in this upload.")
            st.warning("Review the findings before committing. Format checks do not prove that an APAAR ID is authentic.")
            allow = st.checkbox("I reviewed the preview. Commit this synthetic/demo upload to the local registry.")
            if st.button("Commit upload", type="primary", disabled=not allow):
                added = 0; skipped = 0
                existing_refs = {r[0] for r in con.execute("SELECT student_ref FROM students").fetchall()}
                for _, row in normalized.iterrows():
                    ref = str(row["student_ref"]).strip()
                    if not ref or ref in existing_refs:
                        skipped += 1; continue
                    values = [str(row[k]) for k in REQUIRED_COLUMNS]
                    con.execute("INSERT INTO students(student_ref,student_name,apaar_id,institution,program,academic_year,admission_date,seat_category,nri,oci,foreign_national,status,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", tuple(values)+("Submitted",datetime.now().astimezone().isoformat(timespec="seconds")))
                    existing_refs.add(ref); added += 1
                con.commit(); add_audit(con,"UPLOAD_COMMITTED",f"added={added}; skipped={skipped}; rows={len(normalized)}",role)
                for _, fnd in new_findings.iterrows():
                    con.execute("INSERT INTO review_cases(student_ref,rule_code,finding,status,reviewer_note,updated_at) VALUES(?,?,?,?,?,?)",(fnd.student_ref,fnd.rule_code,fnd.finding,"Open","",datetime.now().astimezone().isoformat(timespec="seconds")))
                con.commit(); st.success(f"Committed {added} records. Skipped {skipped} missing/duplicate references."); st.rerun()
        except Exception as exc:
            st.error(f"Could not read this CSV: {exc}")
    else:
        st.info("Tip: start with the downloadable template. Required columns: " + ", ".join(REQUIRED_COLUMNS))

elif page == "Review Queue":
    st.markdown("<div class='section-title'>Human review queue</div>", unsafe_allow_html=True)
    st.caption("Alerts are leads for review, not automatic fraud decisions.")
    cases = pd.read_sql_query("SELECT id,student_ref,rule_code,finding,status,reviewer_note,updated_at FROM review_cases ORDER BY id DESC", con)
    if cases.empty:
        st.info("No review cases yet. Upload a CSV with validation issues to populate the queue.")
    else:
        f1,f2 = st.columns(2)
        status_filter = f1.selectbox("Status", ["All", "Open", "Resolved", "Dismissed"])
        code_filter = f2.selectbox("Rule", ["All"] + sorted(cases["rule_code"].unique().tolist()))
        shown = cases.copy()
        if status_filter != "All": shown = shown[shown.status == status_filter]
        if code_filter != "All": shown = shown[shown.rule_code == code_filter]
        st.dataframe(shown, hide_index=True, use_container_width=True)
        st.markdown("#### Review a case")
        case_id = st.selectbox("Case ID", cases["id"].tolist())
        selected = cases[cases.id == case_id].iloc[0]
        st.write(f"**{selected['rule_code']}** · {selected['student_ref']} — {selected['finding']}")
        with st.form("review_form"):
            decision = st.radio("Decision", ["Open", "Resolved", "Dismissed"], horizontal=True, index=["Open","Resolved","Dismissed"].index(selected["status"]))
            note = st.text_area("Reviewer note (required for a final decision)", value=selected["reviewer_note"] or "")
            save = st.form_submit_button("Save review decision", type="primary")
        if save:
            if decision != "Open" and not note.strip(): st.error("Add a brief reason before closing a case.")
            else:
                con.execute("UPDATE review_cases SET status=?,reviewer_note=?,updated_at=? WHERE id=?",(decision,note.strip(),datetime.now().astimezone().isoformat(timespec="seconds"),int(case_id)))
                con.commit(); add_audit(con,"REVIEW_DECISION",f"case={case_id}; decision={decision}; note={note.strip()}",role); st.success("Review decision saved."); st.rerun()

elif page == "Seat Ledger Lab":
    st.markdown("<div class='section-title'>Seat Ledger Lab · what-if simulator</div>", unsafe_allow_html=True)
    st.markdown("Try hypothetical intake values to see how the demo capacity check behaves. Actual capacity rules must be configured from authoritative approvals, including applicable seat pools.")
    programs = sorted(students["program"].dropna().unique().tolist()) if not students.empty else ["Computer Science"]
    a,b,c = st.columns(3)
    prog = a.selectbox("Program", programs)
    year = b.selectbox("Academic year", sorted(students["academic_year"].dropna().unique().tolist()) or ["2026-27"])
    approved = c.number_input("Illustrative approved regular-seat intake", min_value=0, max_value=10000, value=7, step=1)
    current = int(((students["program"] == prog) & (students["academic_year"] == year) & (students["seat_category"] == "regular")).sum()) if not students.empty else 0
    x,y,z = st.columns(3)
    x.markdown(f"<div class='metric'><div class='label'>Current regular admissions</div><div class='value'>{current}</div><div class='hint'>From local synthetic registry</div></div>", unsafe_allow_html=True)
    y.markdown(f"<div class='metric'><div class='label'>Configured intake</div><div class='value'>{approved}</div><div class='hint'>Illustrative, editable assumption</div></div>", unsafe_allow_html=True)
    z.markdown(f"<div class='metric'><div class='label'>Current headroom / overrun</div><div class='value'>{max(0,approved-current) if current <= approved else '+'+str(current-approved)}</div><div class='hint'>{'Seats remaining' if current <= approved else 'Seats above demo limit'}</div></div>", unsafe_allow_html=True)
    hypothetical = st.slider("Add hypothetical regular-seat admissions", 0, 50, 0)
    projected = current + hypothetical
    st.progress(min(projected / max(approved,1), 1.0), text=f"Projected regular admissions: {projected} / {approved}")
    if projected > approved:
        st.error(f"Review required: projected count exceeds the illustrative limit by {projected-approved}. This is a simulation, not an official violation finding.")
    else:
        st.success(f"Within the illustrative limit; {approved-projected} regular seats remain in this scenario.")
    st.markdown("#### Seat pool mix")
    if not students.empty:
        pool = students[students["program"] == prog]["seat_category"].value_counts().rename_axis("seat_category").reset_index(name="records")
        st.bar_chart(pool.set_index("seat_category"), height=220)

elif page == "Correction Impact Lab":
    st.markdown("<div class='section-title'>Correction Impact Lab · preview before you commit</div>", unsafe_allow_html=True)
    st.markdown("This is the prototype's signature workflow: preview a proposed correction against the same validation rules before changing the registry. It shows the impact; it does not decide whether a record is true.")
    if students.empty:
        st.info("No records to correct yet.")
    else:
        ref = st.selectbox("Choose a synthetic record", students["student_ref"].tolist(), key="correction_ref")
        current = students[students["student_ref"] == ref].iloc[0]
        with st.form("correction_preview_form"):
            a,b,c = st.columns(3)
            new_aid = a.text_input("Proposed APAAR-like ID", value=str(current["apaar_id"]))
            new_date = b.text_input("Proposed admission date (YYYY-MM-DD)", value=str(current["admission_date"]))
            new_category = c.selectbox("Proposed seat category", ["regular", "supernumerary", "nri", "oci", "foreign_national"], index=["regular", "supernumerary", "nri", "oci", "foreign_national"].index(str(current["seat_category"]) if str(current["seat_category"]) in ["regular", "supernumerary", "nri", "oci", "foreign_national"] else "regular"))
            preview = st.form_submit_button("Preview correction impact", type="primary")
        if preview:
            st.session_state["correction_preview_data"] = {"ref": ref, "apaar_id": new_aid.strip(), "admission_date": new_date.strip(), "seat_category": new_category}
            st.session_state["correction_confirm"] = False
        preview_data = st.session_state.get("correction_preview_data")
        if preview_data and preview_data.get("ref") == ref:
            proposed_aid = preview_data["apaar_id"]
            proposed_date = preview_data["admission_date"]
            proposed_category = preview_data["seat_category"]
            base = students[REQUIRED_COLUMNS].copy()
            before_findings = validate_records(base, demo_intake())
            candidate = base.copy()
            candidate.loc[candidate["student_ref"] == ref, "apaar_id"] = proposed_aid
            candidate.loc[candidate["student_ref"] == ref, "admission_date"] = proposed_date
            candidate.loc[candidate["student_ref"] == ref, "seat_category"] = proposed_category
            after_findings = validate_records(candidate, demo_intake())
            before_score = quality_score(base, before_findings)
            after_score = quality_score(candidate, after_findings)
            m1,m2,m3 = st.columns(3)
            m1.markdown(f"<div class='metric'><div class='label'>Findings before</div><div class='value'>{len(before_findings)}</div><div class='hint'>Current registry</div></div>", unsafe_allow_html=True)
            m2.markdown(f"<div class='metric'><div class='label'>Findings after preview</div><div class='value'>{len(after_findings)}</div><div class='hint'>Not saved yet</div></div>", unsafe_allow_html=True)
            delta = after_score - before_score
            m3.markdown(f"<div class='metric'><div class='label'>Quality score change</div><div class='value'>{delta:+d}</div><div class='hint'>{before_score} → {after_score} / 100</div></div>", unsafe_allow_html=True)
            old_row_findings = before_findings[before_findings["student_ref"] == ref]
            new_row_findings = after_findings[after_findings["student_ref"] == ref]
            l,r = st.columns(2)
            with l:
                st.markdown("#### Before")
                st.dataframe(old_row_findings if not old_row_findings.empty else pd.DataFrame([{"result":"No findings for this record"}]), hide_index=True, use_container_width=True)
            with r:
                st.markdown("#### Proposed result")
                st.dataframe(new_row_findings if not new_row_findings.empty else pd.DataFrame([{"result":"No findings for this record"}]), hide_index=True, use_container_width=True)
            st.warning("A higher score only means fewer configured rule findings. It does not prove the proposed values are authentic.")
            confirm = st.checkbox("I have checked the source evidence and want to save this proposed correction.", key="correction_confirm")
            if st.button("Apply correction to local demo registry", disabled=not confirm):
                old_masked = mask_apaar(current["apaar_id"])
                con.execute("UPDATE students SET apaar_id=?, admission_date=?, seat_category=? WHERE student_ref=?", (proposed_aid,proposed_date,proposed_category,ref))
                con.commit()
                add_audit(con,"RECORD_CORRECTED",f"ref={ref}; apaar={old_masked}->{mask_apaar(proposed_aid)}; date={proposed_date}; category={proposed_category}",role)
                st.session_state.pop("correction_preview_data", None)
                st.success("Correction saved to the local demo registry and recorded in the audit chain.")
                st.rerun()

elif page == "Verification Portal":
    st.markdown("<div class='section-title'>Privacy-first verification portal</div>", unsafe_allow_html=True)
    st.markdown("This page demonstrates a consent-gated response. It does **not** contact APAAR, DigiLocker or AICTE systems.")
    if students.empty:
        st.info("No student records available.")
    else:
        ref = st.selectbox("Select synthetic student reference", students["student_ref"].tolist())
        row = students[students["student_ref"] == ref].iloc[0]
        purpose = st.selectbox("Verification purpose", ["Enrolment status", "Programme and academic year", "Full authorised demo record"])
        consent = st.checkbox("Student consent is recorded for this demo verification")
        if st.button("Preview verifier response", type="primary"):
            if not consent:
                st.error("No response generated: consent is not recorded in this demo flow.")
            else:
                response = {"verification_status":"SIMULATED — NOT OFFICIAL APAAR VERIFICATION", "record_reference":str(row.student_ref), "purpose":purpose, "student_consent":"DEMO CONSENT CHECKED"}
                if purpose in ["Programme and academic year", "Full authorised demo record"]:
                    response.update({"programme":str(row.program),"academic_year":str(row.academic_year),"enrolment_status":str(row.status)})
                if purpose == "Full authorised demo record":
                    response.update({"student_name":str(row.student_name),"apaar_id":mask_apaar(row.apaar_id),"institution":str(row.institution),"seat_category":str(row.seat_category)})
                st.json(response)
                add_audit(con,"VERIFICATION_PREVIEW",f"ref={ref}; purpose={purpose}; fields={','.join(response.keys())}",role)
                st.info("Production design: authenticate verifier, verify purpose and consent, return only permitted fields, and log access. Do not put personal data directly in a QR code.")

elif page == "Reports & Audit":
    st.markdown("<div class='section-title'>Reports and tamper-evident audit trail</div>", unsafe_allow_html=True)
    c1,c2 = st.columns(2)
    with c1:
        st.markdown("#### Registry report")
        report = students[["student_ref","student_name","apaar_masked","institution","program","academic_year","admission_date","seat_category","status"]].rename(columns={"apaar_masked":"apaar_masked"}) if not students.empty else pd.DataFrame()
        st.download_button("Export registry CSV (masked ID)", report.to_csv(index=False).encode("utf-8"), file_name="apaar_connect_registry_masked.csv", mime="text/csv")
        st.download_button("Export validation findings", findings.to_csv(index=False).encode("utf-8"), file_name="apaar_connect_findings.csv", mime="text/csv")
        cases = pd.read_sql_query("SELECT * FROM review_cases", con)
        st.download_button("Export review cases", cases.to_csv(index=False).encode("utf-8"), file_name="apaar_connect_review_cases.csv", mime="text/csv")
    with c2:
        st.markdown("#### Audit chain integrity")
        raw_events = con.execute("SELECT event_json,previous_hash,event_hash FROM audit ORDER BY id").fetchall()
        events = [{"event":json.loads(r[0]),"previous_hash":r[1],"event_hash":r[2]} for r in raw_events]
        valid, broken = verify_audit_chain(events)
        if valid: st.success(f"Audit chain valid · {len(events)} events checked")
        else: st.error(f"Audit chain check failed at event index {broken}")
        if events:
            audit_view = pd.DataFrame([{"time":e["event"].get("timestamp"),"actor":e["event"].get("actor"),"action":e["event"].get("action"),"detail":e["event"].get("detail"),"hash":e["event_hash"][:16]+"…"} for e in events])
            st.dataframe(audit_view.tail(30), hide_index=True, use_container_width=True)
        st.caption("Hash chaining is tamper-evident within this local demo; it is not a substitute for protected production storage, key management or independent logging.")
    with st.expander("Reset local demo database"):
        st.warning("This deletes all local demo changes and reloads the synthetic seed data.")
        if st.button("Reset demo data", type="secondary"):
            con.close(); DB_PATH.unlink(missing_ok=True); st.rerun()

elif page == "About & Limitations":
    st.markdown("<div class='section-title'>Project notes, assumptions and limitations</div>", unsafe_allow_html=True)
    st.markdown("""
### What is implemented
- Local SQLite registry with synthetic seed records and a CSV import workflow.
- Rule-based checks for missing/invalid identifier format, duplicates in an upload, required fields, date format/window and configurable illustrative intake checks.
- Quality Passport score, human review queue, seat what-if simulator, correction impact preview, masked CSV exports and hash-chained audit events.
- Purpose-based verification preview with explicit demo consent checkbox and field minimisation.

### What is not implemented / must not be claimed
- No live APAAR, AICTE, DigiLocker, ABC or institutional ERP integration.
- No official identity validation. A 12-digit format check only validates shape, not ownership or authenticity.
- Demo role selector is not real authentication. Do not use real student data, credentials, secrets or government identifiers.
- The demo intake rules and academic date window are assumptions. They must be replaced by authorised rules and actual approved-intake records.
- The audit chain is a local tamper-evidence demonstration, not a hardened immutable log service.
- This prototype is not production-ready; it needs security review, formal privacy/legal review, authenticated APIs, access control, encryption, backup, monitoring and load testing.

### Suggested production path
1. Confirm field definitions, seat-pool policies and exception handling with AICTE/institution stakeholders.
2. Obtain documented official API access and use a replaceable integration adapter.
3. Add SSO/MFA, server-side RBAC, institution data isolation, encryption/key management and monitored audit storage.
4. Conduct privacy impact assessment, retention policy design, threat modelling and independent penetration testing.
5. Pilot with consented, authorised test data before any live rollout.
""")
    st.markdown("**Official reference links:** [APAAR portal](https://apaar.education.gov.in/) · [AICTE portal](https://www.aicte.gov.in/)")

st.markdown("<hr><div class='small-muted'>APAAR-Connect prototype · SIH PS 26263 · synthetic data only · not an official government product or endorsement.</div>", unsafe_allow_html=True)
