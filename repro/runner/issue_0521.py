#!/usr/bin/env python3
"""Reproduction for issue #521 (RuntimeError: Attempted to exit cancel scope in a different task than it was entered in).

Uses the real mcp 2.2.0 API. Transport: sse.
"""
import asyncio, logging
from mcp.server.mcpserver import MCPServer
from mcp import Client

logging.disable(logging.CRITICAL)  # silence uvicorn/httpx access logs


def repro_0521():
    server = MCPServer("cs")

    @server.tool()
    def ping() -> str:
        return "pong"

    async def run():
        port = 9231
        t = asyncio.create_task(
            server.run_streamable_http_async(host="127.0.0.1", port=port))
        await asyncio.sleep(1.2)
        url = "http://127.0.0.1:%d/mcp" % port
        clients = []
        for _ in range(4):
            c = Client(url, mode="auto")
            await c.__aenter__()
            await c.list_tools()
            clients.append(c)
        async def close(c):
            await c.__aexit__(None, None, None)
        errs = []
        try:
            await asyncio.gather(
                *[close(c) for c in [clients[2], clients[0], clients[3], clients[1]]])
        except BaseException as e:
            errs.append("%s: %s" % (type(e).__name__, str(e)[:70]))
        t.cancel()
        try:
            await t
        except BaseException:
            pass
        return errs

    try:
        errs = asyncio.run(run())
    except BaseException as e:
        errs = ["%s: %s" % (type(e).__name__, str(e)[:70])]

    hits = [s for s in errs if "cancel scope" in s.lower() or "CancelledError" in s]
    if not hits:
        return "4 clients closed cleanly (bug not reproduced); raw=%r" % errs[:2]
    return "%d cancel-scope error(s), e.g. %s" % (len(hits), hits[0])


if __name__ == "__main__":
    print(repro_0521())
