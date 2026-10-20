# Security and data boundaries

## Intended use

This repository is a local, single-user portfolio prototype with synthetic data. It is not a production service. No supported production release or security certification is claimed.

The server binds to `127.0.0.1`. Do not expose it to the Internet or a shared network without designing authentication, authorization, tenancy, privacy controls, operational monitoring, and deployment protection first.

## What the controls do

The backend checks case versions, evidence freshness, candidate scope, recorded verification, and approved request state. SQLite commits business changes with their audit entries. Accepted and rejected processing is idempotent.

Those business checks do not establish a person's identity. Actor labels are demonstration metadata. A verification note is an attestation entered by a user, not an independent authority check.

The audit is append-only through normal application operations, not cryptographically tamper-proof. Demo reset intentionally clears synthetic work. Anyone controlling the local files can edit the database or source.

## Keep private material out of the repository

Use synthetic records and `.example` addresses. Local databases, environment files, logs, dependencies, and test captures are ignored by Git. Do not force-add them or upload customer screenshots, credentials, mailbox exports, or real contact records in issues.

There are no application API keys to configure. Dependency installation downloads packages; the normal demonstration does not send business records to an external API.

## Reporting

Use GitHub's private vulnerability reporting option if the repository owner enables it. Otherwise, contact the maintainer through the contact method published on their GitHub profile before sending sensitive evidence. No dedicated reporting address or response-time commitment is currently established.

For ordinary bugs using only synthetic data, a public issue is appropriate. Include the affected version, steps, and expected behavior. Do not publish secrets or private records as proof.
