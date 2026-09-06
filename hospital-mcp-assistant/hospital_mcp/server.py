"""Official MCP server process for the hospital database tools."""

from __future__ import annotations

import logging
import os

from mcp.server.fastmcp import FastMCP

from .tools import register_tools


logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

mcp = FastMCP(
    "hospital-database-server",
    instructions=(
        "Use these tools only for the synthetic hospital demonstration database. "
        "Never invent records that are not returned by a tool."
    ),
)

register_tools(mcp)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
