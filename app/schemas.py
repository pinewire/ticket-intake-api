from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class MessageIn(BaseModel):
    author_type: str = Field(default="customer")
    body: str


class RequesterContext(BaseModel):
    department: Optional[str] = None
    region: Optional[str] = None
    tenure_days: Optional[int] = None
    prior_ticket_count: Optional[int] = None


class TicketCreate(BaseModel):
    """Matches the payload shape from the Confluence design doc."""
    subject: str
    messages: list[MessageIn]
    requester: Optional[RequesterContext] = None
    source: str = Field(default="api")


class TicketOut(BaseModel):
    public_id: str
    subject: str
    status: str
    category: Optional[str]
    priority: Optional[str]
    triage_state: str
    created_at: datetime

    class Config:
        from_attributes = True
