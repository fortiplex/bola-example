from datetime import datetime

from pydantic import BaseModel


class BookingCreate(BaseModel):
    invitee_email: str
    invitee_name: str = ""
    scheduled_at: datetime


class BookingPublicResponse(BaseModel):
    public_uuid: str
    scheduled_at: datetime
    invitee_name: str
    status: str

    model_config = {"from_attributes": True}


class BookingHostResponse(BaseModel):
    id: int
    public_uuid: str
    event_type_id: int
    host_id: int
    invitee_email: str
    invitee_name: str
    scheduled_at: datetime
    status: str
    notes: str

    model_config = {"from_attributes": True}


class BookingUpdate(BaseModel):
    notes: str | None = None
    status: str | None = None
