# Security and data boundaries

## Intended use

This repository is a portfolio prototype with synthetic data, available as a hosted demonstration and a local application. It is not a production service. No supported production release or security certification is claimed.

The local server binds to `127.0.0.1`. The public showcase uses Vercel and Cloudflare Workers with a separate SQLite-backed Durable Object for each anonymous browser identifier. The identifier is stored in localStorage and forwarded through the Vercel API proxy. This separates ordinary visitors' scenarios, but is not authentication or an authorization boundary for private data. Clearing browser storage starts another workspace. Never enter real customer, contact, or confidential records. A production deployment requires identity, authorization, privacy controls, and operational protections.

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
