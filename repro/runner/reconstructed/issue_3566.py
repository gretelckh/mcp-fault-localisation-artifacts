#!/usr/bin/env python3
"""Reconstructed reproduction for issue #3566 (comma-separated scopes).
RECONSTRUCTED from the capture's recorded trigger; original script not released.
Transport: not_applicable (pure logic test)."""
from mcp.client.auth.oauth2 import union_scopes
from mcp.shared.auth import OAuthClientInformationFull, InvalidScopeError


def repro_3566():
    u = union_scopes("read", "read,write")
    c = OAuthClientInformationFull(client_id="c", scope="read,write")
    try:
        c.validate_scope("read")
        v = "no error"
    except InvalidScopeError as e:
        v = "RAISED InvalidScopeError: %s" % e
    return "union_scopes('read','read,write') -> %r; validate_scope('read,write','read') -> %s" % (u, v)


if __name__ == "__main__":
    print(repro_3566())
