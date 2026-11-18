#!/usr/bin/env python3
"""Reproduction for issue #409 (Error from MCP server: SyntaxError: Unexpected token 'E', 'Error: typ'... is not valid JSO).

Uses the real mcp 2.2.0 API. Transport: streamable-http.
"""
from pydantic import TypeAdapter
from mcp.types import JSONRPCMessage


def repro_0409():
    bad = b"Error: type error in handler"
    try:
        TypeAdapter(JSONRPCMessage).validate_json(bad)
        return "parsed without error (bug not reproduced)"
    except BaseException as e:
        return "%s: %s" % (type(e).__name__, str(e)[:110])


if __name__ == "__main__":
    print(repro_0409())
