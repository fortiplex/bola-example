from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import (
    _invalidate_event_type_owner_cache,
    get_current_user,
    require_event_type_accessible,
    require_event_type_owner_or_org_admin,
)
from app.models import Booking, EventType, Membership, User
from app.schemas.booking import BookingHostResponse
from app.schemas.event_type import (
    EventTypeCreate,
    EventTypeResponse,
    EventTypeTransferRequest,
    EventTypeUpdate,
)

router = APIRouter(prefix="/api/v1", tags=["event-types"])


@router.post("/event-types", response_model=EventTypeResponse)
def create_personal_event_type(
    payload: EventTypeCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    et = EventType(
        owner_id=current_user.id,
        org_id=None,
        slug=payload.slug,
        title=payload.title,
        duration_min=payload.duration_min,
        description=payload.description,
    )
    db.add(et)
    db.commit()
    db.refresh(et)
    return et


@router.post("/orgs/{org_id}/event-types", response_model=EventTypeResponse)
def create_team_event_type(
    org_id: int,
    payload: EventTypeCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not (
        db.query(Membership)
        .filter(Membership.org_id == org_id, Membership.user_id == current_user.id)
        .first()
    ):
        raise HTTPException(status_code=404, detail="Org not found")
    et = EventType(
        owner_id=current_user.id,
        org_id=org_id,
        slug=payload.slug,
        title=payload.title,
        duration_min=payload.duration_min,
        description=payload.description,
    )
    db.add(et)
    db.commit()
    db.refresh(et)
    return et


@router.get("/event-types/{event_type_id}", response_model=EventTypeResponse)
def get_event_type(
    event_type_id: int,
    et: EventType = Depends(require_event_type_accessible),
):
    return et


@router.patch("/event-types/{event_type_id}", response_model=EventTypeResponse)
def update_event_type(
    event_type_id: int,
    payload: EventTypeUpdate,
    et: EventType = Depends(require_event_type_owner_or_org_admin),
    db: Session = Depends(get_db),
):
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(et, field, value)
    db.commit()
    db.refresh(et)
    _invalidate_event_type_owner_cache()
    return et


@router.patch("/orgs/{org_id}/event-types/{event_type_id}", response_model=EventTypeResponse)
def update_org_event_type(
    org_id: int,
    event_type_id: int,
    payload: EventTypeUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    membership = (
        db.query(Membership)
        .filter(Membership.org_id == org_id, Membership.user_id == current_user.id)
        .first()
    )
    if not membership:
        raise HTTPException(status_code=404, detail="Org not found")
    if membership.role not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="Admin role required")
    et = db.get(EventType, event_type_id)
    if not et:
        raise HTTPException(status_code=404, detail="Event type not found")
    if et.org_id != org_id:
        raise HTTPException(status_code=404, detail="Event type not found in this org")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(et, field, value)
    db.commit()
    db.refresh(et)
    _invalidate_event_type_owner_cache()
    return et


@router.delete("/event-types/{event_type_id}")
def delete_event_type(
    event_type_id: int,
    et: EventType = Depends(require_event_type_owner_or_org_admin),
    db: Session = Depends(get_db),
):
    db.delete(et)
    db.commit()
    _invalidate_event_type_owner_cache()
    return {"deleted": True}


@router.post("/event-types/{event_type_id}/transfer", response_model=EventTypeResponse)
def transfer_event_type(
    event_type_id: int,
    payload: EventTypeTransferRequest,
    et: EventType = Depends(require_event_type_owner_or_org_admin),
    db: Session = Depends(get_db),
):
    new_owner = db.get(User, payload.new_owner_id)
    if not new_owner:
        raise HTTPException(status_code=404, detail="Target user not found")
    et.owner_id = payload.new_owner_id
    db.commit()
    db.refresh(et)
    # Cache invalidation is handled by the next PATCH; transfer is a rare admin op
    return et


@router.get("/users/{user_id}/event-types", response_model=list[EventTypeResponse])
def list_user_public_event_types(user_id: int, db: Session = Depends(get_db)):
    return (
        db.query(EventType)
        .filter(EventType.owner_id == user_id, EventType.is_active == True)  # noqa: E712
        .all()
    )


@router.get("/event-types/{event_type_id}/bookings", response_model=list[BookingHostResponse])
def list_event_type_bookings(
    event_type_id: int,
    et: EventType = Depends(require_event_type_accessible),
    db: Session = Depends(get_db),
):
    # Org members can see all bookings on a team event type so they can coordinate scheduling.
    return db.query(Booking).filter(Booking.event_type_id == et.id).all()
