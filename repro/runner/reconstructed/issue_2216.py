#!/usr/bin/env python3
"""Reconstructed reproduction for issue #2216 (validate_scope rejects None scopes).
RECONSTRUCTED from the capture's recorded trigger; the author's original
repro_oauth_logic.py was never released. Uses the real mcp 2.2.0 API.
Transport: not_applicable (pure logic test)."""
from mcp.shared.auth import OAuthClientInformationFull, InvalidScopeError


def repro_2216():
    c = OAuthClientInformationFull(client_id="c", scope=None)
    try:
        c.validate_scope("read")
        return "validate_scope(scope=None, req='read') -> no error (bug not reproduced)"
    except InvalidScopeError as e:
        return "validate_scope(scope=None, req='read') -> RAISED InvalidScopeError: %s" % e


if __name__ == "__main__":
    print(repro_2216())
