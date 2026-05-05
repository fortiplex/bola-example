from pydantic import BaseModel


class OrgCreate(BaseModel):
    name: str
    slug: str


class OrgResponse(BaseModel):
    id: int
    name: str
    slug: str

    model_config = {"from_attributes": True}


class MembershipCreate(BaseModel):
    user_id: int
    role: str = "member"  # owner|admin|member


class MembershipResponse(BaseModel):
    id: int
    user_id: int
    org_id: int
    role: str

    model_config = {"from_attributes": True}
