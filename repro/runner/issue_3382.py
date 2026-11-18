#!/usr/bin/env python3
"""Reproduction for issue #3382 (OAuthClientProvider auth lock is permanently poisoned when httpx closes async_auth_flow fr).

Uses the real mcp 2.2.0 API. Transport: streamable-http.
"""

import asyncio
import httpx2
from mcp.client.auth.oauth2 import OAuthClientProvider
from mcp.shared.auth import OAuthClientMetadata


class MemStorage:
    async def get_tokens(self): return None
    async def set_tokens(self, tokens): pass
    async def get_client_info(self): return None
    async def set_client_info(self, client_info): pass


async def main():
    provider = OAuthClientProvider(
        server_url="https://example.invalid/mcp",
        client_metadata=OAuthClientMetadata(redirect_uris=["http://localhost:1/callback"]),
        storage=MemStorage(),
    )

    # Task A: advance the flow. With no stored tokens it suspends at
    # `response = yield request`, still inside `async with context.lock`.
    flow = provider.async_auth_flow(httpx2.Request("POST", "https://example.invalid/mcp"))
    await flow.asend(None)

    # Task B: httpx tears the stream down from a different task on
    # cancellation, closing the generator there.
    try:
        await asyncio.get_running_loop().create_task(flow.aclose())
    except RuntimeError as exc:
        print(f"aclose raised: {exc!r}")            # <- fires

    print("lock still held:", provider.context.lock.locked())   # True

    # The "reconnect" — blocks forever at line 582:
    flow2 = provider.async_auth_flow(httpx2.Request("POST", "https://example.invalid/mcp"))
    try:
        await asyncio.wait_for(flow2.asend(None), timeout=2)
        print("second flow proceeds")
    except asyncio.TimeoutError:
        prin
