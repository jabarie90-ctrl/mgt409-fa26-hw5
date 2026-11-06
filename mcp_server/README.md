# Campus Customs MCP server

FastMCP server for the shop desk. Agents and the FastAPI backend read and write `data/campus_customs_new.db` through these tools. They never invent rows.

Working database: `data/campus_customs_new.db` (copy of `data/campus_customs.db`).

Run (stdio, for Cursor):

```
python mcp_server/server.py
```

## Tools

- `get_sku_stock` — `inventory`. Ticket 101: Tauhid’s `CC-TEE-WHITE` size S is qty 0.
- `get_lease` — `leases`. Ticket 102: Elm City Properties rent is $2,400 due 2026-09-02 on lease 1.
- `get_sku_pricing` — `pricing`. Ticket 103: Yale AI Club hoodies, cost $22 / list $58.
- `get_desk` — `desk`. Shop calendar. `date_today` is 2026-08-31.
- `get_cash` — `cash_accounts`. Checking starts at $3,400. Cash only goes out.
- `list_tickets` / `get_ticket` — `tickets`. Board rows 101, 102, 103.
- `get_invoice` — `invoices`. Ticket 101 points at invoice 501 ($840, overdue).
- `get_vendor` — `vendors`. Bulldog Print Co is vendor 1, 5-day lead.
- `vendor_can_ship` — `invoices` + `vendors`. False while that vendor still has an open invoice.
- `list_inventory_for_sku` — `inventory`. Every size on the shelf for one SKU.
- `prepare_payment` — `payments` + `cash_accounts`. Stages a pay. Does not move cash.
- `pending_payments` — `payments`. Rows waiting on a human.
- `list_payments` — `payments`. Every pay, including ones a human already stamped.
- `receive_stock` — `inventory`. Add units after the vendor is allowed to ship.
- `pick_stock` — `inventory`. Take units off the shelf for a filled order.
- `update_ticket` — `tickets`. Set status to open or resolved.

Human approve is **not** an MCP tool. FastAPI `POST /approve-pay` is the only path that calls `apply_approved_payment` and deducts checking.
