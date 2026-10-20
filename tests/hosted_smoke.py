"""Run existing acceptance scenarios against a deployed synthetic API.

Run: python tests/hosted_smoke.py https://supplier-onboarding-resolution.vercel.app
Uses isolated anonymous sessions and restores their fixtures when finished.
"""
import sys
from pathlib import Path
from uuid import uuid4

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from test_workflow import (
    test_one_representative_end_to_end,
    test_stale_review_cannot_process_until_reviewed_again,
    test_rejected_request_is_idempotent_and_preserves_contact,
    test_blank_note_rejected,
    test_old_case_version_cannot_change_case,
)


def main():
    base = sys.argv[1].rstrip("/")
    session = str(uuid4())
    with httpx.Client(base_url=base, headers={"X-Demo-Session": session}, timeout=60) as client:
        health = client.get("/api/health")
        health.raise_for_status()
        assert health.json()["status"] == "ok"
        try:
            for check in (
                test_one_representative_end_to_end,
                test_stale_review_cannot_process_until_reviewed_again,
                test_rejected_request_is_idempotent_and_preserves_contact,
                test_blank_note_rejected,
                test_old_case_version_cannot_change_case,
            ):
                client.post("/api/demo/reset", json={"variant": "accepted"}).raise_for_status()
                check(client)
                print(f"PASS {check.__name__}")
            with httpx.Client(base_url=base, headers={"X-Demo-Session": session}, timeout=60) as reloaded:
                assert reloaded.get("/api/cases/weser").json()["verifications"]
            with httpx.Client(base_url=base, headers={"X-Demo-Session": str(uuid4())}, timeout=60) as visitor:
                case = visitor.get("/api/cases/weser").json()
                assert case["version"] == 1 and not case["verifications"]
            print("PASS persistence across clients and visitor isolation")
        finally:
            client.post("/api/demo/reset", json={"variant": "accepted"}).raise_for_status()


if __name__ == "__main__":
    main()
