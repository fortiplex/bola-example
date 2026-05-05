from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_booking_host
from app.models import Booking, EventType, ShareLink, User
from app.schemas.booking import (
    BookingCreate,
    BookingHostResponse,
    BookingPublicResponse,
    BookingUpdate,
)

router = APIRouter(prefix="/api/v1", tags=["bookings"])


def load_booking_by_uuid(public_uuid: str, db: Session) -> Booking:
    booking = db.query(Booking).filter(Booking.public_uuid == public_uuid).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking


@router.post("/event-types/{event_type_id}/bookings", response_model=BookingPublicResponse)
def create_booking(
    event_type_id: int,
    payload: BookingCreate,
    db: Session = Depends(get_db),
):
    et = db.get(EventType, event_type_id)
    if not et or not et.is_active:
        raise HTTPException(status_code=404, detail="Event type not bookable")
    booking = Booking(
        event_type_id=et.id,
        host_id=et.owner_id,
        invitee_email=payload.invitee_email,
        invitee_name=payload.invitee_name,
        scheduled_at=payload.scheduled_at,
    )
    db.add(booking)
    db.flush()
    # Auto-issue a reschedule share link valid for 7 days, created by the host
    link = ShareLink(
        booking_id=booking.id,
        purpose="reschedule",
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        created_by=et.owner_id,
    )
    db.add(link)
    db.commit()
    db.refresh(booking)
    return booking


@router.get("/bookings/mine", response_model=list[BookingHostResponse])
def list_my_bookings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return db.query(Booking).filter(Booking.host_id == current_user.id).all()


@router.get("/bookings/{booking_id:int}", response_model=BookingHostResponse)
def get_booking_host_detail(
    booking_id: int,
    booking: Booking = Depends(require_booking_host),
):
    return booking


@router.get("/bookings/{public_uuid}", response_model=BookingPublicResponse)
def get_booking_public(public_uuid: str, db: Session = Depends(get_db)):
    return load_booking_by_uuid(public_uuid, db)


@router.patch("/bookings/{booking_id}", response_model=BookingHostResponse)
def update_booking(
    booking_id: int,
    payload: BookingUpdate,
    booking: Booking = Depends(require_booking_host),
    db: Session = Depends(get_db),
):
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(booking, field, value)
    db.commit()
    db.refresh(booking)
    return booking


@router.post("/bookings/{booking_id}/cancel")
def cancel_booking(
    booking_id: int,
    booking: Booking = Depends(require_booking_host),
    db: Session = Depends(get_db),
):
    booking.status = "cancelled"
    db.commit()
    return {"cancelled": True}
