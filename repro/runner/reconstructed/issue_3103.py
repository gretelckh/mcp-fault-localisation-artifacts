#!/usr/bin/env python3
"""Reconstructed reproduction for issue #3103 (WWW-Authenticate omits scope).
RECONSTRUCTED from the capture's recorded trigger; original script not released.
Transport: not_applicable (pure logic / source-inspection test)."""
import inspect
from mcp.server.auth.middleware.bearer_auth import RequireAuthMiddleware


def repro_3103():
    src = inspect.getsource(RequireAuthMiddleware._send_auth_error)
    has_scope = "scope=" in src
    return ("_send_auth_error: www_auth_parts=[error, error_description(, resource_metadata)] "
            "-> Bearer ...; scope= parameter %s" % ("present" if has_scope else "is missing"))


if __name__ == "__main__":
    print(repro_3103())
