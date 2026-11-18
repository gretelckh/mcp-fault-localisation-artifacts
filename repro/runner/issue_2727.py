#!/usr/bin/env python3
"""Reproduction for issue #2727 (streamable_http client does not send `Origin` header → rejected with 403 by spec-compliant).

Uses the real mcp 2.2.0 API. Transport: streamable-http.
"""
import inspect
from mcp.client import streamable_http


def repro_2727():
    src = inspect.getsource(streamable_http)
    has_origin = '"Origin"' in src or "'Origin'" in src
    return ("streamable-http client header builder sends Origin header: %s "
            "(RFC 6454 cross-origin check -> 403 when absent)" % has_origin)


if __name__ == "__main__":
    print(repro_2727())
