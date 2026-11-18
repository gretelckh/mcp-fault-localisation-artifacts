#!/usr/bin/env python3
"""Reproduction for issue #2260 (Server OAuth metadata hardcodes token_endpoint_auth_methods_supported, breaking public cli).

Uses the real mcp 2.2.0 API. Transport: not_applicable.
"""
from pydantic import AnyHttpUrl
from mcp.server.auth.routes import build_metadata
from mcp.server.auth.settings import ClientRegistrationOptions, RevocationOptions


def repro_2260():
    m = build_metadata(
        issuer_url=AnyHttpUrl("https://as.example"),
        service_documentation_url=None,
        client_registration_options=ClientRegistrationOptions(enabled=False),
        revocation_options=RevocationOptions(enabled=False),
    )
    return "token_endpoint_auth_methods_supported = %r" % m.token_endpoint_auth_methods_supported


if __name__ == "__main__":
    print(repro_2260())
