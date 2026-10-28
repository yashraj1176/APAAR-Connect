"""Core logic for APAAR-Connect demo. Uses synthetic data only; no official integration."""
from __future__ import annotations
import hashlib, json, re
from datetime import datetime, timezone
from typing import Any
import pandas as pd

REQUIRED_COLUMNS = ["student_ref", "student_name", "apaar_id", "institution", "program", "academic_year", "admission_date", "seat_category", "nri", "oci", "foreign_national"]
CATEGORIES = {"regular", "supernumerary", "nri", "oci", "foreign_national"}


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def mask_apaar(value: Any) -> str:
    s = re.sub(r"\D", "", str(value or ""))
    if not s:
        return "Not provided"
    return f"•••• •••• {s[-4:]}" if len(s) >= 4 else "••••"


def seed_records() -> list[dict[str, Any]]:
    # Every identity and institution below is fictional test data.
    rows = []
    names = ["Aarav Demo", "Ira Sample", "Kabir Test", "Meera Fiction", "Dev Mock", "Anaya Demo", "Reyansh Sample", "Sara Test", "Vihaan Fiction", "Aditi Mock", "Arjun Demo", "Kiara Sample", "Rohan Test", "Myra Fiction", "Ishaan Mock", "Naina Demo", "Advait Sample", "Tara Test"]
    programs = ["Computer Science", "Information Technology", "Electronics"]
    for i, name in enumerate(names, 1):
        rows.append({
            "student_ref": f"STU-{2026:04d}-{i:03d}", "student_name": name,
            "apaar_id": f"99990000{i:04d}", "institution": "Demo Institute of Technology",
            "program": programs[(i - 1) % len(programs)], "academic_year": "2026-27",
            "admission_date": f"2026-07-{(i % 25) + 1:02d}",
            "seat_category": "regular" if i % 7 else "supernumerary",
            "nri": bool(i % 11 == 0), "oci": False, "foreign_national": bool(i % 13 == 0),
        })
    # Planted demo signals: duplicate identifier and invalid identifier are deliberate, synthetic.
    rows[4]["apaar_id"] = rows[1]["apaar_id"]  # cross-record duplicate
    rows[8]["apaar_id"] = "INVALID-DEMO-ID"
    rows[12]["admission_date"] = "2026-04-02"  # outside illustrative admission window
    return rows


def normalize_records(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for c in REQUIRED_COLUMNS:
        if c not in df.columns:
            df[c] = ""
    df = df[REQUIRED_COLUMNS]
    for c in REQUIRED_COLUMNS:
        df[c] = df[c].fillna("").astype(str).str.strip()
    for c in ["nri", "oci", "foreign_national"]:
        df[c] = df[c].str.lower().map({"true": "true", "1": "true", "yes": "true", "y": "true", "false": "false", "0": "false", "no": "false", "n": "false", "": "false"}).fillna("false")
    return df


def validate_records(df: pd.DataFrame, intake: dict[tuple[str, str, str], int] | None = None) -> pd.DataFrame:
    """Return one finding per issue. Capacity checks use illustrative demo limits."""
    clean = normalize_records(df)
    findings: list[dict[str, Any]] = []
    seen: dict[str, int] = {}
    for idx, row in clean.iterrows():
        ref = row["student_ref"] or f"ROW-{idx + 1}"
        aid = row["apaar_id"]
        if not aid:
            findings.append(_finding(ref, "MISSING_APAAR", "High", "APAAR ID is missing.", "Use the authorised source to confirm the identifier, or mark the record as provisional."))
        elif not re.fullmatch(r"\d{12}", aid):
            findings.append(_finding(ref, "INVALID_APAAR_FORMAT", "High", "Identifier does not match the expected 12-digit format.", "Check the source record. Format validation is not official identity verification."))
        elif aid in seen:
            findings.append(_finding(ref, "DUPLICATE_APAAR", "High", f"Identifier matches {clean.iloc[seen[aid]]['student_ref'] or 'another row'} in this upload.", "Review both enrolments with authorised staff; do not automatically label as fraud."))
        else:
            seen[aid] = idx
        for field in ("student_name", "institution", "program", "academic_year", "admission_date"):
            if not row[field]:
                findings.append(_finding(ref, f"MISSING_{field.upper()}", "Medium", f"Required field '{field}' is empty.", f"Complete {field.replace('_', ' ')} from the institution's authoritative record."))
        if row["seat_category"] not in CATEGORIES:
            findings.append(_finding(ref, "UNKNOWN_SEAT_CATEGORY", "Medium", "Seat category is not recognised by this demo configuration.", "Map the category to the institution's approved rules before submission."))
        try:
            dt = datetime.strptime(row["admission_date"], "%Y-%m-%d").date()
            if dt < datetime(2026, 6, 1).date() or dt > datetime(2027, 5, 31).date():
                findings.append(_finding(ref, "DATE_OUTSIDE_DEMO_WINDOW", "Medium", "Admission date is outside the illustrative 2026-27 demo window.", "Confirm the applicable academic calendar; this demo window is not an official AICTE rule."))
        except ValueError:
            if row["admission_date"]:
                findings.append(_finding(ref, "INVALID_DATE", "Medium", "Admission date must use YYYY-MM-DD format.", "Correct the date format and re-upload."))
    # Capacity: only regular seats are compared against the demo approved intake. Other pools are reported separately.
    if intake:
        group = clean[clean["seat_category"] == "regular"].groupby(["institution", "program", "academic_year"]).size()
        for key, count in group.items():
            limit = intake.get(tuple(key))
            if limit is not None and count > limit:
                for _, row in clean[(clean["institution"] == key[0]) & (clean["program"] == key[1]) & (clean["academic_year"] == key[2]) & (clean["seat_category"] == "regular")].iterrows():
                    findings.append(_finding(row["student_ref"], "INTAKE_REVIEW", "High", f"Regular-seat count {count} is above the illustrative configured intake of {limit}.", "Check applicable approved intake and permitted seat-pool rules before deciding."))
    return pd.DataFrame(findings, columns=["student_ref", "rule_code", "severity", "finding", "suggested_action"])


def _finding(ref: str, code: str, severity: str, finding: str, action: str) -> dict[str, str]:
    return {"student_ref": ref, "rule_code": code, "severity": severity, "finding": finding, "suggested_action": action}


def quality_score(records: pd.DataFrame, findings: pd.DataFrame) -> int:
    if records.empty:
        return 0
    high = int((findings["severity"] == "High").sum()) if not findings.empty else 0
    medium = int((findings["severity"] == "Medium").sum()) if not findings.empty else 0
    score = round(max(0, 100 - ((high * 12 + medium * 5) / max(len(records), 1) * 10)))
    return min(100, score)


def chain_event(previous_hash: str, event: dict[str, Any]) -> str:
    canonical = json.dumps({"previous_hash": previous_hash, "event": event}, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def verify_audit_chain(events: list[dict[str, Any]]) -> tuple[bool, int | None]:
    previous = "GENESIS"
    for i, item in enumerate(events):
        expected = chain_event(previous, item["event"])
        if item.get("previous_hash") != previous or item.get("event_hash") != expected:
            return False, i
        previous = item["event_hash"]
    return True, None


def demo_intake() -> dict[tuple[str, str, str], int]:
    return {
        ("Demo Institute of Technology", "Computer Science", "2026-27"): 7,
        ("Demo Institute of Technology", "Information Technology", "2026-27"): 7,
        ("Demo Institute of Technology", "Electronics", "2026-27"): 7,
    }
