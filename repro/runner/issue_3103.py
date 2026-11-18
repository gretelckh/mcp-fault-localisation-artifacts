#!/usr/bin/env python3
"""Reproduction for issue #3103 (RequireAuthMiddleware omits RFC 6750 scope in WWW-Authenticate on 401/403).

Uses the real mcp 2.2.0 API. Transport: not_applicable.
"""
import inspect
from mcp.server.auth.middleware.bearer_auth import RequireAuthMiddleware


def repro_3103():
    src = inspect.getsource(RequireAuthMiddleware._send_auth_error)
    has_scope = "scope=" in src
    return ("_send_auth_error: www_auth_parts=[error, error_description(, resource_metadata)] "
            "-> Bearer ...; scope= parameter %s" % ("present" if has_scope else "is missing"))


if __name__ == "__main__":
    print(repro_3103())
