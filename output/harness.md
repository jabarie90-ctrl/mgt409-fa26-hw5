# Campus Customs operations harness

Shop “today” is `desk.date_today` = **2026-08-31**. Checking starts at **$3,400**. Three open tickets: **101**, **102**, **103**. Working copy is `data/campus_customs_new.db`. Original `data/campus_customs.db` stays frozen.

## Tables

### `desk`

Fields: `date_today`, `notes`.

This is the shop calendar. Overdue invoices and rent use `date_today`, not the laptop clock.

### `tickets`

Fields: `id`, `type`, `requester`, `subject`, `sku`, `size`, `qty`, `lease_id`, `invoice_id`, `status`, `notes`, `created_at`.

The board. 101 is a size-S tee order, 102 is rent, 103 is a 20-hoodie discount ask. Agents resolve rows here; they do not invent tickets.

### `inventory`

Fields: `sku`, `name`, `size`, `qty`, `location`.

Stock by SKU and size. Ticket 101 needs `CC-TEE-WHITE` / S (qty **0**). Ticket 103 needs 20 × `CC-HOOD-NAVY` / M (qty **8**).

### `pricing`

Fields: `sku`, `unit_cost`, `list_price`.

What we pay a vendor vs what we ring up. Ticket 103’s bulk ask has to clear margin against `unit_cost` 22 / `list_price` 58 on the hoodie.

### `vendors`

Fields: `id`, `name`, `specialty`, `lead_days`.

Who can reprint and how long they take. `Bulldog Print Co` (id 1) is apparel, 5-day lead. A vendor with an open invoice does not ship.

### `invoices`

Fields: `id`, `vendor_id`, `amount`, `due_date`, `status`, `description`.

Invoice **501** is $840 to vendor 1, due **2026-08-28**, status `open`. That is overdue as of 8/31. Ticket 101 points at this invoice. Pay it (human approve) before that vendor reprints the missing S tees.

### `leases`

Fields: `id`, `space_name`, `landlord`, `monthly_rent`, `next_due`, `notes`.

Chapel Street shop, Elm City Properties, **$2,400** due **2026-09-02**. Ticket 102 is this rent notice.

### `cash_accounts`

Fields: `name`, `balance`, `date`.

One row: `checking` = **3400** on 2026-08-31. Cash only goes out. Pay tools must refuse if the balance would go negative.

### `payments`

Fields: `id`, `kind`, `ref_id`, `amount`, `account`, `paid_at`, `approved_by`.

Empty until a human approves a pay. Staged rows sit with empty `approved_by` until FastAPI `POST /approve-pay`. That is the audit of money leaving checking.

P4 smoke (`output/mcp_smoke.json`) was captured on a fresh working copy, identical to `data/campus_customs.db` (S tee qty **0**, lease **$2,400** due **2026-09-02**, hoodie **22 / 58**). After Problem 9 the working copy has S qty **104** and checking **$160**. Those three smoke outputs still match the original file.

## MCP tools (Problem 3)

- `get_sku_stock` — table `inventory` — ticket **101**. Tauhid asked for `CC-TEE-WHITE` size S. This tool is the one that returns qty **0**, so the desk knows the tee is not on Aisle B and a reprint has to be considered.
- `get_lease` — table `leases` — ticket **102**. The rent email is lease 1. This tool is the one that returns **$2,400** due **2026-09-02** to Elm City Properties, which is the number accounting has to stage for a human pay.
- `get_sku_pricing` — table `pricing` — ticket **103**. The club wants 20 hoodies. This tool is the one that returns unit cost **22** and list **58**, so accounting can tell whether a bulk cut still covers cost.

## MCP tools added for the team (Problem 5)

- `get_desk` — `desk`. Shop calendar. Overdue means `due_date` < `date_today` (2026-08-31), not the laptop clock.
- `get_cash` — `cash_accounts`. Checking balance. `prepare_payment` refuses if amount > this number.
- `list_tickets` — `tickets`. Open / resolved / all rows on the board.
- `get_ticket` — `tickets`. One ticket plus the sku / lease / invoice columns that join the rest of the shop.
- `get_invoice` — `invoices`. Ticket 101’s invoice 501 ($840, due 2026-08-28, open).
- `get_vendor` — `vendors`. Name, specialty, `lead_days`. Bulldog Print Co is vendor 1, 5 days.
- `vendor_can_ship` — `invoices` + `vendors`. False while vendor 1 still has invoice 501 open.
- `list_inventory_for_sku` — `inventory`. Every size of one SKU. Ticket 103 uses this to see M is 8, not 20.
- `prepare_payment` — `payments` + `cash_accounts`. Stages invoice / rent / restock. Does not deduct checking.
- `pending_payments` — `payments`. Rows waiting on a named human.
- `list_payments` — `payments`. Stamped rows too, so a second run does not treat an already-paid rent as a new shortfall.
- `receive_stock` — `inventory`. Add units after `vendor_can_ship` is true. Ticket 101 reprint is 840/8 = 105 S tees.
- `pick_stock` — `inventory`. Take Tauhid’s 1 S tee off the shelf after the reprint lands.
- `update_ticket` — `tickets`. Set status `open` or `resolved` and write the desk notes.

`apply_approved_payment` is a Python function on the FastAPI human-approve route. It is not an MCP tool, so agents cannot move cash.

## Agents

- **Boss** (`backend/prompts/boss.md`) — reads the ticket, picks who works first, returns the verdict. Does not pick stock or draft customer copy.
- **Inventory** (`backend/prompts/inventory.md`) — shelf qty, shortfall, vendor lead, receive / pick. Does not stage pays.
- **Accounting** (`backend/prompts/accounting.md`) — cash, overdue invoices, margin vs unit cost, `prepare_payment` only.
- **Facilities** (`backend/prompts/facilities.md`) — lease 1 rent due 2026-09-02. Hands the $2,400 to Accounting.
- **Customer Service** (`backend/prompts/customer_service.md`) — drafts stay on the ticket. Never emails Tauhid, the club, or Elm City Properties.

Full connectivity: every agent can `ask_teammate` (depth max 3). Shop facts go through MCP only. Model is `gpt-6-luna` for every agent. Runs append to `output/audit_trail.json`.

## API routes (Problem 7)

- `GET /tickets` — three board rows and whether each is open or resolved
- `POST /tickets/{ticket_id}/run` — run the agent team on that ticket
- `GET /events` — recent agent / tool / handoff rows so the board can refresh
- `GET /payments/pending` — staged pays waiting on a human
- `POST /approve-pay` — human only; this is the route that actually changes cash
- `GET /cash` — checking balance from `cash_accounts`
- `GET /desk` — shop calendar (`date_today`)
- `POST /reset` — copy original `data/campus_customs.db` onto the working file
- `GET /health` — process is up

Start from `backend/`: `uvicorn main:app --reload --port 8000`

## Dashboard (Problem 8)

React + Vite + TypeScript in `frontend/`. Talks to `http://localhost:8000`. Layout notes are in `output/design.md`. Start with `npm run dev` (port 5173).

## Safety

What a real shop would want before agents touch customers or money:

- A named human has to approve every dollar that leaves checking. Agents only `prepare_payment`. The FastAPI route is the only caller of `apply_approved_payment`. `approved_by` cannot be `agent`, `boss`, or `system`.
- `prepare_payment` and `apply_approved_payment` both refuse if the amount would take checking below zero.
- Cash only goes out. There is no inbound-sale tool that pads the till.
- A vendor with an open invoice does not ship (`vendor_can_ship`).
- Customer Service drafts copy. Nothing emails a customer or calls a vendor.
- Overdue uses `desk.date_today`, not the laptop clock.

Token / loop limits so a stuck agent does not burn the key:

- `UsageLimits(request_limit=40, tool_calls_limit=40)` on every agent run
- `ask_teammate` depth max 3
- Boss is told not to send every specialist on every ticket
