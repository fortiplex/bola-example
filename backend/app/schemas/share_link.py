from datetime import datetime

from pydantic import BaseModel


class ShareLinkCreate(BaseModel):
    purpose: str  # view|cancel|reschedule
    expires_in_minutes: int = 60 * 24 * 7  # 7 days default


class ShareLinkResponse(BaseModel):
    token: str
    purpose: str
    expires_at: datetime

    model_config = {"from_attributes": True}


class RescheduleRequest(BaseModel):
    booking_id: int  # Multi-meeting reschedule pages reference the target by id.
    new_time: datetime
