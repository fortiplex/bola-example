# bola-example

A Python FastAPI backend modeled on a Calendly-for-Teams scheduling SaaS, plus a set of branches that each introduce one Broken Object Level Authorization (BOLA) vulnerability. Every vuln has a syntactically present authorization check; the bug is in semantic intent. They are chosen to evade conventional SAST and AI-assisted SAST.

**⚠ Do not deploy any branch of this project anywhere public.**

## Setup

See [`CLAUDE.md`](./CLAUDE.md).

## Branches

| Branch | Vulnerability | PoC |
|---|---|---|
| `main` | (clean baseline — no vulns) | — |
| `bola/uuid-slug-skip` | Host-detail endpoint trusts UUID-as-capability | [`docs/vulnerabilities/uuid-slug-skip.md`](docs/vulnerabilities/uuid-slug-skip.md) |
| `bola/parent-only-auth` | Listing checks org membership but not booking host | [`docs/vulnerabilities/parent-only-auth.md`](docs/vulnerabilities/parent-only-auth.md) |
| `bola/cached-owner` | Ownership LRU cache not invalidated on transfer | [`docs/vulnerabilities/cached-owner.md`](docs/vulnerabilities/cached-owner.md) |
| `bola/composite-key-mismatch` | Scoped admin endpoint doesn't verify resource scope | [`docs/vulnerabilities/composite-key-mismatch.md`](docs/vulnerabilities/composite-key-mismatch.md) |
| `bola/share-token-confused-deputy` | Reschedule endpoint uses body-supplied booking_id | [`docs/vulnerabilities/share-token-confused-deputy.md`](docs/vulnerabilities/share-token-confused-deputy.md) |
| `bola/all` | All five merged together (convenience for batch scans) | (see individual PoCs above) |
