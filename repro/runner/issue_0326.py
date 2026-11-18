#!/usr/bin/env python3
"""Reproduction for issue #326 (MCP client with npx not working when env parameter of StdioServerParameters is set).

Uses the real mcp 2.2.0 API. Transport: stdio.
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
