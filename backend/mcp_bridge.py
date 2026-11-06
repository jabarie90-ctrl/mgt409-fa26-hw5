"""Call the FastMCP shop server. No second SQLite layer for shop facts."""
from __future__ import annotations

from typing import Any

from fastmcp import Client

from mcp_server.server import mcp


async def shop(name: str, **arguments: Any) -> Any:
    async with Client(mcp) as client:
        result = await client.call_tool(name, arguments)
        data = getattr(result, "data", None)
        if data is not None:
            return data
        structured = getattr(result, "structured_content", None)
        if structured is not None:
            return structured
        return result
