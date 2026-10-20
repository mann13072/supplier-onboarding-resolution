# Demo guide

## What to demonstrate

Show a controlled intervention inside a supplier record. The important question is: **does the next action follow from the evidence, and does the application preserve the difference between a decision and a successful update?**

All companies, people, dates, events, and transaction results are synthetic. Public SupplyOn material establishes the problem area, not an internal feature gap.

## Starting state

Start the app using the [README](../README.md#quick-start). Open Demo controls, select **Accepted by synthetic registry**, choose **Reset synthetic rollout**, and confirm. This resets only the prototype database.

The rollout has 30 supplier relationships. Four contain substantive exception scenarios; the others provide context. The demonstration starts at a fictional snapshot on 6 November 2026.

## The primary case

### 1. Find the blocked supplier

Search for **Weser**, then open its record. Return to the rollout once to show that the selected filters persist.

Explain the roles:

- **Lena Hoffmann:** customer buyer and relationship owner.
- **Maya Roth:** onboarding consultant.
- **Anna Becker:** imported contact whose invitation mailbox failed.
- **Tom Keller:** referred Bremen contact whose authority needs verification.

The names are workflow personas, not logged-in user identities.

### 2. Inspect the evidence

Open the evidence links in Resolution assistance or the timeline:

| Evidence | Observation | What it does not establish |
|---|---|---|
| E01 | Customer ERP record lists Anna for supplier 310184, Bremen | That the old contact is still reachable |
| E02 / E03 | Two mailbox-not-found results | Supplier unwillingness or proof Anna left |
| E04 | Newer spreadsheet lists a service inbox with no site | That the newer contact is correct |
| E05 | The service desk reports another site and suggests Tom | Tom's authority for this buyer relationship |
| E06 | Maya records the unresolved verification need | Permission to update a contact |

The original text and source timestamps are inspectable. The rule-based assessment cites the same evidence. It should not describe these events as a refusal to participate.

### 3. Create the next task

Choose **Create verification task**. Inspect or edit the proposed instructions. The task asks Lena to verify the candidate through the existing approved supplier contact route and confirm the buyer, site, and workflow.

Save it. The task is persisted locally and gains an owner and due date. No message is sent. Reload the page to show the work remains present.

### 4. Record verification

Choose **Record buyer verification**. Use **Insert this case's synthetic example** to populate the fictional response, inspect it, and record it.

The note records a human attestation on Lena's behalf. The application has not checked a phone call or independently verified identity. A confirmed outcome unlocks a scoped correction proposal; it does not update the current contact.

### 5. Review a correction request

Choose **Propose contact correction**. Compare Anna with Tom and inspect the exact relationship scope. Create the request.

Choose **Review and approve request**, inspect the current evidence version, and record Maya's review note. The current onboarding contact still shows Anna. This demonstrates that approval and receiving-system acceptance are different states.

### 6. Make the review stale

Before processing, use **Demo controls → Add evidence / invalidate review**. Close the drawer.

The request becomes stale. The processing button is unavailable. The server also rejects processing if called directly. Review the new evidence and approve again.

### 7. Process the update

Choose **Process simulated update**. With the accepted scenario, the synthetic registry returns `DEMO_ACK` and Tom becomes the operational onboarding contact.

Show the two contact boxes together:

- **ERP source contact:** Anna, unchanged.
- **Current onboarding contact:** Tom, updated for this relationship only.

Open Activity to inspect the persisted decisions and result. Repeating processing cannot create another update or audit result.

### 8. Observe participation separately

In Demo controls, record registration, then first test confirmation. They are distinct actions with distinct events. The synthetic confirmation covers PO 4500062718, 1,200 units, and delivery on 23 November 2026.

Production readiness remains outside the feature. Do not describe this as a live order, a production transaction, or proof of customer savings.

## The negative examples

### Authority unresolved: Havel

Open **Havel Forming**. The supplied verification example is inconclusive. Recording it keeps the case blocked and leaves the current contact unchanged. There is no correction proposal to approve.

### Participation follow-up: Elbe

Open **Elbe Surface Technologies**. The receiving server accepted the invitation, but no participation is recorded. Create a follow-up task. There is no evidence to support contact replacement, and delivery does not prove human readership.

### Technical failure: Rhein

Open **Rhein Castings**. Registration is recorded, but the test returned the invented `TEST_UOM_UNKNOWN` result. The next action is a technical investigation. Changing contacts or repeating registration instructions would not address that evidence.

### Approved but rejected: Weser variant

Select **Rejected · scope locked** in Demo controls and reset the synthetic rollout. Replay Weser through verification and review.

Process the update. `DEMO_SCOPE_LOCKED` appears. Anna remains the current onboarding contact, and registration/test controls stay blocked. The UI does not turn a rejected update into success or retry automatically.

## Suggested presentation

> “I modeled one onboarding exception within its operational context. The feature brings evidence, ownership, verification, and request processing into the supplier record. I built a deterministic baseline first, including cases that remain unresolved or get rejected. I would want to validate the assumptions against the team's actual tools and ownership rules.”

Mann's contribution is product definition, process and domain modeling, directing AI-assisted implementation, reviewing the result, and testing its limits. Present the project on that basis.

## Refreshing the README images

After building, run:

```text
python tests/browser_smoke.py --capture-docs
```

This starts an isolated temporary database and captures the unmodified synthetic rollout and supplier record into `docs/assets/`. It does not read or reset the normal application database. Inspect the two PNGs before including them in Git.
