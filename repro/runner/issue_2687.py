#!/usr/bin/env python3
"""Reproduction for issue #2687 (`OAuthClientInformationFull.redirect_uris`: pydantic strict-type-equality breaks `AnyUrl(x).

Uses the real mcp 2.2.0 API. Transport: not_applicable.
"""
from pydantic import AnyUrl, AnyHttpUrl
from mcp.shared.auth import OAuthClientInformationFull


def repro_2687():
    a = OAuthClientInformationFull(client_id="a", redirect_uris=[AnyUrl("https://x/cb")])
    b = OAuthClientInformationFull(client_id="a", redirect_uris=[AnyHttpUrl("https://x/cb")])
    return "a.redirect_uris==b.redirect_uris : %s; a==b : %s" % (
        a.redirect_uris == b.redirect_uris, a == b)


if __name__ == "__main__":
    print(repro_2687())
