#!/usr/bin/env python3
"""Reproduction for issue #3434 (In-process callback failures break tool calls and notification sends).

Uses the real mcp 2.2.0 API. Transport: streamable-http.
"""

import anyio

from mcp import Client
from mcp.server.mcpserver import Context, MCPServer

server = MCPServer("callback-repro")


@server.tool()
async def work(context: Context) -> str:
    await context.report_progress(1, 1)
    return "done"


async def broken_progress(progress: float, total: float | None, message: str | None) -> None:
    raise RuntimeError("consumer failed")


async def main() -> None:
    async with Client(server, mode="2026-07-28") as client:
        result = await client.call_tool("work", progress_callback=broken_progress)
        print(result.content[0].text)


anyio.run(main)
