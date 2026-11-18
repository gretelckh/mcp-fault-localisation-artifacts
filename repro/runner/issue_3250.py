#!/usr/bin/env python3
"""Reproduction for issue #3250 (OAuthClientProvider._initialize() breaks transparent refresh: missing update_token_expiry ).

Uses the real mcp 2.2.0 API. Transport: not_applicable.
"""
import asyncio
from mcp.client.auth.oauth2 import OAuthClientProvider, TokenStorage
from mcp.shared.auth import OAuthClientMetadata, OAuthToken


class _Storage(TokenStorage):
    async def get_tokens(self):
        return OAuthToken(access_token="at-stale", token_type="Bearer",
                          expires_in=-3600, refresh_token="rt")
    async def set_tokens(self, t): pass
    async def get_client_info(self): return None
    async def set_client_info(self, c): pass


def repro_3250():
    provider = OAuthClientProvider(
        server_url="http://x",
        client_metadata=OAuthClientMetadata(redirect_uris=["http://localhost/cb"]),
        storage=_Storage(),
    )
    async def run():
        await provider._initialize()
        return provider.context.token_expiry_time, provider.context.is_token_valid()
    expiry, valid = asyncio.run(run())
    return ("after _initialize: token_expiry_time=%s; is_token_valid()=%s "
            "(token expired 1h ago); stale Bearer sent with 0 refreshes" % (expiry, valid))


if __name__ == "__main__":
    print(repro_3250())
