#!/usr/bin/env python3
"""Reproduction for issue #915 (Exception in `ClientSessionGroup` if `streamable_http` MCP server is not available).

Uses the real mcp 2.2.0 API. Transport: streamable-http.
"""

import asyncio

from mcp.client.session_group import ClientSessionGroup, StreamableHttpParameters


async def main():
    async with ClientSessionGroup() as client_session_group:
        server_params = StreamableHttpParameters(url="http://localhost:3001/mcp/")
        try:
            await client_session_group.connect_to_server(server_params)
        except Exception:
            print("this is never reached")


if __name__ == "__main__":
    asyncio.run(main())
