# CLAUDE.md — bola-example

## Purpose

Calendly-for-Teams-style scheduling backend. The `main` branch (once merged) is the clean, authorization-correct base. Five `bola/*` branches each introduce one Broken Object Level Authorization (BOLA) vulnerability chosen specifically to evade conventional and AI-assisted SAST.

**These vulnerabilities are deliberate teaching artifacts.** Before "fixing" any code on a `bola/*` branch, confirm intent with the user — the project's value depends on those bugs being preserved.

## Setup

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # then edit JWT_SECRET to something random and >=32 chars
python seed_data.py
uvicorn app.main:app --reload
```

API at `http://127.0.0.1:8000`, Swagger at `/docs`.

## Layout

- `app/main.py` — FastAPI app, router wiring
- `app/config.py` — env-driven settings
- `app/database.py` — SQLAlchemy engine + session
- `app/models/` — SQLAlchemy ORM models
- `app/schemas/` — Pydantic request/response models
- `app/auth/` — JWT signing, password hashing
- `app/deps.py` — auth + permission dependency helpers (this is where most BOLA branches modify code)
- `app/routers/` — endpoint handlers grouped by resource
- `seed_data.py` — creates demo users/orgs/event-types/bookings

## Branches

See `README.md` for the index of `bola/*` branches and links to per-branch PoC writeups in `docs/vulnerabilities/`.
