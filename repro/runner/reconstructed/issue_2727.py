#!/usr/bin/env python3
"""Reconstructed reproduction for issue #2727 (streamable-http client omits Origin header).
RECONSTRUCTED from the capture's recorded trigger; original repro_2727.py was
never released. Inspects the real mcp 2.2.0 streamable-http client header builder.
Transport: streamable-http."""
import inspect
from mcp.client import streamable_http


def repro_2727():
    src = inspect.getsource(streamable_http)
    has_origin = '"Origin"' in src or "'Origin'" in src
    return ("streamable-http client header builder sends Origin header: %s "
            "(RFC 6454 cross-origin check -> 403 when absent)" % has_origin)


if __name__ == "__main__":
    print(repro_2727())
