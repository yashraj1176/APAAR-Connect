# Project map

| File | Purpose |
|---|---|
| `app.py` | Streamlit UI, local SQLite workflows, CSV import/export, review queue, verification preview, audit view |
| `core.py` | Normalisation, explainable validation rules, quality score, masked IDs, hash-chain helpers, synthetic seed data |
| `tests/test_core.py` | Unit tests for validation and audit-chain behaviour |
| `requirements.txt` | Minimal Python dependencies |
| `DEMO_SCRIPT.md` | Judge-facing 3-minute demo walkthrough |
| `README.md` | Setup, architecture, differentiators and limitations |
| `run_windows.bat` | Windows convenience launcher |

## Requirement-to-feature mapping

| SIH requirement | Prototype coverage | Boundary |
|---|---|---|
| Student-level data submission | CSV upload + local registry | Local demo only |
| APAAR identifier validation | Missing / 12-digit format rules | Not official identity validation |
| Duplicate records | Duplicate identifier checks across the records in the current validation set | No privacy-preserving federation between live institutions |
| Intake monitoring | Seat Ledger Lab | Configurable illustrative intake values only |
| Institutional / AICTE dashboards | Overview, registry, review queue | Demo role switch is not authentication |
| Authorised verification | Purpose-based response preview + consent checkbox | No live verifier credentials or official APIs |
| Audit trail | Hash-chained local event log | Not hardened immutable storage |
| Reports | Masked CSV exports | No official report schema supplied |
| Integration API | Documented future integration boundary | API adapter not connected/implemented |
| Privacy and security | Masked display, field minimisation, clear mock labels | Production security controls still required |
