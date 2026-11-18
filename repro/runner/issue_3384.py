#!/usr/bin/env python3
"""Reproduction for issue #3384 (ClientSessionGroup raises KeyError when a server exposes no tools, resources or prompts).

Uses the real mcp 2.2.0 API. Transport: not_applicable.
"""

import anyio
import mcp_types as types
from mcp.client.client import Client
from mcp.client.session_group import ClientSessionGroup
from mcp.server.mcpserver import MCPServer

INFO = types.Implementation(name="empty", version="1.0")


async def main() -> None:
    # A server that registers no tools, no resources and no prompts.
    async with Client(MCPServer("empty")) as client:
        group = ClientSessionGroup()
        await group.connect_with_session(INFO, client.session)


anyio.run(main)
