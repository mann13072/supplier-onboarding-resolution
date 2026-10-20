# Contributing

This is a bounded portfolio prototype. Useful contributions make its decisions clearer, its controls more reliable, or its interface easier to use.

## Start locally

Follow the [README setup](README.md#quick-start), then install `requirements-dev.txt` in the same virtual environment. Use Node 24 and Python 3.13 for parity with CI.

Keep a backend running with `python -m app` while using the optional `npm run dev` frontend server. Both are foreground processes; stop them when finished. The built application needs only the backend.

## Preserve the important boundaries

- Use synthetic supplier records and `.example` email addresses. Do not submit employer records, customer information, personal contact details, or credentials.
- Preserve the distinction between the ERP snapshot and the scoped onboarding-contact registry.
- Do not bypass verification, current-evidence review, or receiving-system acknowledgment.
- Keep inconclusive and rejected outcomes visible. Do not turn them into success to complete a demonstration.
- Keep all case decisions on the backend. UI availability is not the authority.
- Do not imply SupplyOn affiliation, access to its APIs, or a verified internal product gap.
- Treat a live AI adapter or enterprise connector as a separate proposal with its own evaluation plan.

## Validate a change

From an activated virtual environment:

```text
npm run build
python -m pytest -q tests/test_workflow.py
python tests/browser_smoke.py
```

Use `npm.cmd` on Windows if PowerShell blocks the `npm` script. The browser check requires Playwright and its browser dependencies; see the README.

Add or revise a meaningful test when business behavior changes. For a purely visual change, inspect desktop and mobile and run the existing relevant checks. Do not add tests that only repeat the implementation.

The browser test uses a temporary database, not normal local work. Screenshots in `test-results/` stay out of Git. Intentional README images belong in `docs/assets/` and must show only the synthetic dataset.

## Pull requests

Describe the user problem, resulting behavior, and validation. Explain changes to source ownership, allowed actions, or request processing explicitly. Keep changes narrow; update the documentation if setup, UI labels, or the demonstration sequence changes.

Use public issues for ordinary reproducible bugs or feature discussions. Follow [SECURITY.md](SECURITY.md) for reports that could expose private information.
