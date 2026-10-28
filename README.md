# APAAR-Connect — SIH PS 26263 Prototype

**Tagline:** One academic identity. More trustworthy student records.

A local, demonstrable prototype for the SIH problem statement: APAAR-linked student data management and verification for AICTE-approved institutions.

> **Important:** This is an independent prototype using fictional synthetic data. It is not affiliated with or endorsed by AICTE or APAAR. It does not connect to APAAR, AICTE, DigiLocker, ABC or any government system. Identifier checks are format checks only; they do not verify a real identity. Do not upload real student data.

## Features implemented

- Overview dashboard with a rule-based Data Quality Passport score.
- Synthetic student registry with masked identifier display and local demo record creation.
- CSV template download, CSV upload, row preview, validation findings and downloadable error report.
- Rule checks: missing fields, 12-digit format check, duplicate identifier within the supplied records, date format/demo date window, seat category and illustrative intake review.
- Human review queue with Open / Resolved / Dismissed decisions and mandatory notes for closing a case.
- Seat Ledger Lab with hypothetical capacity what-if simulation.
- Consent-gated verification response preview with purpose-based field minimisation.
- CSV exports with masked identifiers.
- Local hash-chained audit events and tamper-check demo.
- Tests for core validation and audit-chain behaviour.

## Differentiators to present to judges

1. **Explainable Validation:** each alert has a stable rule code, reason and suggested next action.
2. **Data Quality Passport:** a cleanup-oriented score that is explicitly not a fraud score or official compliance ranking.
3. **Seat Ledger Lab:** a what-if sandbox for intake/capacity scenarios. Seat rules are configurable assumptions until authoritative rules are supplied.
4. **Consent-first verifier preview:** the demo demonstrates purpose limitation and minimal disclosure instead of putting personal data into a QR code.
5. **Tamper-evident event chain:** reviewers can verify that the locally stored audit sequence has not changed since events were recorded.
6. **Honest integration boundary:** official identity checks are kept behind a future adapter; the UI clearly labels the current flow simulated.

These are a combination of prototype differentiators, not a claim that no other system has similar features. Existing public repositories for the same problem statement already demonstrate some advanced patterns such as seat ledgers, consent, duplicate detection, credentials and audit chains. The value here is a coherent, easy-to-run judge demo with transparent assumptions.

## Requirements

- Python 3.10 or newer (Python 3.12 recommended)
- Internet connection only for installing Python packages / loading the optional Google font. App data stays in local SQLite.

## Run on Windows (VS Code / CMD)

1. Extract this ZIP.
2. Open the extracted `apaar_connect_prototype` folder in VS Code.
3. Open Terminal in that folder and run:

   ```bat
   python -m venv .venv
   .venv\Scripts\activate
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   streamlit run app.py
   ```

4. Browser should open automatically. If not, visit `http://localhost:8501`.
5. Use the left sidebar to switch pages. The role selector is a **demo-only** switch, not production authentication.

If `python` points to a different installation, try `py -3.12 -m venv .venv` then activate the environment and continue.

## Run tests

```bat
python -m pip install pytest
python -m pytest -q
```

## CSV schema

The downloadable sample template contains these fields:

`student_ref, student_name, apaar_id, institution, program, academic_year, admission_date, seat_category, nri, oci, foreign_national`

Boolean fields accept common forms such as `true/false`, `yes/no`, `1/0`. Expected demo seat categories are `regular`, `supernumerary`, `nri`, `oci`, `foreign_national`. Adjustments to real categories must be approved by the relevant authority before deployment.

## Local data and reset

The first run creates `apaar_connect_demo.sqlite3` and seeds fictional records. Use **Reports & Audit → Reset demo data** to remove local demo changes and reload the seed. The SQLite file is created only when the app runs and is excluded from the ZIP.

## Limitations and production work

- No live API, official APAAR validation, AICTE portal SSO, DigiLocker, ABC or ERP integration.
- Seed identities, institutions and all data are fictional; demo IDs are placeholders.
- Role selection is not real authentication/authorisation; do not treat it as secure.
- The date window and seat-intake examples are illustrative assumptions, not official rules.
- Duplicate checks are scoped to the records available to this local demo; no secure cross-institution identity matching is implemented.
- Hash chaining is a tamper-evidence demonstration, not immutable storage.
- No production-grade encryption, MFA, user administration, database row-level security, backup, monitoring, rate limits or penetration testing.
- Not production-ready and not suitable for real personal data until security, privacy, legal and stakeholder reviews are completed.

## Architecture

```text
Streamlit UI
  ├── Overview / Quality Passport
  ├── Registry / CSV ingestion
  ├── Rule-based validation engine (core.py)
  ├── Human review queue
  ├── Seat what-if simulator
  ├── Consent-gated verifier preview
  └── CSV reports + hash-chained audit events
              │
              ▼
        Local SQLite database

Future only (not connected): official APAAR / AICTE integration adapter
```

## Official reference links

- APAAR portal: https://apaar.education.gov.in/
- AICTE portal: https://www.aicte.gov.in/
- SIH problem statement background: https://zaidsayyed.in/tools/sih-problem-statements/sih26263

## Project status

**Prototype / hackathon demo.** No claim of official deployment, official validation or affiliation.
