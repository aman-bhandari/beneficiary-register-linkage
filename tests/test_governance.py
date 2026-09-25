"""Masking and the tamper-evident access log."""
import sqlite3

from api.governance import ROLES, Audit, mask_fields, mask_name, mask_number, scope_sql


def test_masks():
    assert mask_name("Kamla Devi Bisht") == "K•••• D••• B••••"
    assert mask_number("234567891234", 4).endswith("1234") and "5678" not in mask_number("234567891234", 4)
    f = mask_fields({"aadhaar": "234567891234", "applicant_name": "कमला देवी", "dob": "12-03-1950", "card_no": "123456789012"}, unmasked=False)
    assert f["aadhaar"].endswith("1234") and f["applicant_name"] != "कमला देवी" and f["dob"] == "••-••-1950"
    assert f["card_no"].endswith("012") and not f["card_no"].startswith("123")
    g = mask_fields({"aadhaar": "234567891234", "applicant_name": "कमला देवी"}, unmasked=True)
    assert g["applicant_name"] == "कमला देवी" and g["aadhaar"].startswith("•"), "Aadhaar stays masked even when unmasked"


def test_scope_sql_folds_posting_into_query():
    where, params = scope_sql(ROLES["aswo_hawalbag"], "c")
    assert "c.district in" in where and "c.block in" in where and params == ["Almora", "HAWALBAG"]
    assert scope_sql(ROLES["planner"]) == ("true", [])


def test_audit_chain_verifies_and_detects_tampering(tmp_path):
    a = Audit(tmp_path / "audit.db")
    for i in range(5):
        a.log("dswo_almora", "open_case", f"ALM-{i:06d}", {"i": i})
    assert a.verify() == {"ok": True, "entries_checked": 5, "head": a.events(1)[0]["hash"]}
    con = sqlite3.connect(tmp_path / "audit.db")
    try:
        con.execute("update events set detail = '{}' where seq = 3")
        raise AssertionError("the log accepted an edit")
    except sqlite3.IntegrityError:
        pass
    # someone with file access drops the guard and edits entry 3: verification names the entry
    con.execute("drop trigger events_no_update")
    con.execute("update events set object = 'ALM-999999' where seq = 3")
    con.commit()
    res = a.verify()
    assert res["ok"] is False and res["broken_at"] == 3
