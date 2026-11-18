#!/usr/bin/env python3
"""Reproduction for issue #3209 (Bug: OAuth provider holds context.lock for the whole request, so the standalone GET SSE st).

Uses the real mcp 2.2.0 API. Transport: streamable-http.
"""
import asyncio, time
import httpx2
from mcp.client.auth.oauth2 import OAuthClientProvider, TokenStorage
from mcp.shared.auth import OAuthClientMetadata, OAuthToken


class _Storage(TokenStorage):
    async def get_tokens(self):
        return OAuthToken(access_token="at", token_type="Bearer", expires_in=99999)
    async def set_tokens(self, t): pass
    async def get_client_info(self): return None
    async def set_client_info(self, c): pass


def repro_3209():
    provider = OAuthClientProvider(
        server_url="http://127.0.0.1:9999",
        client_metadata=OAuthClientMetadata(redirect_uris=["http://localhost/cb"]),
        storage=_Storage(),
    )
    async def one():
        flow = provider.async_auth_flow(httpx2.Request("GET", "http://127.0.0.1:9999/mcp"))
        await flow.__anext__()
        await asyncio.sleep(0.3)
        try:
            await flow.asend(httpx2.Response(200))
        except StopAsyncIteration:
            pass
    async def run():
        t = time.time()
        await asyncio.gather(one(), one(), one())
        return time.time() - t
    elapsed = asyncio.run(run())
    return ("3 concurrent GET /mcp: elapsed %.3fs (fully serialised; "
            "parallel would be ~0.3s)" % elapsed)


if __name__ == "__main__":
    print(repro_3209())
