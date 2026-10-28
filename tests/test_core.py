import pandas as pd
from core import chain_event, verify_audit_chain, validate_records, quality_score, REQUIRED_COLUMNS


def sample():
    return pd.DataFrame([{
        "student_ref":"STU-1", "student_name":"Demo", "apaar_id":"999900000001",
        "institution":"Demo Institute of Technology", "program":"Computer Science",
        "academic_year":"2026-27", "admission_date":"2026-08-01", "seat_category":"regular",
        "nri":"false", "oci":"false", "foreign_national":"false"
    }])


def test_valid_record_has_no_findings():
    result = validate_records(sample())
    assert result.empty


def test_duplicate_identifier_is_flagged():
    df = pd.concat([sample(), sample().assign(student_ref="STU-2")], ignore_index=True)
    result = validate_records(df)
    assert "DUPLICATE_APAAR" in set(result.rule_code)


def test_invalid_identifier_is_flagged():
    df = sample(); df.loc[0, "apaar_id"] = "not-a-real-id"
    result = validate_records(df)
    assert "INVALID_APAAR_FORMAT" in set(result.rule_code)


def test_missing_required_column_is_handled():
    df = sample().drop(columns=["student_name"])
    result = validate_records(df)
    assert "MISSING_STUDENT_NAME" in set(result.rule_code)


def test_audit_chain_verifies_and_detects_tampering():
    events = []
    prev = "GENESIS"
    for i in range(3):
        event = {"action": "TEST", "index": i}
        digest = chain_event(prev, event)
        events.append({"event": event, "previous_hash": prev, "event_hash": digest})
        prev = digest
    assert verify_audit_chain(events) == (True, None)
    events[1]["event"]["index"] = 100
    valid, index = verify_audit_chain(events)
    assert not valid and index == 1


def test_quality_score_in_range():
    df = sample()
    findings = validate_records(df)
    assert 0 <= quality_score(df, findings) <= 100
