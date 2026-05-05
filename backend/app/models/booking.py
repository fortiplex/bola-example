import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def _new_uuid() -> str:
    return str(uuid.uuid4())


class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    public_uuid: Mapped[str] = mapped_column(
        String, unique=True, nullable=False, index=True, default=_new_uuid
    )
    event_type_id: Mapped[int] = mapped_column(
        ForeignKey("event_types.id"), nullable=False, index=True
    )
    host_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    invitee_email: Mapped[str] = mapped_column(String, nullable=False)
    invitee_name: Mapped[str] = mapped_column(String, nullable=False, default="")
    scheduled_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="confirmed")
    notes: Mapped[str] = mapped_column(String, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
