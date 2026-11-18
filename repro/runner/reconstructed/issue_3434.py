#!/usr/bin/env python3
"""As-recorded reproduction code for issue #3434.

This is the EXACT snippet captured in repro/captures/issue_3434.txt section 1.
It is preserved as EVIDENCE, not a runnable reproduction: the author never
released the original script, and this fragment uses imports/APIs that do not
exist in the pinned mcp 2.2.0 (e.g. fake internal modules). Status: valid Python syntax.
Transport: see data/transport_72.csv.
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
