from fastapi import FastAPI

from app.config import settings
from app.database import init_db
from app.routers import auth, bookings, event_types, orgs, share_links

settings.validate()

app = FastAPI(title="bola-example", version="0.1.0")

init_db()

app.include_router(auth.router)
app.include_router(orgs.router)
app.include_router(event_types.router)
app.include_router(bookings.router)
app.include_router(share_links.router)


@app.get("/health")
def health() -> dict:
    return {"status": "healthy"}
