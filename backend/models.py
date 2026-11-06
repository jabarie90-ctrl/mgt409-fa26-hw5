"""Types the desk agents return."""
from __future__ import annotations

from pydantic import BaseModel, Field


class PendingPay(BaseModel):
    payment_id: int
    kind: str
    ref_id: int
    amount: float
    note: str = ""


class TicketVerdict(BaseModel):
    ticket_id: int
    status: str = Field(description="open, waiting_approval, or resolved")
    summary: str
    pending_payments: list[PendingPay] = Field(default_factory=list)
    customer_draft: str = ""
    agents_involved: list[str] = Field(default_factory=list)
