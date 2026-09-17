import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _now():
    return datetime.now(timezone.utc)


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(
        String, unique=True, index=True, default=lambda: f"TKT-{uuid.uuid4().hex[:8].upper()}"
    )
    requester_department: Mapped[str] = mapped_column(String, nullable=True)
    requester_region: Mapped[str] = mapped_column(String, nullable=True)
    requester_tenure_days: Mapped[int] = mapped_column(nullable=True)
    subject: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, default="open")
    category: Mapped[str] = mapped_column(String, nullable=True)  # NULL until triage runs
    priority: Mapped[str] = mapped_column(String, nullable=True)  # NULL until triage runs
    triage_state: Mapped[str] = mapped_column(String, default="pending")
    source: Mapped[str] = mapped_column(String, default="api")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    messages: Mapped[list["Message"]] = relationship(back_populates="ticket", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id"))
    author_type: Mapped[str] = mapped_column(String, default="customer")
    body: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    ticket: Mapped["Ticket"] = relationship(back_populates="messages")


class TicketEvent(Base):
    __tablename__ = "ticket_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id"))
    event: Mapped[str] = mapped_column(String, nullable=False)
    actor: Mapped[str] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Outbox(Base):
    __tablename__ = "outbox"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    request_id: Mapped[str] = mapped_column(String, unique=True, default=lambda: str(uuid.uuid4()))
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id"))
    state: Mapped[str] = mapped_column(String, default="pending")
    attempts: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
