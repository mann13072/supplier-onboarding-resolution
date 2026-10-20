from pathlib import Path
from typing import Literal
from datetime import date
import os

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from .domain import RuleError, RuleBasedSummary, latest_verification, require
from .fixtures import DEMO_TIME, ROLLOUT_ID, event, scope
from .store import Store

ROOT = Path(__file__).resolve().parent.parent


class Body(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Mutation(Body):
    expectedVersion: int = Field(ge=1)


class TaskBody(Mutation):
    type: Literal["verify_contact", "follow_up", "investigate_technical"]
    title: str = Field(min_length=5, max_length=160)
    note: str = Field(min_length=15, max_length=3000)
    dueDate: date


class VerificationBody(Mutation):
    candidateEmail: str = Field(min_length=3, max_length=250)
    scopeKey: str
    outcome: Literal["confirmed", "inconclusive", "not_confirmed"]
    method: Literal["approved_phone", "existing_account_contact"]
    note: str = Field(min_length=24, max_length=3000)


class ProposalBody(Mutation):
    scopeKey: str
    candidateEmail: str


class ReviewBody(Mutation):
    note: str = Field(min_length=12, max_length=3000)


class DemoEventBody(Mutation):
    type: Literal["additional_evidence", "registered", "test_passed"]


class ResetBody(Body):
    variant: Literal["accepted", "rejected"]


def create_app(db_path=None, static_dir=None):
    app = FastAPI(title="Onboarding resolution · independent local prototype", docs_url="/api/docs")
    store = Store(db_path or os.getenv("ONBOARDING_DB", str(ROOT / "data" / "prototype.sqlite3")))
    app.state.store = store

    @app.exception_handler(RuleError)
    async def rule_error(request: Request, exc: RuleError):
        return JSONResponse(status_code=exc.status, content={"detail": exc.message})

    @app.get("/api/health")
    def health():
        return {"status": "ok", "environment": "local synthetic prototype", "liveIntegrations": False}

    @app.get("/api/rollouts/{rid}")
    def rollout(rid: str):
        require(rid == ROLLOUT_ID, "Rollout not found.", 404)
        return store.rollout()

    @app.get("/api/cases/{cid}")
    def case(cid: str):
        return store.get(cid)

    @app.post("/api/cases/{cid}/tasks")
    def task(cid: str, body: TaskBody):
        def change(c, db):
            assessment = RuleBasedSummary().summarize(c)
            require(body.type == assessment["taskType"], "This task does not address the observed blocker.")
            require(not any(t["type"] == body.type and t["status"] == "open" for t in c["tasks"]),
                    "An open task of this type already exists. Review it rather than creating a duplicate.")
            owner = "Pavel Fischer · integration specialist" if body.type == "investigate_technical" else "Lena Hoffmann"
            c["tasks"].append(dict(id=f"task-{cid}-{len(c['tasks'])+1}", type=body.type, title=body.title,
                note=body.note, dueDate=body.dueDate.isoformat(), assignee=owner, status="open",
                evidenceIds=[e["id"] for e in c["events"]], createdBy="Maya Roth"))
            c["owner"] = owner
            return f"Task assigned to {owner}. No email sent."
        return store.mutate(cid, body.expectedVersion, "Maya Roth", "Task created", change)

    @app.post("/api/cases/{cid}/verifications")
    def verify(cid: str, body: VerificationBody):
        def change(c, db):
            require(c["caseType"] == "contact" and c["candidate"], "No candidate contact is awaiting verification.")
            require(not any(r["status"] in ("accepted", "rejected") for r in c["requests"]),
                    "This request has already been processed. Reset the synthetic case to replay it.")
            require(body.scopeKey == scope(c), "Verification scope does not match this buyer, site, and workflow.")
            require(body.candidateEmail.casefold() == c["candidate"]["email"].casefold(),
                    "The verification does not refer to this candidate.")
            eid = f"V{len(c['verifications'])+1:02}"
            v = dict(id=f"verification-{cid}-{len(c['verifications'])+1}", candidate=dict(c["candidate"]),
                     scopeKey=body.scopeKey, outcome=body.outcome, method=body.method, note=body.note,
                     verifier="Lena Hoffmann", evidenceId=eid, recordedAt=DEMO_TIME)
            c["verifications"].append(v)
            c["events"].append(event(eid, "verification", f"Buyer verification: {body.outcome.replace('_',' ')}",
                "Lena Hoffmann · recorded synthetic attestation", body.note, DEMO_TIME, outcome=body.outcome))
            c["evidenceVersion"] += 1
            for req in c["requests"]:
                if req["status"] in ("approved", "pending_review", "stale"):
                    req["status"] = "stale"
            if body.outcome == "confirmed":
                c["owner"] = "Maya Roth"
                for t in c["tasks"]:
                    if t["type"] == "verify_contact":
                        t["status"] = "completed"
            return f"{body.outcome} verification recorded for {body.scopeKey}; no contact changed."
        return store.mutate(cid, body.expectedVersion, "Lena Hoffmann (recorded)", "Verification recorded", change)

    @app.post("/api/cases/{cid}/change-requests")
    def propose(cid: str, body: ProposalBody):
        def change(c, db):
            v = latest_verification(c)
            require(c["caseType"] == "contact" and v and v["outcome"] == "confirmed", "Confirmed scoped verification is required.")
            require(body.scopeKey == scope(c) == v["scopeKey"], "Request scope does not match the verified relationship.")
            require(body.candidateEmail.casefold() == v["candidate"]["email"].casefold(), "Candidate differs from the verified contact.")
            require(not c["requests"], "A correction request already exists. Review that request.")
            current = store.view(db, c)["currentContact"]
            c["requests"].append(dict(id=f"request-{cid}-01", candidate=dict(c["candidate"]), previousContact=current,
                scopeKey=scope(c), verificationId=v["id"], status="pending_review", approvedEvidenceVersion=None,
                reviewedBy=None, reviewNote=None, result=None))
            return "Scoped correction proposed to the synthetic onboarding relationship-contact registry. ERP unchanged."
        return store.mutate(cid, body.expectedVersion, "Maya Roth", "Correction requested", change)

    def find_request(rid):
        with store.connection() as db:
            import json
            for row in db.execute("SELECT payload FROM cases"):
                c = json.loads(row[0])
                if any(r["id"] == rid for r in c["requests"]):
                    return c["id"]
        raise RuleError("Correction request not found.", 404)

    @app.post("/api/change-requests/{rid}/approve")
    def approve(rid: str, body: ReviewBody):
        cid = find_request(rid)
        def change(c, db):
            req = next(r for r in c["requests"] if r["id"] == rid)
            v = latest_verification(c)
            require(req["status"] in ("pending_review", "stale"), "Only a pending or stale request can be reviewed.")
            require(v and v["outcome"] == "confirmed" and v["scopeKey"] == req["scopeKey"] == scope(c),
                    "Current confirmed verification is required before approval.")
            require(v["candidate"] == req["candidate"], "The request no longer matches the verified candidate.")
            req.update(status="approved", approvedEvidenceVersion=c["evidenceVersion"],
                       reviewedBy="Maya Roth", reviewNote=body.note, verificationId=v["id"])
            return "Maya reviewed current evidence. Request approved; receiving system has not applied it."
        return store.mutate(cid, body.expectedVersion, "Maya Roth", "Review approved", change)

    @app.post("/api/change-requests/{rid}/process-demo")
    def process(rid: str, body: Mutation):
        cid = find_request(rid)
        def already(c):
            return next(r for r in c["requests"] if r["id"] == rid)["status"] in ("accepted", "rejected")
        def change(c, db):
            import json
            req = next(r for r in c["requests"] if r["id"] == rid)
            require(req["status"] == "approved", "Review and approve the current request before processing.")
            require(req["approvedEvidenceVersion"] == c["evidenceVersion"], "Evidence changed after approval. Review again.")
            variant = db.execute("SELECT value FROM settings WHERE key='variant'").fetchone()[0]
            if variant == "rejected":
                req.update(status="rejected", result="DEMO_SCOPE_LOCKED: receiving registry requires owner clarification. No contact changed.")
            else:
                db.execute("UPDATE contacts SET payload=? WHERE scope=?", (json.dumps(req["candidate"]), req["scopeKey"]))
                req.update(status="accepted", result="DEMO_ACK: scoped onboarding contact updated. ERP source snapshot unchanged.")
            return req["result"]
        return store.mutate(cid, body.expectedVersion, "Synthetic registry adapter", "Update processed", change, idempotent=already)

    @app.post("/api/demo/cases/{cid}/events")
    def demo_event(cid: str, body: DemoEventBody):
        def change(c, db):
            require(c["caseType"] == "contact", "No milestone simulation is modeled for this case.")
            req = c["requests"][-1] if c["requests"] else None
            if body.type == "additional_evidence":
                require(req and req["status"] in ("approved", "pending_review", "stale"), "Create a request first to demonstrate a stale review.")
                eid = f"N{len(c['events'])+1:02}"
                c["events"].append(event(eid, "note", "Additional buyer evidence received", "Buyer case note · synthetic event",
                    "Buyer confirms the same Bremen scope. This additional evidence must be reviewed before processing.", DEMO_TIME))
                c["evidenceVersion"] += 1
                req["status"] = "stale"
                return "Additional evidence recorded. Previous review invalidated; no registry change."
            require(req and req["status"] == "accepted", "An accepted contact update is required before simulating participation.")
            if body.type == "registered":
                require(not c["registered"], "Registration is already recorded.")
                c["registered"] = True
                c["events"].append(event("REG01", "registered", "Supplier registration observed", "Synthetic onboarding activity",
                    "Tom completed the fictional registration and guidance process. No live account created.", "2026-11-09T14:00:00+01:00"))
            else:
                require(c["registered"] and not c["testPassed"], "Record registration before the first test confirmation.")
                c["testPassed"] = True
                c["events"].append(event("TEST01", "test_passed", "First test confirmation passed", "Synthetic test harness",
                    "Supplier 310184 · PO 4500062718 · 1,200 units · 23 November 2026 · buyer test receipt observed. "
                    "Production go-live remains separately approved.", "2026-11-10T10:15:00+01:00"))
            c["evidenceVersion"] += 1
            return "Independent synthetic milestone recorded. No production activation."
        return store.mutate(cid, body.expectedVersion, "Demonstration controls", "Synthetic event added", change)

    @app.post("/api/demo/reset")
    def reset(body: ResetBody):
        store.reset(body.variant)
        return store.rollout()

    # Never return the SPA document for a missing API route or missing asset.
    @app.api_route("/api/{unmatched:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
    def unknown_api(unmatched: str):
        raise RuleError("API route not found.", 404)

    dist = Path(static_dir) if static_dir else ROOT / "dist"
    if (dist / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

    @app.get("/{path:path}")
    def frontend(path: str):
        index = dist / "index.html"
        if not index.is_file():
            return JSONResponse(status_code=503, content={"detail": "Frontend not built. Run npm.cmd run build first."})
        if path and not path.startswith("supplier-management"):
            raise RuleError("Page not found.", 404)
        return FileResponse(index)

    return app


app = create_app()
