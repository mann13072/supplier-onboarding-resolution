"""Business decisions are explicit rules. Free text never grants authority."""
from typing import Protocol


class RuleError(Exception):
    def __init__(self, message, status=409):
        self.message, self.status = message, status


class SummaryProvider(Protocol):
    def summarize(self, case: dict) -> dict: ...


class RuleBasedSummary:
    def summarize(self, c):
        events = c["events"]
        facts = []
        bounces = [e["id"] for e in events if e["type"] == "bounce"]
        referrals = [e["id"] for e in events if e["type"] == "referral"]
        if bounces:
            facts.append(dict(text=f"{len(bounces)} invitation delivery failure(s) recorded.", evidenceIds=bounces))
        if referrals:
            facts.append(dict(text="A contact was suggested in a supplier reply. This is a referral, not verified authority.", evidenceIds=referrals))
        for kind, text in [("delivered", "The receiving mail server accepted the invitation. Human readership is unknown."),
                           ("registered", "A registration event is recorded."),
                           ("test_failed", "A transaction test failed; the technical result requires investigation."),
                           ("test_passed", "The first synthetic test confirmation passed.")]:
            ids = [e["id"] for e in events if e["type"] == kind]
            if ids:
                facts.append(dict(text=text, evidenceIds=ids))
        verified = latest_verification(c)
        if verified:
            facts.append(dict(text=f"Lena recorded a {verified['outcome']} verification result for this scope.", evidenceIds=[verified["evidenceId"]]))
        req = c["requests"][-1] if c["requests"] else None
        if c["caseType"] == "reference":
            return dict(provider="Rule-based assessment", category="No modeled exception", severity="neutral",
                        facts=[dict(text="Background rollout record; no resolution workflow is modeled.", evidenceIds=[events[0]["id"]])],
                        unknowns=["This is a reference supplier, not an independently validated readiness assessment."],
                        nextAction="No action in this demonstration", taskType=None, canPropose=False)
        if c["caseType"] == "technical":
            return dict(provider="Rule-based assessment", category="Technical investigation", severity="danger", facts=facts,
                        unknowns=["Root cause and approved unit mapping require a technical owner."],
                        nextAction="Create a technical investigation task", taskType="investigate_technical", canPropose=False)
        if c["caseType"] == "unanswered":
            return dict(provider="Rule-based assessment", category="Participation follow-up", severity="warning", facts=facts,
                        unknowns=["Whether the contact has read the invitation.", "Why no participation event has been recorded."],
                        nextAction="Ask the relationship owner to follow up", taskType="follow_up", canPropose=False)
        accepted = req and req["status"] == "accepted"
        confirmed = verified and verified["outcome"] == "confirmed"
        if accepted:
            category, severity, action = "Contact blocker resolved", "success", "Await independent participation events"
        elif req and req["status"] == "rejected":
            category, severity, action = "Update rejected", "danger", "Review the receiving-system rejection with the record owner"
        elif req and req["status"] == "approved":
            category, severity, action = "Approved · processing pending", "info", "Process the approved request in the demo registry"
        elif req and req["status"] == "stale":
            category, severity, action = "Review required again", "warning", "Review the latest evidence before approving again"
        elif confirmed:
            category, severity, action = "Verification recorded", "info", "Review a relationship-scoped contact correction"
        else:
            category, severity, action = "Contact verification required", "warning", "Ask Lena to verify the referred contact"
        unknowns = [] if confirmed else ["The candidate's authority for this buyer, supplier site, and workflow."]
        if not c["registered"]:
            unknowns.append("Supplier participation has not been observed; it cannot be inferred from a contact correction.")
        return dict(provider="Rule-based assessment", category=category, severity=severity, facts=facts,
                    unknowns=unknowns, nextAction=action, taskType=None if confirmed or accepted else "verify_contact",
                    canPropose=bool(confirmed and not req))


def latest_verification(c):
    return c["verifications"][-1] if c["verifications"] else None


def milestone(c):
    if c["testPassed"]:
        return "First test completed"
    if c["registered"]:
        return "Registered · test pending"
    if c["caseType"] == "contact":
        return "Invitation delivery failed"
    if c["caseType"] == "unanswered":
        return "Invited · no response observed"
    return "Invitation recorded"


def require(condition, message, status=409):
    if not condition:
        raise RuleError(message, status)
