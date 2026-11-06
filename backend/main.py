"""FastAPI desk API. Human approve is the only path that moves cash."""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mcp_server.server import DB_PATH, apply_approved_payment  # noqa: E402
from backend.mcp_bridge import shop  # noqa: E402
from backend.team import run_ticket  # noqa: E402

ORIG_DB = ROOT / "data" / "campus_customs.db"
AUDIT_PATH = ROOT / "output" / "audit_trail.json"
EVENTS: list[dict] = []
if AUDIT_PATH.exists():
    try:
        loaded = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
        if isinstance(loaded, list):
            EVENTS.extend(loaded)
    except json.JSONDecodeError:
        pass

app = FastAPI(title="Campus Customs desk")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ApproveBody(BaseModel):
    payment_id: int
    approved_by: str = "store manager"


@app.get("/tickets")
async def tickets():
    rows = await shop("list_tickets", status="all")
    return {"tickets": rows}


@app.post("/tickets/{ticket_id}/run")
async def run(ticket_id: int):
    ticket = await shop("get_ticket", ticket_id=ticket_id)
    if not ticket.get("found"):
        raise HTTPException(404, f"ticket {ticket_id} not found")
    try:
        verdict = await run_ticket(ticket_id, events=EVENTS)
    except Exception as exc:
        raise HTTPException(500, f"run failed: {exc}") from exc
    return {"verdict": verdict.model_dump(), "events": EVENTS[-40:]}


@app.get("/events")
async def events(limit: int = 400, ticket_id: int | None = None):
    rows = EVENTS
    if ticket_id is not None:
        rows = [e for e in EVENTS if e.get("ticket_id") == ticket_id]
    return {"events": rows[-limit:]}


@app.get("/cash")
async def cash():
    return await shop("get_cash")


@app.get("/desk")
async def desk():
    return await shop("get_desk")


@app.get("/payments/pending")
async def payments_pending():
    return {"payments": await shop("pending_payments")}


@app.post("/approve-pay")
async def approve_pay(body: ApproveBody):
    result = apply_approved_payment(body.payment_id, body.approved_by)
    if not result.get("ok"):
        raise HTTPException(400, result.get("reason", "pay refused"))
    EVENTS.append(
        {
            "kind": "HUMAN_APPROVE",
            "payment_id": body.payment_id,
            "approved_by": body.approved_by,
            "result": result,
        }
    )
    return result


@app.post("/reset")
async def reset():
    EVENTS.clear()
    shutil.copy2(ORIG_DB, DB_PATH)
    return {"ok": True, "checking": await shop("get_cash")}


@app.get("/health")
async def health():
    return {"ok": True}
