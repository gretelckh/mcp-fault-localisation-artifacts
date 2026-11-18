#!/usr/bin/env python3
"""Reproduction for issue #507 (404 Not Found Error when Establishing SSE Connection via MCP Python SDK).

Uses the real mcp 2.2.0 API. Transport: sse.
"""
import asyncio, threading, time
from http.server import BaseHTTPRequestHandler, HTTPServer
from mcp.client.sse import sse_client


class _H(BaseHTTPRequestHandler):
    def do_GET(self):
        body = b"not found"
        self.send_response(404)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def log_message(self, *a): pass


def repro_0507():
    srv = HTTPServer(("127.0.0.1", 9298), _H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    async def run():
        try:
            async with sse_client("http://127.0.0.1:9298/sse") as (r, w):
                return "connected (bug not reproduced)"
        except BaseException as e:
            return "%s: %s" % (type(e).__name__, str(e)[:90])
    try:
        res = asyncio.run(run())
    finally:
        srv.shutdown()
    return res


if __name__ == "__main__":
    print(repro_0507())
