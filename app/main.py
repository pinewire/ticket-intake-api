import asyncio
import logging

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import engine, Base, get_db
from app.models import Ticket, Message, TicketEvent, Outbox
from app.schemas import TicketCreate, TicketOut

logger = logging.getLogger("ticket_intake")

app = FastAPI(title="Ticket Intake API")

MAX_RETRY_DELAY_SECONDS = 10


async def init_db() -> None:
    """Create tables, retrying until Postgres is reachable.

    Runs in the background so the app starts even when the database is down.
    The process stays alive and /ready reports not-ready until this succeeds,
    instead of crashing and being restarted in a loop by Kubernetes.
    """
    delay = 1
    while True:
        try:
            # Fine for local dev; use a real migration tool (Alembic) later.
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            app.state.db_initialized = True
            logger.info("database ready, tables ensured")
            return
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning("database not reachable (%s), retrying in %ss", exc, delay)
            await asyncio.sleep(delay)
            delay = min(delay * 2, MAX_RETRY_DELAY_SECONDS)


@app.on_event("startup")
async def on_startup():
    app.state.db_initialized = False
    # Keep a reference so the task isn't garbage collected.
    app.state.db_init_task = asyncio.create_task(init_db())


@app.on_event("shutdown")
async def on_shutdown():
    task = getattr(app.state, "db_init_task", None)
    if task and not task.done():
        task.cancel()


@app.get("/health")
async def health():
    """Liveness: the process is up. Does not touch the database."""
    return {"status": "ok"}


@app.get("/ready")
async def ready(db: AsyncSession = Depends(get_db)):
    """Readiness: the database is reachable and tables exist."""
    if not getattr(app.state, "db_initialized", False):
        raise HTTPException(status_code=503, detail="database not initialized")
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        raise HTTPException(status_code=503, detail="database unreachable")
    return {"status": "ready"}


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
