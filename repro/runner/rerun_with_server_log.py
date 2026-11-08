#!/usr/bin/env python3
"""Re-run one case from repro_cases.py with the server's logging switched on.

Why this exists: in the 2025 runs the harness recorded what the client received, and the MCP
server converts a tool exception into `is_error=True` plus a one-line `TextContent`, so the
traceback stayed in the server's own stderr and was never written to disk. Turning the server
logger up brings it back. The result is a NEW run -- say so in any file produced from it.

Two environment notes, both learned the hard way:

* `Client(url, mode="auto")` (what repro_framework.py uses) negotiates `server/discover` in this
  build and then posts the call to a percent-encoded path, which answers 404. `mode="legacy"`
  takes the plain initialize handshake and works.
* the server runs as an in-process asyncio task, so its logging lands on this process's stderr;
  no separate log file is needed.

Usage:
    python repro/runner/rerun_with_server_log.py 110            # print the transcript
    python repro/runner/rerun_with_server_log.py 110 --port 9400 > out.log 2>&1

This script never writes into `data/` -- the 2025 record is left untouched.
"""
import argparse
import asyncio
import logging
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import mcp                                     # noqa: E402
import repro_cases as rc                       # noqa: E402
import repro_framework as rf                   # noqa: E402

_RealClient = mcp.Client


def _legacy(url, **kw):
    kw["mode"] = "legacy"
    return _RealClient(url, **kw)


rf.Client = _legacy


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("issue", type=int)
    ap.add_argument("--port", type=int, default=9400)
    args = ap.parse_args()

    if args.issue not in rc.CASES:
        print("no Case definition for #%d" % args.issue)
        return 3

    logging.basicConfig(level=logging.INFO, stream=sys.stderr,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    for name in ("mcp", "mcp.server", "mcp.server.mcpserver"):
        logging.getLogger(name).setLevel(logging.DEBUG)

    case = rc.CASES[args.issue]
    ct = getattr(case, "client_timeout", 0.0)
    r = asyncio.run(rf.run_case(case, args.port, ct))
    print("----- CAPTURED -----")
    print(r["message"])
    print("----- VIA -----")
    print(r["via"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
