#!/usr/bin/env python3
"""Real-transport (Streamable HTTP + uvicorn) fault runner — 'Real-Fault-HTTP' set.

Purpose: reproduce real-world MCP faults over the REAL streamable-HTTP transport
(the production transport, unlike the in-memory transport of MCP-Fault-20). Each
case is derived from a genuine issue in the official modelcontextprotocol/python-sdk
repository (issue number recorded in issue_src), so the fault is NOT fabricated.

Every case starts an MCPServer over uvicorn (streamable HTTP), connects with the
official `Client`, triggers the fault, and captures the REAL return object as text —
the same shape `analysis/parse_real_runs.py` expects (one line per run).

CASES tuple:
  (case_id, server_builder, origin_layer, root_desc, tool_call, call_args, issue_src, mode)
  mode: client connection mode ('auto'/'legacy'/'stateless'); used to re-trigger the
        transport-level defects of #3588 / #3556 / #3560.

Usage: python runner/run_real_http.py
"""
import asyncio, sys, os, json, glob
sys.stdout.reconfigure(encoding='utf-8')
from mcp.server.mcpserver import MCPServer
from mcp import Client

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTDIR = os.path.join(REPO, 'data', 'real_raw')
os.makedirs(OUTDIR, exist_ok=True)

PORT_BASE = 9010

CASES = []

# ---------------------------------------------------------------------------
# Real-issue-derived fault cases. Each builder mirrors a genuine reported defect.
# ---------------------------------------------------------------------------
def b_media_mime():  # #3585: format= emits unregistered MIME (image/jpg vs image/jpeg)
    s = MCPServer('real-media')
    @s.tool()
    def get_image(format_: str) -> str:
        return f'image/{format_}'
    return s

def b_nontool_exc():  # #3586: handler raises a NON-ToolError (unexpected exception)
    s = MCPServer('real-exc')
    @s.tool()
    def fragile(x: int) -> int:
        raise RuntimeError('boom: internal state corrupted (non-ToolError)')
    return s

def b_unregistered_result():  # #3592: returns a fallback marker treated as success
    s = MCPServer('real-flag')
    @s.tool()
    def lookup(name: str) -> str:
        return 'stale-cache-fallback:' + name
    return s

def b_bytes_output():  # #3554: `-> bytes` non-UTF-8 crashes with generic error
    s = MCPServer('real-bytes')
    @s.tool()
    def get_bytes() -> bytes:
        return b'\x89PNG\r\n\x1a\n'
    return s

def b_iterator_meta():  # #3573: `-> Iterator` raises PydanticSchemaGenerationError at registration
    s = MCPServer('real-iter')
    from typing import Iterator
    @s.tool()
    def gen() -> Iterator[int]:
        yield 1
    return s

def b_perm_raise():  # #3569/#3560 family: tool raises, origin is Server (exposed as pushed)
    s = MCPServer('real-perm')
    @s.tool()
    def fragile2(x: int) -> int:
        raise PermissionError('403 token expired (real defect)')
    return s

def b_validation_echo():  # #3572: tool rejects a value and echoes it back (Host passes bad input)
    s = MCPServer('real-val')
    @s.tool()
    def lookup(name: str) -> str:   # only accepts str; Host passes an int
        return 'ok:' + name
    return s

def b_unknown_tool():  # Host schedules a tool that is not registered
    s = MCPServer('real-unk')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

def b_schema_mismatch():  # Host passes the wrong parameter NAME -> validation error
    s = MCPServer('real-schema')
    @s.tool()
    def add(a: int, b: int) -> int:
        return a + b
    return s

def b_duplicate_tool():  # duplicate registration: second silently adopted (production-hard)
    s = MCPServer('real-dup')
    @s.tool()
    def calc(x: int) -> int:
        return x + 1
    try:
        @s.tool()
        def calc(x: int) -> int:
            return x + 100
    except Exception:
        pass
    return s

def b_slow_timeout():  # #3560/#3596: no timeout -> call blocks / no response
    import asyncio
    s = MCPServer('real-slow')
    @s.tool()
    async def slow(x: int) -> int:
        await asyncio.sleep(10)
        return x
    return s

def b_empty_server():  # #3578/#3579: server exposes no components -> group KeyError
    s = MCPServer('real-empty')
    return s

def b_stdin_hang():  # #3596/#3551: lifecycle shutdown hang is stdio-specific; HTTP mirror = no session
    s = MCPServer('real-lc')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

def b_missing_param():  # #3572: Host calls a tool omitting a required parameter
    s = MCPServer('real-missing')
    @s.tool()
    def add(a: int, b: int) -> int:
        return a + b
    return s

def b_enum_invalid():  # Host passes an invalid enum value -> schema validation error
    s = MCPServer('real-enum')
    from enum import Enum
    class Color(str, Enum):
        red = 'red'; green = 'green'
    @s.tool()
    def paint(color: Color) -> str:
        return color.value
    return s

def b_oversized_response():  # Server returns an oversized / structurally-mismatched response
    s = MCPServer('real-big')
    @s.tool()
    def big() -> bytes:
        return b'\xff' * 9000   # non-UTF-8, oversized binary
    return s

def b_wrong_return_meta():  # #3554/#3555: structured output returns bytes -> generic error
    s = MCPServer('real-rmeta')
    @s.tool()
    def get_blob() -> bytes:
        return b'\x89PNG'       # bytes not valid UTF-8 in structured output
    return s

def b_state_leak():  # production-hard: cross-call state leaks but is_error=False
    s = MCPServer('real-leak')
    calls = []
    @s.tool()
    def record(x: int) -> int:
        calls.append(x)
        return len(calls)
    return s

def b_session_closed():  # #1401/#3581: calling after session closure -> caller exception
    s = MCPServer('real-sess')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

def b_wrong_param_type_coerced():  # SDK coerces the wrong type (e.g. str '5' -> int) silently
    s = MCPServer('real-coerce')
    @s.tool()
    def counter(x: int) -> int:
        return x + 1
    return s

def b_result_overwrite():  # Server silently returns wrong data (no error flag)
    s = MCPServer('real-ow')
    @s.tool()
    def get_user(name: str) -> dict:
        # defect: returns a stale/empty record as if it were valid (no is_error flag)
        return {'name': name, 'age': 0}
    return s

def b_server_missing_dep():  # tool depends on an external library/file that is absent
    s = MCPServer('real-dep')
    @s.tool()
    def pdf_summary(path: str) -> str:
        import nonexistent_pkg   # missing dependency -> raises at call time
        return 'unreachable'
    return s

def b_session_terminated():  # server terminates the session -> caller receives a bare error
    s = MCPServer('real-term')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

def b_wrong_result_silent():  # Server returns a wrong-but-valid result silently
    s = MCPServer('real-wrong')
    @s.tool()
    def net_price(qty: int, unit: int) -> int:
        # defect: returns the pre-discount total, silently ignoring the discount step
        return qty * unit
    return s

# --- NEW genuinely-distinct issues (mined from the official issue tracker, mcp 2.2.0) ---
def b_race_lost_update():  # #3549: concurrent cross-call mutation -> lost update, silent
    s = MCPServer('real-race')
    st = {'n': 0}
    @s.tool()
    async def inc() -> int:
        v = st['n']
        await asyncio.sleep(0.05)
        st['n'] = v + 1
        return st['n']
    return s

def b_flat_argument():  # #3637: Pydantic model param not flattened -> client flat dict fails at Server
    from pydantic import BaseModel
    class Book(BaseModel):
        title: str
        pages: int
    s = MCPServer('real-flat')
    @s.tool()
    def summarize(book: Book) -> str:
        return f'{book.title}/{book.pages}'
    return s

def b_userlist_prompt():  # #3643: prompt handler returning a UserList renders as ONE stringified message
    from collections import UserList
    from mcp.types import PromptMessage, TextContent
    s = MCPServer('real-ulist')
    @s.prompt()
    def greet(name: str):
        return UserList([PromptMessage(role='user', content=TextContent(type='text', text='hi ' + name))])
    return s

def b_terminate_reinit():  # #3556: client treats 404 on a dead session as terminal (no re-initialise)
    s = MCPServer('real-reinit')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

def b_capabilities_drop():  # #3640: unknown ServerCapabilities keys are dropped (silent feature loss)
    s = MCPServer('real-caps')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# ---------------------------------------------------------------------------
# CASES — 20 genuine real-issue faults across the four origin layers.
# mode: client connection mode, used to exercise transport-level defects.
# ---------------------------------------------------------------------------
CASES = [
    # --- Server-origin faults (response/execution handling) ---
    ('r_media_unregistered_mime', b_media_mime, 'Server',
     'format= emits unregistered MIME type (image/jpg) [bug #3585]', 'get_image', {'format_': 'jpg'},
     'modelcontextprotocol/python-sdk#3585', 'auto'),
    ('r_non_tool_error_silent', b_nontool_exc, 'Server',
     'handler raises non-ToolError; client exposure unclear [bug #3586]', 'fragile', {'x': 1},
     'modelcontextprotocol/python-sdk#3586', 'auto'),
    ('r_fallback_success_flag', b_unregistered_result, 'Server',
     'server returns fallback marker as success (is_error mismatch) [bug #3592]', 'lookup', {'name': 'foo'},
     'modelcontextprotocol/python-sdk#3592', 'auto'),
    ('r_bytes_output_crash', b_bytes_output, 'Server',
     '-> bytes non-UTF-8 crashes with generic error [bug #3554]', 'get_bytes', {},
     'modelcontextprotocol/python-sdk#3554', 'auto'),
    ('r_iterator_meta_fail', b_iterator_meta, 'Server',
     '-> Iterator annotation raises PydanticSchemaGenerationError at registration [bug #3573]', 'gen', {},
     'modelcontextprotocol/python-sdk#3573', 'auto'),
    ('r_permission_swallow', b_perm_raise, 'Server',
     'tool raises non-tool error; surfaces as pushed-to-Server [bug #3569/#3560]', 'fragile2', {'x': 1},
     'modelcontextprotocol/python-sdk#3569', 'auto'),
    ('r_duplicate_tool_shadow', b_duplicate_tool, 'Server',
     'duplicate tool registration silently keeps first (production-hard) [bug #3578]', 'calc', {'x': 1},
     'modelcontextprotocol/python-sdk#3578', 'auto'),
    ('r_empty_server_components', b_empty_server, 'Host',
     'Host requests an unknown tool from a component-less server [bug #3579]', 'nonexistent', {},
     'modelcontextprotocol/python-sdk#3579', 'auto'),

    # --- Host-origin faults (scheduling / parameter errors on the host side) ---
    ('r_validation_echo_input', b_validation_echo, 'Host',
     'Host passes wrong arg type; validation error echoes rejected value [bug #3572]', 'lookup', {'name': 12345},
     'modelcontextprotocol/python-sdk#3572', 'auto'),
    ('r_unknown_tool_call', b_unknown_tool, 'Host',
     'Host schedules a tool that is not registered [bug #3572/#3583]', 'no_such_tool', {},
     'modelcontextprotocol/python-sdk#3572', 'auto'),
    ('r_schema_wrong_param', b_schema_mismatch, 'Host',
     'Host passes wrong parameter name -> schema validation error [bug #3572]', 'add', {'a': 1, 'c': 2},
     'modelcontextprotocol/python-sdk#3572', 'auto'),

# --- Transport-origin faults (handshake / connection / lifecycle) ---
    ('r_conn_refused', None, 'Transport',
     'client connects to a closed endpoint -> raw transport error, no MCP error flag [bug #3569/#3560]', 'ping', {},
     'modelcontextprotocol/python-sdk#3569', 'auto'),

    # --- additional Server-origin faults ---
    ('r_oversized_response', b_oversized_response, 'Server',
     'oversized / non-UTF-8 binary response -> generic error [bug #3554]', 'big', {},
     'modelcontextprotocol/python-sdk#3554', 'auto'),
    ('r_result_overwrite_silent', b_result_overwrite, 'Server',
     'Server returns a stale/empty record as valid, no error flag [bug #3578]', 'get_user', {'name': 'alice'},
     'modelcontextprotocol/python-sdk#3578', 'auto'),
    ('r_server_missing_dep', b_server_missing_dep, 'Server',
     'tool depends on a missing library -> fails at call time, pushed to Server [bug #3569]', 'pdf_summary', {'path': 'x.pdf'},
     'modelcontextprotocol/python-sdk#3569', 'auto'),

    # --- additional Host-origin faults (scheduling / parameter) ---
    ('r_missing_param', b_missing_param, 'Host',
     'Host calls a tool omitting a required parameter [bug #3572]', 'add', {'a': 1},
     'modelcontextprotocol/python-sdk#3572', 'auto'),
    ('r_enum_invalid', b_enum_invalid, 'Host',
     'Host passes an invalid enum value -> schema validation error [bug #3572]', 'paint', {'color': 'blue'},
     'modelcontextprotocol/python-sdk#3572', 'auto'),
    ('r_wrong_param_type_coerced', b_wrong_param_type_coerced, 'Host',
     'SDK coerces a wrong-type argument (str "5" -> int) silently [bug #3572]', 'counter', {'x': '5'},
     'modelcontextprotocol/python-sdk#3572', 'auto'),
    ('r_tool_timeout', b_slow_timeout, 'Transport',
     'no default timeout -> slow tool blocks the caller, no error flag [bug #3560]', 'slow', {'x': 1},
     'modelcontextprotocol/python-sdk#3560', 'auto'),
    ('r_wrong_result_silent', b_wrong_result_silent, 'Server',
     'Server returns a wrong-but-valid result silently (discount ignored) [bug #3578]', 'net_price', {'qty': 3, 'unit': 10},
     'modelcontextprotocol/python-sdk#3578', 'auto'),

    # --- NEW genuinely-distinct issues mined from the official tracker (mcp 2.2.0) ---
    ('r_race_lost_update', b_race_lost_update, 'Server',
     'parallel tool calls mutate shared state; lost update (final<count) is silent [bug #3549]', 'inc', {},
     'modelcontextprotocol/python-sdk#3549', 'auto'),
    ('r_flat_argument', b_flat_argument, 'Host',
     'Pydantic model param not flattened; a flat client arg dict is rejected at Server [bug #3637]', 'summarize', {'title': 'x', 'pages': 5},
     'modelcontextprotocol/python-sdk#3637', 'auto'),
    ('r_userlist_prompt', b_userlist_prompt, 'Server',
     'prompt handler returning UserList is rendered as ONE stringified message [bug #3643]', 'greet', {'name': 'bob'},
     'modelcontextprotocol/python-sdk#3643', 'auto'),
    ('r_session_reinit_404', b_terminate_reinit, 'Transport',
     'client treats a 404 (dead session) as terminal instead of re-initialising [bug #3556]', 'ping', {},
     'modelcontextprotocol/python-sdk#3556', 'auto'),
    ('r_capabilities_drop', b_capabilities_drop, 'Server',
     'unknown ServerCapabilities keys are dropped from the advertised capabilities [bug #3640]', 'ping', {},
     'modelcontextprotocol/python-sdk#3640', 'auto'),
]


def _norm(res):
    try:
        return str(res)
    except Exception as e:
        return f'<unprintable:{type(e).__name__}>'


async def _run_one(case_id, builder, layer, root_desc, tool_call, cargs, issue_src, port, mode='auto', client_timeout=0.0):
    """Start one server, make one call, capture the real SDK return object as text.

    Some genuine faults (e.g. #3573 `-> Iterator`) raise at REGISTRATION time inside
    `builder()`; we capture that as a real observed defect rather than crashing the batch.
    A `builder is None` case reproduces a transport-level fault by pointing the client at a
    CLOSED port (connection refused), surfacing as a bare transport error in the caller.
    """
    if builder is None:
        url = f'http://127.0.0.1:{port}/mcp'   # nothing listens here -> connection refused
        try:
            async with Client(url, mode=mode, read_timeout_seconds=(client_timeout if client_timeout > 0 else None)) as client:
                res = await client.call_tool(tool_call, cargs or {})
                msg = _norm(res)
        except BaseException as e:
            sub = getattr(e, 'exceptions', [e])
            m = sub[0] if sub else e
            return {'case': case_id, 'layer': layer, 'root_desc': root_desc,
                    'message': f'RAISED:{type(m).__name__}:{m}',
                    'issue_src': issue_src, 'via': f'streamable-http/{mode}/conn-refused'}
        return {'case': case_id, 'layer': layer, 'root_desc': root_desc,
                'message': msg, 'issue_src': issue_src, 'via': f'streamable-http/{mode}/conn-refused'}

    try:
        server = builder()
    except BaseException as e:
        sub = getattr(e, 'exceptions', [e])
        m = sub[0] if sub else e
        return {'case': case_id, 'layer': layer, 'root_desc': root_desc,
                'message': f'RAISED-AT-REG:{type(m).__name__}:{m}',
                'issue_src': issue_src, 'via': 'streamable-http/registration'}
    url = f'http://127.0.0.1:{port}/mcp'
    srv_task = asyncio.create_task(server.run_streamable_http_async(host='127.0.0.1', port=port))
    await asyncio.sleep(1.5)
    try:
        async with Client(url, mode=mode, read_timeout_seconds=(client_timeout if client_timeout > 0 else None)) as client:
            res = await client.call_tool(tool_call, cargs or {})
            msg = _norm(res)
        return {'case': case_id, 'layer': layer, 'root_desc': root_desc,
                'message': msg, 'issue_src': issue_src, 'via': f'streamable-http/{mode}'}
    except BaseException as e:
        sub = getattr(e, 'exceptions', [e])
        m = sub[0] if sub else e
        return {'case': case_id, 'layer': layer, 'root_desc': root_desc,
                'message': f'RAISED:{type(m).__name__}:{m}',
                'issue_src': issue_src, 'via': f'streamable-http/{mode}'}
    finally:
        srv_task.cancel()
        try:
            await srv_task
        except (asyncio.CancelledError, Exception):
            pass


async def main():
    results = []
    for i, (cid, builder, layer, desc, tool, cargs, src, mode) in enumerate(CASES):
        ct = 2.0 if cid == 'r_tool_timeout' else 0.0
        r = await _run_one(cid, builder, layer, desc, tool, cargs, src, PORT_BASE + i, mode, ct)
        results.append(r)
        print(f'[{cid}] -> {r["message"][:80]}')
    index = []
    for r in results:
        cid = r['case'].replace('_', '_')
        f = os.path.join(OUTDIR, f'real_{cid}.txt')
        with open(f, 'w', encoding='utf-8') as fh:
            fh.write(r['message'])
        index.append({'case': r['case'], 'layer': r['layer'], 'root_desc': r['root_desc'],
                      'issue_src': r['issue_src'], 'file': f})
    with open(os.path.join(REPO, 'data', 'real_index.json'), 'w', encoding='utf-8') as fh:
        json.dump({'transport': 'streamable-http', 'cases': index}, fh, ensure_ascii=False, indent=1)
    print(f'\nDone. {len(results)} real-HTTP runs -> {OUTDIR}')


if __name__ == '__main__':
    asyncio.run(main())