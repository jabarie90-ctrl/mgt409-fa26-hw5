"""Five Campus Customs agents. Shop facts come from MCP. gpt-6-luna only."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from pydantic_ai import Agent, RunContext, UsageLimits
from pydantic_ai.exceptions import UsageLimitExceeded
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.providers.openai import OpenAIProvider
from openai import AsyncOpenAI

from backend.mcp_bridge import shop
from backend.models import PendingPay, TicketVerdict

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT.parent / ".env")
load_dotenv(ROOT / ".env")

MODEL_NAME = "gpt-6-luna"
PROMPTS = ROOT / "backend" / "prompts"
AUDIT_PATH = ROOT / "output" / "audit_trail.json"
MAX_DEPTH = 3


def _model() -> OpenAIResponsesModel:
    portkey = (os.getenv("PORTKEY_API_KEY") or "").strip()
    openai_key = (os.getenv("OPENAI_API_KEY") or "").strip()
    if portkey:
        client = AsyncOpenAI(
            api_key=portkey,
            base_url=os.getenv("PORTKEY_BASE_URL", "https://api.portkey.ai/v1"),
            default_headers={
                "x-portkey-api-key": portkey,
                "x-portkey-provider": os.getenv("PORTKEY_PROVIDER", "openai"),
            },
        )
        return OpenAIResponsesModel(MODEL_NAME, provider=OpenAIProvider(openai_client=client))
    if not openai_key:
        raise RuntimeError("PORTKEY_API_KEY or OPENAI_API_KEY is missing.")
    return OpenAIResponsesModel(MODEL_NAME, provider=OpenAIProvider(api_key=openai_key))


@dataclass
class Session:
    ticket_id: int = 0
    depth: int = 0
    caller: str = "boss"
    events: list[dict] = field(default_factory=list)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def append_audit(row: dict) -> None:
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    rows: list = []
    if AUDIT_PATH.exists():
        try:
            loaded = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
            if isinstance(loaded, list):
                rows = loaded
        except json.JSONDecodeError:
            rows = []
    rows.append(row)
    AUDIT_PATH.write_text(json.dumps(rows, indent=2), encoding="utf-8")


def _stamp(session: Session, **row: Any) -> None:
    event = {"time": _now(), "ticket_id": session.ticket_id, **row}
    session.events.append(event)
    append_audit(event)


def _prompt(name: str) -> str:
    return (PROMPTS / f"{name}.md").read_text(encoding="utf-8")


def _live(name: str):
    def _fn(_ctx: RunContext[Session]) -> str:
        return _prompt(name)

    _fn.__name__ = f"prompt_{name}"
    return _fn


model = _model()
USAGE = UsageLimits(request_limit=40, tool_calls_limit=40)

boss_agent = Agent(
    model, deps_type=Session, output_type=TicketVerdict, instructions=_live("boss"), name="boss"
)
inventory_agent = Agent(
    model, deps_type=Session, output_type=str, instructions=_live("inventory"), name="inventory"
)
accounting_agent = Agent(
    model, deps_type=Session, output_type=str, instructions=_live("accounting"), name="accounting"
)
facilities_agent = Agent(
    model, deps_type=Session, output_type=str, instructions=_live("facilities"), name="facilities"
)
cs_agent = Agent(
    model, deps_type=Session, output_type=str, instructions=_live("customer_service"), name="customer_service"
)

TEAM = {
    "boss": boss_agent,
    "inventory": inventory_agent,
    "accounting": accounting_agent,
    "facilities": facilities_agent,
    "customer_service": cs_agent,
}


async def _shop(session: Session, tool: str, **arguments: Any) -> Any:
    _stamp(session, kind="TOOL", agent=session.caller, tool=tool, args=arguments)
    result = await shop(tool, **arguments)
    _stamp(session, kind="TOOL_RESULT", agent=session.caller, tool=tool, result=_clip(result))
    return result


def _clip(value: Any, limit: int = 800) -> Any:
    text = json.dumps(value, default=str) if not isinstance(value, str) else value
    if len(text) <= limit:
        return value
    return text[:limit] + "…"


def _attach_shop(agent: Agent) -> None:
    @agent.tool
    async def get_desk(ctx: RunContext[Session]) -> dict:
        """Shop calendar. date_today is today for overdue checks."""
        return await _shop(ctx.deps, "get_desk")

    @agent.tool
    async def get_cash(ctx: RunContext[Session]) -> dict:
        """Checking balance."""
        return await _shop(ctx.deps, "get_cash")

    @agent.tool
    async def get_ticket(ctx: RunContext[Session], ticket_id: int) -> dict:
        """One ticket on the board."""
        return await _shop(ctx.deps, "get_ticket", ticket_id=ticket_id)

    @agent.tool
    async def list_tickets(ctx: RunContext[Session], status: str = "open") -> list:
        """Tickets on the board. status is open, resolved, or all."""
        return await _shop(ctx.deps, "list_tickets", status=status)

    @agent.tool
    async def get_sku_stock(ctx: RunContext[Session], sku: str, size: str) -> dict:
        """On-hand qty for one SKU and size."""
        return await _shop(ctx.deps, "get_sku_stock", sku=sku, size=size)

    @agent.tool
    async def list_inventory_for_sku(ctx: RunContext[Session], sku: str) -> list:
        """Every size on the shelf for one SKU."""
        return await _shop(ctx.deps, "list_inventory_for_sku", sku=sku)

    @agent.tool
    async def get_sku_pricing(ctx: RunContext[Session], sku: str) -> dict:
        """Unit cost and list price."""
        return await _shop(ctx.deps, "get_sku_pricing", sku=sku)

    @agent.tool
    async def get_lease(ctx: RunContext[Session], lease_id: int) -> dict:
        """Lease and rent due."""
        return await _shop(ctx.deps, "get_lease", lease_id=lease_id)

    @agent.tool
    async def get_invoice(ctx: RunContext[Session], invoice_id: int) -> dict:
        """Vendor invoice."""
        return await _shop(ctx.deps, "get_invoice", invoice_id=invoice_id)

    @agent.tool
    async def get_vendor(ctx: RunContext[Session], vendor_id: int) -> dict:
        """Vendor name and lead_days."""
        return await _shop(ctx.deps, "get_vendor", vendor_id=vendor_id)

    @agent.tool
    async def vendor_can_ship(ctx: RunContext[Session], vendor_id: int) -> dict:
        """False when this vendor still has an open invoice."""
        return await _shop(ctx.deps, "vendor_can_ship", vendor_id=vendor_id)

    @agent.tool
    async def prepare_payment(
        ctx: RunContext[Session], kind: str, ref_id: int, amount: float, note: str
    ) -> dict:
        """Stage a pay. Does not move cash. A human has to approve it."""
        return await _shop(
            ctx.deps, "prepare_payment", kind=kind, ref_id=ref_id, amount=amount, note=note
        )

    @agent.tool
    async def pending_payments(ctx: RunContext[Session]) -> list:
        """Pays waiting on a human."""
        return await _shop(ctx.deps, "pending_payments")

    @agent.tool
    async def list_payments(ctx: RunContext[Session]) -> list:
        """All payment rows, including ones a human already stamped."""
        return await _shop(ctx.deps, "list_payments")

    @agent.tool
    async def receive_stock(
        ctx: RunContext[Session], sku: str, size: str, qty: int, reason: str
    ) -> dict:
        """Add units after the vendor is allowed to ship."""
        return await _shop(ctx.deps, "receive_stock", sku=sku, size=size, qty=qty, reason=reason)

    @agent.tool
    async def pick_stock(
        ctx: RunContext[Session], sku: str, size: str, qty: int, reason: str
    ) -> dict:
        """Take units off the shelf for a filled order."""
        return await _shop(ctx.deps, "pick_stock", sku=sku, size=size, qty=qty, reason=reason)

    @agent.tool
    async def update_ticket(
        ctx: RunContext[Session], ticket_id: int, status: str, notes: str
    ) -> dict:
        """Set ticket status to open or resolved."""
        return await _shop(ctx.deps, "update_ticket", ticket_id=ticket_id, status=status, notes=notes)


def _attach_handoff(agent: Agent) -> None:
    @agent.tool
    async def ask_teammate(ctx: RunContext[Session], role: str, task: str) -> str:
        """Ask one other desk agent. role is inventory, accounting, facilities, customer_service, or boss.

        Args:
            role: Teammate to ask.
            task: What you need from them.
        """
        key = role.strip().lower().replace(" ", "_")
        if key not in TEAM:
            return f"No agent named {role}. Use inventory, accounting, facilities, customer_service, or boss."
        if key == ctx.deps.caller:
            return "You cannot ask yourself."
        if ctx.deps.depth >= MAX_DEPTH:
            return "Stop handing off. Answer from the tools you already have."
        child = Session(
            ticket_id=ctx.deps.ticket_id,
            depth=ctx.deps.depth + 1,
            caller=key,
            events=ctx.deps.events,
        )
        _stamp(ctx.deps, kind="HANDOFF", agent=ctx.deps.caller, to=key, task=task)
        try:
            result = await TEAM[key].run(task, deps=child, usage_limits=USAGE)
        except UsageLimitExceeded as exc:
            text = f"Stopped after the token/request limit: {exc}"
            _stamp(ctx.deps, kind="HANDOFF_RESULT", agent=key, result=text)
            return text
        text = result.output if isinstance(result.output, str) else json.dumps(result.output, default=str)
        _stamp(ctx.deps, kind="HANDOFF_RESULT", agent=key, result=_clip(text, 600))
        return text


for _agent in TEAM.values():
    _attach_shop(_agent)
    _attach_handoff(_agent)


async def run_ticket(ticket_id: int, events: list[dict] | None = None) -> TicketVerdict:
    session = Session(ticket_id=ticket_id, caller="boss", events=events if events is not None else [])
    ticket = await shop("get_ticket", ticket_id=ticket_id)
    cash = await shop("get_cash")
    desk = await shop("get_desk")
    prompt = (
        f"Run ticket {ticket_id}. Shop today is {desk}. Checking is {cash}. "
        f"Ticket row: {json.dumps(ticket, default=str)}. "
        "Call the teammate who should work first. Do not send everyone. "
        "Keep going until the ticket is waiting_approval (a pay is staged) or resolved. "
        "One specialist report is not a finished desk if the ticket is still blocked."
    )
    _stamp(session, kind="RUN_START", agent="boss", prompt=_clip(prompt, 400))
    try:
        result = await boss_agent.run(prompt, deps=session, usage_limits=USAGE)
    except UsageLimitExceeded as exc:
        pending = await shop("pending_payments")
        verdict = TicketVerdict(
            ticket_id=ticket_id,
            status="waiting_approval" if pending else "open",
            summary=f"Run hit the request limit: {exc}",
            pending_payments=[
                PendingPay(
                    payment_id=int(row.get("id") or row.get("payment_id") or 0),
                    kind=str(row.get("kind") or ""),
                    ref_id=int(row.get("ref_id") or 0),
                    amount=float(row.get("amount") or 0),
                    note="staged before the limit",
                )
                for row in pending
            ],
            agents_involved=["boss"],
        )
        _stamp(session, kind="RUN_END", agent="boss", verdict=verdict.model_dump())
        return verdict
    verdict = result.output
    if not isinstance(verdict, TicketVerdict):
        verdict = TicketVerdict.model_validate(verdict)
    verdict.ticket_id = ticket_id
    if "boss" not in verdict.agents_involved:
        verdict.agents_involved = ["boss", *verdict.agents_involved]
    _stamp(session, kind="RUN_END", agent="boss", verdict=verdict.model_dump())
    return verdict
