#!/usr/bin/env python3
"""Reconstructed reproduction for issue #2687 (AnyUrl/AnyHttpUrl equality).
RECONSTRUCTED from the capture's recorded trigger; original script not released.
Transport: not_applicable (pure logic test)."""
from pydantic import AnyUrl, AnyHttpUrl
from mcp.shared.auth import OAuthClientInformationFull


def repro_2687():
    a = OAuthClientInformationFull(client_id="a", redirect_uris=[AnyUrl("https://x/cb")])
    b = OAuthClientInformationFull(client_id="a", redirect_uris=[AnyHttpUrl("https://x/cb")])
    return "a.redirect_uris==b.redirect_uris : %s; a==b : %s" % (
        a.redirect_uris == b.redirect_uris, a == b)


if __name__ == "__main__":
    print(repro_2687())
