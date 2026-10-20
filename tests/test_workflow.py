from copy import deepcopy
import json

import pytest
from fastapi.testclient import TestClient

from app.api import create_app


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path / "cases.sqlite3", static_dir=tmp_path / "not-built")) as c:
        yield c


def get(client, cid="weser"):
    response = client.get(f"/api/cases/{cid}")
    assert response.status_code == 200
    return response.json()


def write(client, path, c, **data):
    response = client.post(path, json={"expectedVersion": c["version"], **data})
    assert response.status_code == 200, response.text
    return response.json()


def verify(client, c, outcome="confirmed", **overrides):
    data = dict(candidateEmail=c["candidate"]["email"], scopeKey=c["scopeKey"], outcome=outcome,
                method="approved_phone", note="Lena used the existing approved phone contact and confirmed the buyer, site, and workflow.")
    data.update(overrides)
    return write(client, f"/api/cases/{c['id']}/verifications", c, **data)


def proposal(client, c):
    return write(client, f"/api/cases/{c['id']}/change-requests", c,
                 scopeKey=c["scopeKey"], candidateEmail=c["candidate"]["email"])


def approval(client, c):
    return write(client, f"/api/change-requests/{c['requests'][-1]['id']}/approve", c,
                 note="Maya reviewed the latest verification, evidence, contact, and exact relationship scope.")


def process(client, c):
    return write(client, f"/api/change-requests/{c['requests'][-1]['id']}/process-demo", c)


def test_one_representative_end_to_end(client):
    c = get(client)
    original = deepcopy(c["sourceSnapshot"])
    other = get(client, "havel")["currentContact"]
    c = write(client, "/api/cases/weser/tasks", c, type="verify_contact", title="Verify Tom's operational scope",
              note="Please confirm Tom for the Bremen production orders through the existing approved contact route.", dueDate="2026-11-09")
    assert c["tasks"][0]["status"] == "open"
    c = verify(client, c)
    assert c["tasks"][0]["status"] == "completed"
    c = proposal(client, c)
    assert c["requests"][0]["status"] == "pending_review"
    assert c["currentContact"]["name"] == "Anna Becker"
    c = approval(client, c)
    assert c["currentContact"]["name"] == "Anna Becker"
    c = process(client, c)
    assert c["currentContact"]["name"] == "Tom Keller"
    assert c["sourceSnapshot"] == original
    assert get(client, "havel")["currentContact"] == other
    assert not c["registered"] and not c["testPassed"]
    c = write(client, "/api/demo/cases/weser/events", c, type="registered")
    assert c["registered"] and not c["testPassed"]
    c = write(client, "/api/demo/cases/weser/events", c, type="test_passed")
    assert c["milestone"] == "First test completed"
    assert len(c["audit"]) == 8
    assert get(client)["testPassed"]


def test_unverified_referral_cannot_propose(client):
    c = get(client)
    response = client.post("/api/cases/weser/change-requests", json={"expectedVersion": c["version"],
        "scopeKey": c["scopeKey"], "candidateEmail": c["candidate"]["email"]})
    assert response.status_code == 409
    assert not get(client)["requests"]


def test_inconclusive_verification_remains_blocked(client):
    c = verify(client, get(client, "havel"), "inconclusive")
    assert c["assessment"]["category"] == "Contact verification required"
    assert not c["assessment"]["canPropose"]
    assert c["currentContact"]["name"] == "Former team inbox"


@pytest.mark.parametrize("bad", [{"scopeKey": "nordtal|310184|WRONG|workflow"}, {"candidateEmail": "another@other.example"}])
def test_scope_and_candidate_are_checked(client, bad):
    c = get(client)
    response = client.post("/api/cases/weser/verifications", json={"expectedVersion": c["version"],
        "scopeKey": c["scopeKey"], "candidateEmail": c["candidate"]["email"], "outcome": "confirmed",
        "method": "approved_phone", "note": "A synthetic verified attestation with adequate details.", **bad})
    assert response.status_code == 409
    assert get(client)["version"] == 1
    assert len(get(client)["audit"]) == 1


def test_stale_review_cannot_process_until_reviewed_again(client):
    c = approval(client, proposal(client, verify(client, get(client))))
    c = write(client, "/api/demo/cases/weser/events", c, type="additional_evidence")
    assert c["requests"][0]["status"] == "stale"
    response = client.post(f"/api/change-requests/{c['requests'][0]['id']}/process-demo", json={"expectedVersion": c["version"]})
    assert response.status_code == 409
    assert get(client)["currentContact"]["name"] == "Anna Becker"
    c = process(client, approval(client, c))
    assert c["currentContact"]["name"] == "Tom Keller"


def test_rejected_request_is_idempotent_and_preserves_contact(client):
    client.post("/api/demo/reset", json={"variant": "rejected"})
    c = approval(client, proposal(client, verify(client, get(client))))
    old_version = c["version"]
    c = process(client, c)
    audit_count = len(c["audit"])
    assert c["requests"][0]["status"] == "rejected"
    assert c["currentContact"]["name"] == "Anna Becker"
    assert not c["registered"]
    response = client.post(f"/api/change-requests/{c['requests'][0]['id']}/process-demo", json={"expectedVersion": old_version})
    assert response.status_code == 200
    assert len(response.json()["audit"]) == audit_count
    response = client.post("/api/demo/cases/weser/events", json={"expectedVersion": c["version"], "type": "registered"})
    assert response.status_code == 409


def test_accepted_processing_is_idempotent(client):
    c = approval(client, proposal(client, verify(client, get(client))))
    old_version = c["version"]
    c = process(client, c)
    response = client.post(f"/api/change-requests/{c['requests'][0]['id']}/process-demo", json={"expectedVersion": old_version})
    assert response.status_code == 200
    assert response.json()["version"] == c["version"]
    assert len(response.json()["audit"]) == len(c["audit"])


@pytest.mark.parametrize("cid,task_type", [("elbe", "follow_up"), ("rhein", "investigate_technical")])
def test_other_blockers_do_not_allow_contact_repair(client, cid, task_type):
    c = get(client, cid)
    assert c["assessment"]["taskType"] == task_type
    response = client.post(f"/api/cases/{cid}/tasks", json={"expectedVersion": c["version"],
        "type": "verify_contact", "title": "Incorrect intervention", "note": "This action should not match the current evidence.", "dueDate": "2026-11-09"})
    assert response.status_code == 409
    c = write(client, f"/api/cases/{cid}/tasks", c, type=task_type, title="Follow the supported intervention",
              note="Review the source evidence and investigate the actual observed blocker.", dueDate="2026-11-09")
    assert len(c["tasks"]) == 1


def test_old_case_version_cannot_change_case(client):
    old = get(client)
    verify(client, old)
    response = client.post("/api/cases/weser/tasks", json={"expectedVersion": old["version"],
        "type": "verify_contact", "title": "Stale browser request", "note": "This browser did not refresh after the other change.", "dueDate": "2026-11-09"})
    assert response.status_code == 409


def test_duplicate_task_does_not_duplicate_work(client):
    c = get(client)
    data = dict(type="verify_contact", title="Verify the referred contact", note="Check the buyer relationship, site, and contact authority.", dueDate="2026-11-09")
    c = write(client, "/api/cases/weser/tasks", c, **data)
    response = client.post("/api/cases/weser/tasks", json={"expectedVersion": c["version"], **data})
    assert response.status_code == 409
    assert len(get(client)["tasks"]) == 1


def test_summary_provenance_and_rollout_counts(client):
    data = client.get("/api/rollouts/nordtal-november").json()
    assert len(data["cases"]) == 30
    assert sum(c["caseType"] != "reference" for c in data["cases"]) == 4
    for c in data["cases"]:
        ids = {e["id"] for e in c["events"]}
        assert all(set(f["evidenceIds"]) <= ids for f in c["assessment"]["facts"])


def test_reset_is_repeatable_and_clears_only_synthetic_work(client):
    c = verify(client, get(client))
    before = client.get("/api/rollouts/nordtal-november").json()
    assert before["cases"][0]["verifications"]
    result = client.post("/api/demo/reset", json={"variant": "accepted"}).json()
    assert len(result["cases"]) == 30
    assert result["cases"][0]["version"] == 1
    assert not result["cases"][0]["verifications"]


def test_persistence_across_app_instances(tmp_path):
    db = tmp_path / "persistent.sqlite3"
    with TestClient(create_app(db)) as first:
        verify(first, get(first))
    with TestClient(create_app(db)) as second:
        assert get(second)["verifications"][0]["outcome"] == "confirmed"


def test_unknown_api_not_spa_and_unbuilt_frontend_explains(client):
    assert client.get("/api/not-real").status_code == 404
    assert client.get("/").status_code == 503


def test_blank_note_rejected(client):
    c = get(client)
    response = client.post("/api/cases/weser/verifications", json={"expectedVersion": c["version"],
        "candidateEmail": c["candidate"]["email"], "scopeKey": c["scopeKey"], "outcome": "confirmed",
        "method": "approved_phone", "note": " " * 40})
    assert response.status_code == 422
