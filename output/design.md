# Campus Customs board — look

The desk is meant to feel like the night shift at the Chapel Street shop, not a default Vite starter.

## Layout

Three columns on a wide screen:

1. **Spike** — the three tickets as carbon-copy shop tickets (number, requester, SKU). Click one to select it. Open tickets are mustard; resolved tickets get a red “RESOLVED” stamp overlay.
2. **Radio** — five agent lanes (Boss, Inventory, Accounting, Facilities, Customer Service). While a run is live, new tool / handoff lines append in that agent’s lane. After the run, each lane collapses to a two-line summary of what that agent actually did.
3. **Till** — shop date (2026-08-31, not the laptop clock), checking as LED-style digits, and a pending-pay stack. Approve is a rubber stamp, not a generic primary button. Reset sits small at the bottom so you cannot tap it by accident.

On a narrow screen the spike stays on top, radio in the middle, till under it.

## How agents read differently

Each lane has its own stripe so you can scan who is talking without reading the role name:

- Boss — brass
- Inventory — shelf green
- Accounting — ledger burgundy
- Facilities — brick
- Customer Service — note-paper cream

Handoffs render as a ticket passing from one lane to the next. Tool results stay in the caller’s lane.

## Resolved tickets and cash

A resolved ticket keeps its body text but the stamp covers the status chip so you cannot miss it. Checking digits tick down only after a human stamps a pay — the board polls `/cash` and `/payments/pending` after Approve, not after the agent merely stages the row.

## Creative choices

- Paper ticket texture and a navy “after hours” background, because this is a Broadway merch counter, not a SaaS settings page.
- A visible human stamp for money. The whole point of the shop rules is that agents cannot move cash; the UI should make that feel physical.
- Shop-today in the till header so overdue math stays tied to 2026-08-31.
