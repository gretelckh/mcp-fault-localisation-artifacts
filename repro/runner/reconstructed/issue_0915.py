#!/usr/bin/env python3
"""As-recorded reproduction code for issue #915.

This is the EXACT snippet captured in repro/captures/issue_0915.txt section 1.
It is preserved as EVIDENCE, not a runnable reproduction: the author never
released the original script, and this fragment uses imports/APIs that do not
exist in the pinned mcp 2.2.0 (e.g. fake internal modules). Status: valid Python syntax.
Transport: see data/transport_72.csv.
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
