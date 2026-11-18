#!/usr/bin/env python3
"""Reproduction for issue #2216 (Bug: validate_scope rejects client scopes when required scopes in None).

Uses the real mcp 2.2.0 API. Transport: not_applicable.
"""
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
