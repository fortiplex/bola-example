from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_org_admin, require_org_member
from app.models import Membership, Org, User
from app.schemas.org import (
    MembershipCreate,
    MembershipResponse,
    OrgCreate,
    OrgResponse,
)

router = APIRouter(prefix="/api/v1/orgs", tags=["orgs"])


@router.post("", response_model=OrgResponse)
def create_org(
    payload: OrgCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if db.query(Org).filter(Org.slug == payload.slug).first():
        raise HTTPException(status_code=409, detail="Slug taken")
    org = Org(name=payload.name, slug=payload.slug)
    db.add(org)
    db.flush()
    db.add(Membership(user_id=current_user.id, org_id=org.id, role="owner"))
    db.commit()
    db.refresh(org)
    return org


@router.get("", response_model=list[OrgResponse])
def list_my_orgs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(Org)
        .join(Membership, Membership.org_id == Org.id)
        .filter(Membership.user_id == current_user.id)
        .all()
    )


@router.get("/{org_id}", response_model=OrgResponse)
def get_org(
    org_id: int = Path(...),
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
    org = db.get(Org, org_id)
    return org


@router.post("/{org_id}/members", response_model=MembershipResponse)
def add_member(
    org_id: int,
    payload: MembershipCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Inline admin check (can't use require_org_admin factory inside Depends with path param easily)
    caller_membership = (
        db.query(Membership)
        .filter(Membership.org_id == org_id, Membership.user_id == current_user.id)
        .first()
    )
    if not caller_membership:
        raise HTTPException(status_code=404, detail="Org not found")
    if caller_membership.role not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="Admin role required")
    if not db.get(User, payload.user_id):
        raise HTTPException(status_code=404, detail="User not found")
    if (
        db.query(Membership)
        .filter(Membership.org_id == org_id, Membership.user_id == payload.user_id)
        .first()
    ):
        raise HTTPException(status_code=409, detail="Already a member")
    if payload.role not in ("owner", "admin", "member"):
        raise HTTPException(status_code=422, detail="Invalid role")
    m = Membership(user_id=payload.user_id, org_id=org_id, role=payload.role)
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


@router.delete("/{org_id}/members/{user_id}")
def remove_member(
    org_id: int,
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    caller_membership = (
        db.query(Membership)
        .filter(Membership.org_id == org_id, Membership.user_id == current_user.id)
        .first()
    )
    if not caller_membership:
        raise HTTPException(status_code=404, detail="Org not found")
    if caller_membership.role not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="Admin role required")
    target = (
        db.query(Membership)
        .filter(Membership.org_id == org_id, Membership.user_id == user_id)
        .first()
    )
    if not target:
        raise HTTPException(status_code=404, detail="Membership not found")
    db.delete(target)
    db.commit()
    return {"deleted": True}
