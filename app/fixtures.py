"""Deterministic synthetic examples. No customer records or proprietary schemas."""
from copy import deepcopy

ROLLOUT_ID = "nordtal-november"
DEMO_TIME = "2026-11-06T09:00:00+01:00"


def event(eid, kind, title, source, body, time="2026-11-05T15:42:00+01:00", **fields):
    return dict(id=eid, type=kind, title=title, source=source, occurredAt=time,
                body=body, fields=fields)


def scope(case):
    r = case["relationship"]
    return "|".join([r["buyerId"], case["supplier"]["number"], r["siteId"], r["workflow"]])


def base(cid, name, number, site, code, kind, owner="Maya Roth"):
    contact = dict(name="Anna Becker", email="a.becker@weser-components.example")
    return dict(
        id=cid, rolloutId=ROLLOUT_ID, caseType=kind, owner=owner,
        supplier=dict(name=name, number=number, site=site, country="Germany", commodity="Precision components"),
        relationship=dict(buyerId="nordtal", buyerName="Nordtal Motion GmbH", plant="Leipzig · LEI-01",
                          siteId=code, workflow="Purchase-order confirmation"),
        sourceSnapshot=dict(source="Customer ERP export", importedAt="2026-11-02T10:00:00+01:00",
                            lastEditedAt="2024-09-18", contact=deepcopy(contact), readOnly=True),
        initialContact=deepcopy(contact), candidate=None, events=[], tasks=[], verifications=[], requests=[],
        registered=False, testPassed=False, version=1, evidenceVersion=1,
    )


def seed_cases():
    main = base("weser", "Weser Precision Components GmbH", "310184", "Bremen", "BRE", "contact")
    main["candidate"] = dict(name="Tom Keller", email="orders.bremen@weser-components.example")
    main["events"] = [
        event("E01", "erp_import", "Supplier record imported", "Customer ERP export",
              "Supplier 310184 · Bremen · Anna Becker. Last edited 18 September 2024.",
              "2026-11-02T10:00:00+01:00"),
        event("E02", "bounce", "First invitation did not arrive", "Mail delivery service",
              "550 5.1.1: recipient mailbox not found. This does not establish that Anna left the company.",
              "2026-11-03T09:14:00+01:00", recipient=main["initialContact"]["email"]),
        event("E03", "bounce", "Second attempt also failed", "Mail delivery service",
              "The same address returned a mailbox-not-found error. No successful delivery to this mailbox was observed.",
              "2026-11-05T08:31:00+01:00", recipient=main["initialContact"]["email"]),
        event("E04", "record_conflict", "A newer spreadsheet has no site", "Buyer rollout spreadsheet",
              "Edited 28 October: service@weser-components.example. Site is blank. Newer does not mean verified.",
              "2026-11-05T10:00:00+01:00"),
        event("E05", "referral", "The reply refers to a different team", "Supplier email · reviewed synthetic annotation",
              "This inbox supports our Hamburg repair operation. We do not handle Bremen production orders for Nordtal. "
              "Please check with Tom Keller at orders.bremen@weser-components.example. He may be the right person.",
              candidate=deepcopy(main["candidate"]), reportedSite="Hamburg"),
        event("E06", "note", "Consultant requests verification", "Maya Roth · case note",
              "Two bounces and a wrong-site reply. Ask Lena to verify Tom through an existing approved supplier channel. "
              "Do not overwrite the approved record.", "2026-11-06T08:45:00+01:00"),
    ]
    unresolved = base("havel", "Havel Forming GmbH", "310227", "Potsdam", "POT", "contact", "Lena Hoffmann")
    unresolved["initialContact"] = dict(name="Former team inbox", email="sales.old@havel-forming.example")
    unresolved["sourceSnapshot"]["contact"] = deepcopy(unresolved["initialContact"])
    unresolved["candidate"] = dict(name="Eva Stein", email="e.stein@havel-forming.example")
    unresolved["events"] = [
        event("H01", "bounce", "Invitation delivery failed", "Mail delivery service", "550 5.1.1: mailbox not found."),
        event("H02", "referral", "A contact is suggested, authority unclear", "Supplier email · reviewed synthetic annotation",
              "Eva may know this account. We cannot confirm which site she handles.", candidate=deepcopy(unresolved["candidate"])),
        event("H03", "note", "Existing channel could not confirm ownership", "Buyer case note",
              "Lena's existing contact could not confirm Eva's authority. Record an inconclusive result and keep the case open."),
    ]
    unanswered = base("elbe", "Elbe Surface Technologies GmbH", "310302", "Dresden", "DRE", "unanswered")
    unanswered["initialContact"] = dict(name="Julia Weber", email="orders@elbe-surface.example")
    unanswered["sourceSnapshot"]["contact"] = deepcopy(unanswered["initialContact"])
    unanswered["events"] = [
        event("L01", "delivered", "Invitation accepted by receiving mail server", "Mail delivery service",
              "Delivery accepted on 3 November. This is not proof that a person read it.", "2026-11-03T11:20:00+01:00"),
        event("L02", "note", "No registration event recorded", "Onboarding activity snapshot",
              "No reply or registration is observed in this synthetic snapshot. There is no evidence of an invalid contact."),
    ]
    technical = base("rhein", "Rhein Castings GmbH", "310416", "Koblenz", "KOB", "technical")
    technical["initialContact"] = dict(name="Marco Wolf", email="supply@rhein-castings.example")
    technical["sourceSnapshot"]["contact"] = deepcopy(technical["initialContact"])
    technical["registered"] = True
    technical["events"] = [
        event("R01", "registered", "Registration completed", "Onboarding activity", "Participation role recorded. No administrator rights implied."),
        event("R02", "test_failed", "Confirmation test rejected", "Synthetic test harness",
              "TEST_UOM_UNKNOWN: incoming unit 'pieces' has no approved mapping. A technical investigation is needed. "
              "This invented error is not a SupplyOn error code.", fixtureError="TEST_UOM_UNKNOWN"),
    ]
    cases = [main, unresolved, unanswered, technical]
    names = ["Alder Fasteners", "Baltic Assemblies", "Cobalt Plastics", "Donau Seals", "Eifel Tools", "Falken Electronics",
             "Grove Bearings", "Harz Springs", "Isar Moulding", "Jade Metals", "Kronen Cable", "Linden Sensors",
             "Moorberg Stamping", "Neckar Gears", "Oder Coatings", "Pine Motion", "Quarz Ceramics", "Riedel Valves",
             "Saale Machining", "Tannberg Rubber", "Ufer Packaging", "Vega Drives", "Wald Alloy", "Xeno Filtration",
             "Yard Industrial", "Zephyr Cooling"]
    for i, name in enumerate(names):
        c = base(f"reference-{i+1:02}", f"{name} GmbH", str(311000+i), "Main production site", f"S{i+1:02}", "reference")
        c["initialContact"] = dict(name="Supplier order desk", email=f"orders@supplier-{i+1:02}.example")
        c["sourceSnapshot"]["contact"] = deepcopy(c["initialContact"])
        c["registered"] = i % 3 != 0
        c["testPassed"] = i % 3 == 1
        c["events"] = [event(f"B{i+1:02}", "reference", "Rollout snapshot", "Synthetic background fixture",
            "Reference supplier for rollout context. No modeled exception or additional workflow.")]
        cases.append(c)
    return cases
