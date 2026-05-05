from functools import lru_cache

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.auth.jwt_handler import decode_access_token
from app.database import get_db
from app.models import Booking, EventType, Membership, ShareLink, User

bearer_scheme = HTTPBearer(auto_error=True)


def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    payload = decode_access_token(creds.credentials)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = db.get(User, int(payload["sub"]))
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def require_org_member(org_id: int):
    def _dep(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> Membership:
        membership = (
            db.query(Membership)
            .filter(Membership.org_id == org_id, Membership.user_id == current_user.id)
            .first()
        )
        if not membership:
            raise HTTPException(status_code=404, detail="Org not found")
        return membership

    return _dep


def require_org_admin(org_id: int):
    def _dep(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> Membership:
        membership = (
            db.query(Membership)
            .filter(Membership.org_id == org_id, Membership.user_id == current_user.id)
            .first()
        )
        if not membership:
            raise HTTPException(status_code=404, detail="Org not found")
        if membership.role not in ("owner", "admin"):
            raise HTTPException(status_code=403, detail="Admin role required")
        return membership

    return _dep


@lru_cache(maxsize=1024)
def _get_event_type_owner(event_type_id: int, _engine_id: int = 0) -> int | None:
    """Cached lookup of event_type.owner_id. _engine_id allows test isolation by varying the key."""
    from app.database import SessionLocal

    with SessionLocal() as db:
        et = db.get(EventType, event_type_id)
        return et.owner_id if et else None


def _invalidate_event_type_owner_cache() -> None:
    _get_event_type_owner.cache_clear()


def require_event_type_owner_or_org_admin(
    event_type_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EventType:
    """Used for write/delete/transfer on an event type."""
    et = db.get(EventType, event_type_id)
    if not et:
        raise HTTPException(status_code=404, detail="Event type not found")
    cached_owner_id = _get_event_type_owner(event_type_id)
    if cached_owner_id == current_user.id:
        return et
    if et.org_id is not None:
        membership = (
            db.query(Membership)
            .filter(
                Membership.org_id == et.org_id,
                Membership.user_id == current_user.id,
                Membership.role.in_(("owner", "admin")),
            )
            .first()
        )
        if membership:
            return et
    raise HTTPException(status_code=403, detail="Not authorized")


def require_event_type_accessible(
    event_type_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EventType:
    """Used for read/list (looser): any org member can access team event types."""
    et = db.get(EventType, event_type_id)
    if not et:
        raise HTTPException(status_code=404, detail="Event type not found")
    if et.owner_id == current_user.id:
        return et
    if et.org_id is not None:
        membership = (
            db.query(Membership)
            .filter(
                Membership.org_id == et.org_id,
                Membership.user_id == current_user.id,
            )
            .first()
        )
        if membership:
            return et
    raise HTTPException(status_code=403, detail="Not authorized")


def require_booking_host(
    booking_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Booking:
    booking = db.get(Booking, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.host_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not the booking host")
    return booking


def require_valid_share_token(token: str, expected_purpose: str, db: Session) -> ShareLink:
    from datetime import datetime, timezone

    link = db.query(ShareLink).filter(ShareLink.token == token).first()
    if not link:
        raise HTTPException(status_code=404, detail="Invalid token")
    # SQLite returns naive datetimes; normalize to UTC for the comparison.
    expires_at = link.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=403, detail="Token expired")
    if link.used_at is not None:
        raise HTTPException(status_code=403, detail="Token already used")
    if link.purpose != expected_purpose:
        raise HTTPException(status_code=403, detail="Token purpose mismatch")
    return link
