#!/usr/bin/env python3
"""As-recorded reproduction code for issue #76.

This is the EXACT snippet captured in repro/captures/issue_0076.txt section 1.
It is preserved as EVIDENCE, not a runnable reproduction: the author never
released the original script, and this fragment uses imports/APIs that do not
exist in the pinned mcp 2.2.0 (e.g. fake internal modules). Status: valid Python syntax.
Transport: see data/transport_72.csv.
"""

import os
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import dotenv

dotenv.load_dotenv()

async def main():
    server_params = StdioServerParameters(
        command="npx",
        args=["-y", "@modelcontextprotocol/server-github"],
        env={
            "GITHUB_PERSONAL_ACCESS_TOKEN": os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN"),
            "PATH": os.getenv("PATH")
        }
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize the connection
            await session.initialize()

            # Example: Call tool to list repositories
            repos = await session.call_tool(
                "search_repositories",
                arguments={"query": "user:adhikasp"}
            )
            print("Repositories:", repos)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
