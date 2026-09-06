"""Reusable MCP client that owns one stdio session with the hospital server."""

from __future__ import annotations

from contextlib import AsyncExitStack
import os
from pathlib import Path
import sys
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class HospitalMCPClient:
    """Connect, initialize, discover tools and execute tools over MCP."""

    def __init__(self, server_module: str = "hospital_mcp.server") -> None:
        self._server_module = server_module
        self._exit_stack: AsyncExitStack | None = None
        self._session: ClientSession | None = None
        self.initialization_result: Any | None = None

    async def connect(self) -> "HospitalMCPClient":
        if self._session is not None:
            return self

        project_root = Path(__file__).resolve().parents[1]
        environment = os.environ.copy()
        environment["PYTHONPATH"] = os.pathsep.join(
            filter(
                None,
                [str(project_root), environment.get("PYTHONPATH", "")],
            )
        )

        server_parameters = StdioServerParameters(
            command=sys.executable,
            args=["-m", self._server_module],
            env=environment,
        )

        exit_stack = AsyncExitStack()
        try:
            read_stream, write_stream = await exit_stack.enter_async_context(
                stdio_client(server_parameters)
            )
            session = await exit_stack.enter_async_context(
                ClientSession(read_stream, write_stream)
            )
            initialization_result = await session.initialize()
        except Exception:
            await exit_stack.aclose()
            raise

        self._exit_stack = exit_stack
        self._session = session
        self.initialization_result = initialization_result
        return self

    async def list_tools(self) -> list[Any]:
        session = self._require_session()
        response = await session.list_tools()
        return list(response.tools)

    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> Any:
        return await self._require_session().call_tool(tool_name, arguments)

    async def close(self) -> None:
        if self._exit_stack is not None:
            await self._exit_stack.aclose()
        self._exit_stack = None
        self._session = None
        self.initialization_result = None

    def _require_session(self) -> ClientSession:
        if self._session is None:
            raise RuntimeError("MCP client is not connected")
        return self._session

    async def __aenter__(self) -> "HospitalMCPClient":
        return await self.connect()

    async def __aexit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        await self.close()

