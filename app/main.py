from fastapi import FastAPI, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import engine, Base, get_db
from app.models import Ticket, Message, TicketEvent, Outbox
from app.schemas import TicketCreate, TicketOut

app = FastAPI(title="Ticket Intake API")


@app.on_event("startup")
async def on_startup():
    # Creates tables if they don't exist yet. Fine for local dev;
    # use a real migration tool (Alembic) once this goes further.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/api/v1/tickets", response_model=TicketOut, status_code=201)
async def create_ticket(payload: TicketCreate, db: AsyncSession = Depends(get_db)):
    requester = payload.requester

    ticket = Ticket(
        subject=payload.subject,
        source=payload.source,
        requester_department=requester.department if requester else None,
        requester_region=requester.region if requester else None,
        requester_tenure_days=requester.tenure_days if requester else None,
    )
    db.add(ticket)
    await db.flush()  # assigns ticket.id without committing yet

    for m in payload.messages:
        db.add(Message(ticket_id=ticket.id, author_type=m.author_type, body=m.body))

    db.add(TicketEvent(ticket_id=ticket.id, event="ticket.created", actor="customer"))

    # Outbox row written in the SAME transaction as the ticket —
    # this is the guarantee that triage is never silently dropped.
    db.add(Outbox(ticket_id=ticket.id))

    await db.commit()
    await db.refresh(ticket)

    return ticket
