"""Campus Customs shop MCP. All shop facts go through this server.

Talks only to data/campus_customs_new.db. Does not invent rows.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

from fastmcp import FastMCP

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DB_PATH = ROOT / "data" / "campus_customs_new.db"

mcp = FastMCP("campus-customs-desk")


def _connect() -> sqlite3.Connection:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Working database not found: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _rows(sql: str, params: tuple = ()) -> list[dict]:
    with _connect() as conn:
        return [dict(r) for r in conn.execute(sql, params)]


def _one(sql: str, params: tuple = ()) -> dict | None:
    found = _rows(sql, params)
    return found[0] if found else None


def _execute(sql: str, params: tuple = ()) -> None:
    with _connect() as conn:
        conn.execute(sql, params)
        conn.commit()


@mcp.tool
def get_sku_stock(sku: str, size: str) -> dict:
    """On-hand quantity for one Campus Customs SKU and size.

    Args:
        sku: Catalogue SKU, for example CC-TEE-WHITE.
        size: Size code, for example S or M.
    """
    row = _one(
        "SELECT sku, name, size, qty, location FROM inventory WHERE sku = ? AND size = ?",
        (sku, size),
    )
    if not row:
        return {"found": False, "sku": sku, "size": size, "qty": 0}
    return {"found": True, **row}


@mcp.tool
def get_lease(lease_id: int) -> dict:
    """Lease row for the Chapel Street shop (rent, landlord, next due).

    Args:
        lease_id: leases.id, ticket 102 uses 1.
    """
    row = _one("SELECT * FROM leases WHERE id = ?", (lease_id,))
    if not row:
        return {"found": False, "lease_id": lease_id}
    return {"found": True, **row}


@mcp.tool
def get_sku_pricing(sku: str) -> dict:
    """Vendor unit cost and list price for one SKU.

    Args:
        sku: Catalogue SKU, for example CC-HOOD-NAVY.
    """
    row = _one("SELECT sku, unit_cost, list_price FROM pricing WHERE sku = ?", (sku,))
    if not row:
        return {"found": False, "sku": sku}
    return {"found": True, **row}


@mcp.tool
def get_desk() -> dict:
    """Shop calendar. date_today is 'today' for overdue checks."""
    row = _one("SELECT date_today, notes FROM desk")
    return row or {"date_today": None}


@mcp.tool
def get_cash() -> dict:
    """Checking balance. Cash only goes out."""
    row = _one("SELECT name, balance, date FROM cash_accounts WHERE name = 'checking'")
    return row or {"name": "checking", "balance": 0}


@mcp.tool
def list_tickets(status: str = "open") -> list[dict]:
    """Tickets on the board.

    Args:
        status: open, resolved, or all.
    """
    if status == "all":
        return _rows("SELECT * FROM tickets ORDER BY id")
    return _rows("SELECT * FROM tickets WHERE status = ? ORDER BY id", (status,))


@mcp.tool
def get_ticket(ticket_id: int) -> dict:
    """One ticket and the columns that join to inventory, leases, and invoices.

    Args:
        ticket_id: 101, 102, or 103.
    """
    row = _one("SELECT * FROM tickets WHERE id = ?", (ticket_id,))
    if not row:
        return {"found": False, "ticket_id": ticket_id}
    return {"found": True, **row}


@mcp.tool
def get_invoice(invoice_id: int) -> dict:
    """Vendor invoice, including open/paid status and due date.

    Args:
        invoice_id: invoices.id. Ticket 101 points at 501.
    """
    row = _one("SELECT * FROM invoices WHERE id = ?", (invoice_id,))
    if not row:
        return {"found": False, "invoice_id": invoice_id}
    return {"found": True, **row}


@mcp.tool
def get_vendor(vendor_id: int) -> dict:
    """Vendor name, specialty, and lead_days.

    Args:
        vendor_id: vendors.id.
    """
    row = _one("SELECT * FROM vendors WHERE id = ?", (vendor_id,))
    if not row:
        return {"found": False, "vendor_id": vendor_id}
    return {"found": True, **row}


@mcp.tool
def vendor_can_ship(vendor_id: int) -> dict:
    """False when this vendor still has an open unpaid invoice.

    Args:
        vendor_id: vendors.id.
    """
    open_inv = _rows(
        "SELECT id, amount, due_date, status, description FROM invoices "
        "WHERE vendor_id = ? AND status = 'open'",
        (vendor_id,),
    )
    vendor = _one("SELECT id, name FROM vendors WHERE id = ?", (vendor_id,))
    return {
        "vendor_id": vendor_id,
        "vendor": vendor["name"] if vendor else None,
        "can_ship": len(open_inv) == 0,
        "open_invoices": open_inv,
    }


@mcp.tool
def list_inventory_for_sku(sku: str) -> list[dict]:
    """Every size on the shelf for one SKU.

    Args:
        sku: Catalogue SKU.
    """
    return _rows(
        "SELECT sku, name, size, qty, location FROM inventory WHERE sku = ? ORDER BY size",
        (sku,),
    )


@mcp.tool
def prepare_payment(kind: str, ref_id: int, amount: float, note: str) -> dict:
    """Stage a payment. Does not move cash. A human must approve it on the board.

    Args:
        kind: invoice, rent, or restock.
        ref_id: invoices.id, leases.id, or 0 for a restock.
        amount: Dollars to leave checking.
        note: Why this pay is needed.
    """
    cash = get_cash()
    balance = float(cash.get("balance") or 0)
    if amount <= 0:
        return {"ok": False, "reason": "amount must be positive", "note": note}
    if amount > balance:
        return {
            "ok": False,
            "reason": f"checking is ${balance:.2f}; ${amount:.2f} would go negative",
            "note": note,
        }
    desk = get_desk()
    with _connect() as conn:
        # Schema marks paid_at / approved_by NOT NULL. Empty string = staged, not approved.
        cur = conn.execute(
            "INSERT INTO payments (kind, ref_id, amount, account, paid_at, approved_by) "
            "VALUES (?, ?, ?, 'checking', '', '')",
            (kind, ref_id, amount),
        )
        conn.commit()
        payment_id = cur.lastrowid
    return {
        "ok": True,
        "needs_human": True,
        "payment_id": payment_id,
        "kind": kind,
        "ref_id": ref_id,
        "amount": amount,
        "checking": balance,
        "date_today": desk.get("date_today"),
        "note": note,
    }


@mcp.tool
def pending_payments() -> list[dict]:
    """Payments staged by agents that a human has not approved yet."""
    return _rows(
        "SELECT id, kind, ref_id, amount, account, paid_at, approved_by "
        "FROM payments WHERE approved_by IS NULL OR approved_by = '' ORDER BY id"
    )


@mcp.tool
def list_payments() -> list[dict]:
    """Every payment row, including ones a human already stamped."""
    return _rows(
        "SELECT id, kind, ref_id, amount, account, paid_at, approved_by "
        "FROM payments ORDER BY id"
    )


def apply_approved_payment(payment_id: int, approved_by: str) -> dict:
    """Move cash. Called from the FastAPI human-approve route, not from agents."""
    if not approved_by or approved_by.strip().lower() in {"agent", "boss", "system"}:
        return {"ok": False, "reason": "a named human has to approve"}
    pay = _one("SELECT * FROM payments WHERE id = ?", (payment_id,))
    if not pay:
        return {"ok": False, "reason": f"payment {payment_id} not found"}
    if pay["approved_by"] not in (None, ""):
        return {"ok": False, "reason": "already approved", **dict(pay)}
    cash = get_cash()
    balance = float(cash.get("balance") or 0)
    amount = float(pay["amount"])
    if amount > balance:
        return {
            "ok": False,
            "reason": f"checking is ${balance:.2f}; refuse negative balance",
        }
    desk = get_desk()
    today = desk.get("date_today")
    new_balance = round(balance - amount, 2)
    lease = _one("SELECT id, next_due FROM leases WHERE id = ?", (pay["ref_id"],)) if pay["kind"] == "rent" else None
    with _connect() as conn:
        conn.execute(
            "UPDATE cash_accounts SET balance = ?, date = ? WHERE name = 'checking'",
            (new_balance, today),
        )
        conn.execute(
            "UPDATE payments SET paid_at = ?, approved_by = ? WHERE id = ?",
            (today, approved_by, payment_id),
        )
        if pay["kind"] == "invoice":
            conn.execute(
                "UPDATE invoices SET status = 'paid' WHERE id = ?",
                (pay["ref_id"],),
            )
        if pay["kind"] == "rent" and lease and lease.get("next_due"):
            due = datetime.strptime(str(lease["next_due"])[:10], "%Y-%m-%d")
            if due.month == 12:
                nxt = due.replace(year=due.year + 1, month=1)
            else:
                nxt = due.replace(month=due.month + 1)
            conn.execute(
                "UPDATE leases SET next_due = ? WHERE id = ?",
                (nxt.strftime("%Y-%m-%d"), pay["ref_id"]),
            )
        conn.commit()
    return {
        "ok": True,
        "payment_id": payment_id,
        "kind": pay["kind"],
        "ref_id": pay["ref_id"],
        "amount": amount,
        "checking": new_balance,
        "approved_by": approved_by,
    }


@mcp.tool
def pick_stock(sku: str, size: str, qty: int, reason: str) -> dict:
    """Take units off the shelf for a filled customer order.

    Args:
        sku: Catalogue SKU.
        size: Size code.
        qty: Units to pick. Must be > 0 and <= on-hand.
        reason: Why, for the audit.
    """
    if qty <= 0:
        return {"ok": False, "reason": "qty must be positive"}
    row = _one("SELECT sku, size, qty FROM inventory WHERE sku = ? AND size = ?", (sku, size))
    if not row:
        return {"ok": False, "reason": f"no shelf row for {sku} {size}"}
    on_hand = int(row["qty"])
    if qty > on_hand:
        return {"ok": False, "reason": f"only {on_hand} on hand", "qty": on_hand}
    new_qty = on_hand - qty
    _execute(
        "UPDATE inventory SET qty = ? WHERE sku = ? AND size = ?",
        (new_qty, sku, size),
    )
    return {"ok": True, "sku": sku, "size": size, "qty": new_qty, "picked": qty, "reason": reason}


@mcp.tool
def receive_stock(sku: str, size: str, qty: int, reason: str) -> dict:
    """Add units to a shelf after a vendor is allowed to ship.

    Args:
        sku: Catalogue SKU.
        size: Size code.
        qty: Units to add. Must be > 0.
        reason: Why, for the audit.
    """
    if qty <= 0:
        return {"ok": False, "reason": "qty must be positive"}
    row = _one("SELECT sku, size, qty FROM inventory WHERE sku = ? AND size = ?", (sku, size))
    if not row:
        return {"ok": False, "reason": f"no shelf row for {sku} {size}"}
    new_qty = int(row["qty"]) + qty
    _execute(
        "UPDATE inventory SET qty = ? WHERE sku = ? AND size = ?",
        (new_qty, sku, size),
    )
    return {"ok": True, "sku": sku, "size": size, "qty": new_qty, "added": qty, "reason": reason}


@mcp.tool
def update_ticket(ticket_id: int, status: str, notes: str) -> dict:
    """Set ticket status and notes. status is open or resolved.

    Args:
        ticket_id: 101, 102, or 103.
        status: open or resolved.
        notes: What the desk decided.
    """
    if status not in {"open", "resolved"}:
        return {"ok": False, "reason": "status must be open or resolved"}
    existing = _one("SELECT id FROM tickets WHERE id = ?", (ticket_id,))
    if not existing:
        return {"ok": False, "reason": f"ticket {ticket_id} not found"}
    _execute(
        "UPDATE tickets SET status = ?, notes = ? WHERE id = ?",
        (status, notes, ticket_id),
    )
    return {"ok": True, "ticket_id": ticket_id, "status": status, "notes": notes}


if __name__ == "__main__":
    mcp.run()
