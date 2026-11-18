#!/usr/bin/env python3
"""Reconstructed reproduction for issue #3240 (OAuth refresh hits wrong endpoint under a path).
RECONSTRUCTED from the capture's recorded trigger; original script not released.
Uses the real mcp 2.2.0 _refresh_token. Transport: streamable-http (refresh POST)."""
import asyncio
from mcp.client.auth.oauth2 import OAuthClientProvider, TokenStorage
from mcp.shared.auth import OAuthClientMetadata, OAuthToken, OAuthClientInformationFull


class _Storage(TokenStorage):
    async def get_tokens(self):
        return OAuthToken(access_token="at", token_type="Bearer", expires_in=-3600,
                          refresh_token="rt")
    async def set_tokens(self, t): pass
    async def get_client_info(self):
        return OAuthClientInformationFull(client_id="cid")
    async def set_client_info(self, c): pass


def repro_3240():
    provider = OAuthClientProvider(
        server_url="http://127.0.0.1:9999/auth",
        client_metadata=OAuthClientMetadata(redirect_uris=["http://localhost/cb"]),
        storage=_Storage(),
    )
    async def run():
        await provider._initialize()
        req = await provider._refresh_token()
        return str(req.url)
    url = asyncio.run(run())
    return ("AS mounted under /auth; refresh POST hit '%s' "
            "(expected '/auth/token'); no MCP-layer error" % url.replace("http://127.0.0.1:9999", ""))


if __name__ == "__main__":
    print(repro_3240())
