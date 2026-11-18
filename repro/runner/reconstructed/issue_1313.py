#!/usr/bin/env python3
"""Reconstructed reproduction for issue #1313 (client parses non-JSON body marked application/json).
RECONSTRUCTED from the capture's recorded trigger; original repro_json.py was
never released. The real mcp 2.2.0 JSON-RPC parser (pydantic TypeAdapter) is fed
a non-JSON body. Transport: streamable-http."""
from pydantic import TypeAdapter
from mcp.types import JSONRPCMessage


def repro_1313():
    bad = b"Error: type error in handler"
    try:
        TypeAdapter(JSONRPCMessage).validate_json(bad)
        return "parsed without error (bug not reproduced)"
    except BaseException as e:
        return "%s: %s" % (type(e).__name__, str(e)[:110])


if __name__ == "__main__":
    print(repro_1313())
