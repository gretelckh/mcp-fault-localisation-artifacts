#!/usr/bin/env python3
"""Reproduction for issue #3566 (OAuth client scope handling breaks on comma-separated scope strings).

Uses the real mcp 2.2.0 API. Transport: not_applicable.
"""
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
