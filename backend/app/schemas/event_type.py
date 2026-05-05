from pydantic import BaseModel


class EventTypeCreate(BaseModel):
    slug: str
    title: str
    duration_min: int = 30
    description: str = ""


class EventTypeUpdate(BaseModel):
    title: str | None = None
    duration_min: int | None = None
    description: str | None = None
    is_active: bool | None = None


class EventTypeResponse(BaseModel):
    id: int
    owner_id: int
    org_id: int | None
    slug: str
    title: str
    duration_min: int
    description: str
    is_active: bool

    model_config = {"from_attributes": True}


class EventTypeTransferRequest(BaseModel):
    new_owner_id: int
