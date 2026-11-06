# Campus Customs Multi-Agent Operations (HW5)

Shop desk for Campus Customs on Chapel Street. Shop today is whatever `desk.date_today` says (2026-08-31 in the starter books). Five agents (Boss, Inventory, Accounting, Facilities, Customer Service) read the shop through a FastMCP server. A human on the React board has to stamp every pay before checking moves.

## Setup

```
cd "/Users/yale/Desktop/AI Class/HW5"
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Put `PORTKEY_API_KEY` in `.env` if you have one. Otherwise `OPENAI_API_KEY` is enough. Every agent uses `gpt-6-luna` only.

## Clean books

Working file is `data/campus_customs_new.db`. Original `data/campus_customs.db` stays frozen.

```
cp data/campus_customs.db data/campus_customs_new.db
```

Or hit **Reset shop books** on the board (`POST /reset`). Reset before a full three-ticket run.

## Start MCP (for Cursor)

`.mcp.json` already points at this venv and `mcp_server/server.py`. Or:

```
.venv/bin/python mcp_server/server.py
```

The FastAPI app also talks to the same FastMCP server in-process. You do not need a second MCP process just to run the board.

## Start the backend

```
cd backend
PYTHONPATH=".." ../.venv/bin/uvicorn main:app --reload --port 8000
```

API: `http://localhost:8000`

## Start the React board

```
cd frontend
npm install
npm run dev
```

Board: `http://localhost:5173`

## Three-ticket run

1. Reset the books.
2. Run ticket 101. Stamp the $840 invoice. Run 101 again so Inventory can receive the reprint and pick Tauhid’s tee.
3. Run ticket 102. Stamp the $2,400 rent. Run 102 again to close it.
4. Run ticket 103. No restock pay — checking cannot cover 12 hoodies after the two pays. Offer the 8 on the shelf.

Do not email customers. Do not call vendors. Cash only goes out. Checking cannot go negative.
