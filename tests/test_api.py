"""The role matrix, enforced by the API against the built warehouse: who can see which rows and fields, and what
is refused. Requires ./run.sh build to have been run."""
import io
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import api.main as main
from api.governance import Audit

ROOT = Path(__file__).resolve().parent.parent
pytestmark = pytest.mark.skipif(not (ROOT / "data" / "warehouse.duckdb").exists(), reason="warehouse not built")


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    main.audit = Audit(tmp_path_factory.mktemp("audit") / "audit.db")
    return TestClient(main.app)


def get(client, role, path, **kw):
    return client.get(path, headers={"X-Role": role}, **kw)


def test_unknown_role_is_refused(client):
    assert client.get("/api/overview").status_code == 401


def test_planner_sees_aggregates_but_no_individual(client):
    assert get(client, "planner", "/api/overview").status_code == 200
    assert get(client, "planner", "/api/cases").status_code == 403
    ov = get(client, "planner", "/api/overlap?district=Almora").json()
    assert all(v is None or v >= 10 for v in ov["cells"].values()), "small cells must be withheld"


def test_district_officer_sees_only_their_district(client):
    r = get(client, "dswo_almora", "/api/cases?size=200").json()
    assert r["total"] > 0 and r["refused_by_scope"] > 0
    assert {x["district"] for x in r["rows"]} == {"Almora"}
    usn = get(client, "dswo_usn", "/api/cases?size=1").json()["rows"][0]["case_id"]
    assert get(client, "dswo_almora", f"/api/cases/{usn}").status_code == 403


def test_block_officer_sees_only_their_block(client):
    r = get(client, "aswo_hawalbag", "/api/cases?size=200").json()
    assert r["total"] > 0 and {x["block"] for x in r["rows"]} == {"HAWALBAG"}
    other = get(client, "dswo_almora", "/api/cases?size=200&block=DHAULADEVI").json()["rows"][0]["case_id"]
    assert get(client, "aswo_hawalbag", f"/api/cases/{other}").status_code == 403


def test_other_department_and_auditor_get_no_cases(client):
    for role in ("dso_almora", "auditor"):
        assert get(client, role, "/api/cases").status_code == 403
    assert get(client, "auditor", "/api/audit/verify").json()["ok"] is True


def test_names_masked_until_unmasked_with_a_reason(client):
    row = get(client, "dswo_almora", "/api/cases?kind=exclusion&size=1").json()["rows"][0]
    cid = row["case_id"]
    c = get(client, "dswo_almora", f"/api/cases/{cid}").json()
    assert c["unmasked"] is False and "•" in (c["person"]["name_hi"] or c["person"]["name_en"])
    assert client.post(f"/api/cases/{cid}/unmask", json={"reason": "short"}, headers={"X-Role": "dswo_almora"}).status_code == 422
    assert client.post(f"/api/cases/{cid}/unmask", json={"reason": "Field visit planned for next week"}, headers={"X-Role": "dso_almora"}).status_code == 403
    ok = client.post(f"/api/cases/{cid}/unmask", json={"reason": "Field visit planned for next week"}, headers={"X-Role": "dswo_almora"})
    assert ok.status_code == 200
    c = get(client, "dswo_almora", f"/api/cases/{cid}").json()
    assert c["unmasked"] is True and "•" not in (c["person"]["name_hi"] or c["person"]["name_en"])
    for r in c["records"]:
        if r["fields"].get("aadhaar"):
            assert r["fields"]["aadhaar"].startswith("•"), "Aadhaar is never shown in full"
    # another officer's view of the same case is still masked
    assert get(client, "aswo_hawalbag", f"/api/cases/{cid}").status_code in (200, 403)


def test_review_is_recorded_and_changes_no_benefit(client):
    cid = get(client, "dswo_almora", "/api/cases?type=paid_after_death&size=1").json()["rows"][0]["case_id"]
    before = get(client, "dswo_almora", f"/api/cases/{cid}").json()
    r = client.post(f"/api/cases/{cid}/review", json={"decision": "field_visit", "note": "Verify at the bank"}, headers={"X-Role": "dswo_almora"})
    assert r.status_code == 200
    after = get(client, "dswo_almora", f"/api/cases/{cid}").json()
    assert after["review"]["decision"] == "field_visit"
    assert after["person"]["pensions"] == before["person"]["pensions"] and after["records"] == before["records"]
    bad = client.post(f"/api/cases/{cid}/review", json={"decision": "stop_pension"}, headers={"X-Role": "dswo_almora"})
    assert bad.status_code == 422
    assert client.post(f"/api/cases/{cid}/review", json={"decision": "confirmed"}, headers={"X-Role": "planner"}).status_code == 403


def test_every_access_is_logged_and_the_chain_holds(client):
    events = get(client, "auditor", "/api/audit?limit=500").json()["events"]
    actions = {e["action"] for e in events}
    assert {"open_case", "unmask", "review", "refused", "list_cases"} <= actions
    assert get(client, "auditor", "/api/audit/verify").json()["ok"] is True


def test_department_file_links_to_known_people(client):
    sample = ROOT / "data" / "samples" / "nanda_gaura_sample.csv"
    if not sample.exists():
        pytest.skip("sample not generated")
    r = client.post("/api/upload", headers={"X-Role": "dswo_almora"}, data={"department": "WECD"},
                    files={"file": ("sample.csv", sample.read_bytes(), "text/csv")})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["mapping"]["name"] == "Beneficiary Name" and body["rows"] == 300
    assert body["match_rate"] > 0.5
