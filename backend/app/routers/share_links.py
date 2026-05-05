from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_booking_host, require_valid_share_token
from app.models import Booking, ShareLink, User
from app.schemas.booking import BookingPublicResponse
from app.schemas.share_link import (
    RescheduleRequest,
    ShareLinkCreate,
    ShareLinkResponse,
)

router = APIRouter(prefix="/api/v1", tags=["share-links"])


@router.post("/bookings/{booking_id}/share-links", response_model=ShareLinkResponse)
def create_share_link(
    booking_id: int,
    payload: ShareLinkCreate,
    booking: Booking = Depends(require_booking_host),
    db: Session = Depends(get_db),
):
    if payload.purpose not in ("view", "cancel", "reschedule"):
        raise HTTPException(status_code=422, detail="Invalid purpose")
    link = ShareLink(
        booking_id=booking.id,
        purpose=payload.purpose,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=payload.expires_in_minutes),
        created_by=booking.host_id,
    )
    db.add(link)
    db.commit()
    db.refresh(link)
    return link


@router.get("/share/{token}", response_model=BookingPublicResponse)
def get_share_target(token: str, db: Session = Depends(get_db)):
    link = require_valid_share_token(token, "view", db)
    booking = db.get(Booking, link.booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking


@router.post("/share/{token}/reschedule", response_model=BookingPublicResponse)
def reschedule_via_share(
    token: str,
    payload: RescheduleRequest,
    db: Session = Depends(get_db),
):
    link = require_valid_share_token(token, "reschedule", db)
    booking = db.get(Booking, link.booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    booking.scheduled_at = payload.new_time
    booking.status = "rescheduled"
    link.used_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(booking)
    return booking


@router.post("/share/{token}/cancel")
def cancel_via_share(token: str, db: Session = Depends(get_db)):
    link = require_valid_share_token(token, "cancel", db)
    booking = db.get(Booking, link.booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    booking.status = "cancelled"
    link.used_at = datetime.now(timezone.utc)
    db.commit()
    return {"cancelled": True}
