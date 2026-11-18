#!/usr/bin/env python3
"""As-recorded reproduction code for issue #3384.

This is the EXACT snippet captured in repro/captures/issue_3384.txt section 1.
It is preserved as EVIDENCE, not a runnable reproduction: the author never
released the original script, and this fragment uses imports/APIs that do not
exist in the pinned mcp 2.2.0 (e.g. fake internal modules). Status: valid Python syntax.
Transport: see data/transport_72.csv.
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
