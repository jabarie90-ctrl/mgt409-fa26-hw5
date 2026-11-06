# AI_prompts.md

Log of what was typed to the vibe coder. Runtime prompts the agents read live in `backend/prompts/`.

Created at the start of Homework 5. Each of Problems 2–11 has its own section and is filled only when that problem is actually worked.

---

## Problem 1: Vibe coder prompts

**Prompt I typed:** Lets work through hw 5.

**What was lacking after the first prompt:** (none yet)

**Evidence this was its own step:** `AI_prompts.md` exists with a section for each problem. The database copy and harness are Problem 2.

---

## Problem 2: Study the Campus Customs database

**Prompt I typed:** Lets work through hw 5. Open the shop database, copy it to a working file, and write down every table for the agents.

**What was lacking after the first prompt:** (none yet)

**Evidence this was its own step:** `data/campus_customs_new.db` exists, original `data/campus_customs.db` is untouched, `output/harness.md` lists every table from the real schema.

---

## Problem 3: Build the MCP server

**Prompt I typed:** Write an MCP server for the shop that talks to the working database. Start with three tools we actually need for the open tickets: shelf qty for the missing S tee, the Chapel Street lease, and hoodie cost vs list.

**What was lacking after the first prompt:** (none yet)

**Evidence this was its own step:** `mcp_server/server.py` has `get_sku_stock`, `get_lease`, `get_sku_pricing`. `output/harness.md` ties each tool to ticket 101 / 102 / 103. `mcp_server/README.md` exists.

---

## Problem 4: Add the MCP server to vibe coder and test each tool

**Prompt I typed:** Point Cursor at the MCP server from this project and actually call those three tools. Save what I asked and what came back.

**What was lacking after the first prompt:** (none yet)

**Evidence this was its own step:** `.mcp.json` at the HW5 root. `output/mcp_smoke.json` has the three calls matching the database (S tee qty 0, rent $2400 due 2026-09-02, hoodie 22 / 58).

---

## Problem 5: Build the agent team and grow the MCP tools

**Prompt I typed:** Stand up five agents — Boss, Inventory, Accounting, Facilities, Customer Service — with their own prompt files in my words. Shop facts have to come from MCP. They can hand work to each other. Grow the MCP tools so they can stage a pay without moving cash, check whether a vendor can ship, receive and pick stock, and close a ticket. Keep an audit log.

**What was lacking after the first prompt:** (none yet)

**Evidence this was its own step:** `backend/prompts/` has one file per agent. `backend/team.py` wires PydanticAI on `gpt-6-luna`. `output/audit_trail.json` is appended, not wiped. Harness lists every agent and every MCP tool plus the safety / token limits.

---

## Problem 6: Plan the three tickets

**Prompt I typed:** Before we let them loose, write what I expect on each ticket: who the Boss calls first, the handoffs (not everyone), and which MCP tools. Put it on a page with tabs for 101 / 102 / 103 plus empty Cash and Reflection tabs.

**What was lacking after the first prompt:** (none yet)

**Evidence this was its own step:** `output/desk_tickets.html` Expected sections were filled before the live run. Actual, Cash, and Reflection were added after Problem 9 / 10.

---

## Problem 7: Backend routes

**Prompt I typed:** Give the board a FastAPI backend that lists tickets, runs one ticket, streams the recent agent events, lets a human approve a pay, shows checking, and can reset the books.

**What was lacking after the first prompt:** (none yet)

**Evidence this was its own step:** `backend/main.py` has those routes. Harness lists each URL. `POST /approve-pay` is the only path that deducts cash.

---

## Problem 8: Agent dashboard

**Prompt I typed:** Build a React Vite TypeScript desk that lists the three tickets, runs one, shows each agent working, lets me stamp a pay, and shows checking going down. Make it feel like the Chapel Street night shift, not a default Vite page.

**What was lacking after the first prompt:** (none yet)

**Evidence this was its own step:** `frontend/` React board. `output/design.md` records the look. Frontend calls `http://localhost:8000`. Backend CORS allows `http://localhost:5173`.

---

## Problem 9: Resolve the tickets

**Prompt I typed:** Reset the working books, run 101 then 102 then 103 on the board, stamp the pays myself, and fill Actual plus the Cash tab from what actually happened. Ending checking has to match the database.

**What was lacking after the first prompt:** Boss stopped after Inventory on 101 until I told it not to end a run after one specialist. After the rent stamp, a second run treated $160 as a new shortfall until we added list_payments.

**Evidence this was its own step:** Tickets 101–103 are resolved in `data/campus_customs_new.db`. Checking is $160. `output/desk_tickets.html` Actual and Cash are filled. `output/resolved_tickets.json`, `output/resolved_board.html`, and `output/audit_trail.json` are from this run.

---

## Problem 10: Reflection

**Prompt I typed:** Fill the Reflection tab on the same desk_tickets page. Talk about each ticket, Actual vs Expected, what would have been one agent, and three problems this team can and cannot solve — using the tickets and the Cash tab as evidence.

**What was lacking after the first prompt:** (none yet)

**Evidence this was its own step:** Reflection tab on `output/desk_tickets.html` names 101 / 102 / 103 and the $3,400 → $160 cash path.

---

## Problem 11: Submit to GitHub

**Prompt I typed:** Push this to a public GitHub repo. No real .env. Include both database files. Put the URL in output/github_url.txt.

**What was lacking after the first prompt:** (none yet)

**Evidence this was its own step:** `output/github_url.txt` is https://github.com/jabarie90-ctrl/mgt409-fa26-hw5. Public repo, no `.env`.
