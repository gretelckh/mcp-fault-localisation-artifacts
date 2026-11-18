#!/usr/bin/env python3
"""As-recorded reproduction code for issue #326.

This is the EXACT snippet captured in repro/captures/issue_0326.txt section 1.
It is preserved as EVIDENCE, not a runnable reproduction: the author never
released the original script, and this fragment uses imports/APIs that do not
exist in the pinned mcp 2.2.0 (e.g. fake internal modules). Status: valid Python syntax.
Transport: see data/transport_72.csv.
"""

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

server_params = StdioServerParameters(
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", "/home"],
        env={} # fail
        # env=None # no fail
)

async def run():
        async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                        await session.initialize()
                        tools = await session.list_tools()

if __name__ == "__main__":
        import asyncio
        asyncio.run(run())
