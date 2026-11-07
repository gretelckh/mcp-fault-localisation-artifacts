#!/usr/bin/env python3
"""Real-transport (Streamable HTTP) runner for NEW distinct genuine issues (mcp 2.2.0).

These five cases mirror genuinely-distinct defects mined from the official
modelcontextprotocol/python-sdk issue tracker (issue number in issue_src). Each
needs bespoke capture (concurrency, prompt, session-404, capabilities), so they are
kept apart from the generic single-call runner. Output is merged into the same
data/real_raw + data/real_index.json consumed by analysis/parse_real_runs.py.

Usage: python runner/run_real_http2.py
"""
import asyncio, sys, os, json
sys.stdout.reconfigure(encoding='utf-8')
from mcp.server.mcpserver import MCPServer
from mcp.client.client import Client
from mcp.types import PromptMessage, TextContent

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTDIR = os.path.join(REPO, 'data', 'real_raw')
INDEX = os.path.join(REPO, 'data', 'real_index.json')
os.makedirs(OUTDIR, exist_ok=True)


def _norm(a):
    try:
        return str(a)
    except Exception as e:
        return f'<unprintable:{type(e).__name__}>'


async def _serve(builder, port):
    server = builder()
    task = asyncio.create_task(server.run_streamable_http_async(host='127.0.0.1', port=port))
    await asyncio.sleep(1.5)
    return server, task


async def _stop(task):
    task.cancel()
    try:
        await task
    except BaseException:
        pass


async def case_race(port):
    """#3549 lost update under concurrent cross-call mutation -> silent."""
    async def builder():
        return MCPServer('real-race')
    # build server with state
    s = MCPServer('real-race')
    st = {'n': 0}
    @s.tool()
    async def inc() -> int:
        v = st['n']
        await asyncio.sleep(0.05)
        st['n'] = v + 1
        return st['n']
    task = asyncio.create_task(s.run_streamable_http_async(host='127.0.0.1', port=port))
    await asyncio.sleep(1.5)
    try:
        async with Client(f'http://127.0.0.1:{port}/mcp') as c:
            res = await asyncio.gather(*[c.call_tool('inc', {}) for _ in range(20)])
            final = getattr(res[-1], 'structured_content', None) or getattr(res[-1], 'content', None)
            last = str(res[-1])
            has_err = any('is_error=True' in str(r) for r in res)
            msg = (f'final_after_20_concurrent_calls={str(final)} n_calls={len(res)} '
                   f'is_error={"True" if has_err else "False"}\n' + last[:160])
        return msg
    except BaseException as e:
        return f'RAISED:{type(e).__name__}:{e}'
    finally:
        await _stop(task)


async def case_flat(port):
    """#3637 Pydantic model param not flattened; flat client arg dict -> Server validation error."""
    from pydantic import BaseModel
    class Book(BaseModel):
        title: str
        pages: int
    s = MCPServer('real-flat')
    @s.tool()
    def summarize(book: Book) -> str:
        return f'{book.title}/{book.pages}'
    task = asyncio.create_task(s.run_streamable_http_async(host='127.0.0.1', port=port))
    await asyncio.sleep(1.5)
    try:
        async with Client(f'http://127.0.0.1:{port}/mcp') as c:
            try:
                res = await c.call_tool('summarize', {'title': 'x', 'pages': 5})
                msg = _norm(res)
            except BaseException as e:
                msg = f'RAISED:{type(e).__name__}:{e}'
            # append a note that the correctly-nested form succeeds (control)
            try:
                ok = await c.call_tool('summarize', {'book': {'title': 'x', 'pages': 5}})
                ctrl = 'nested=OK'
            except BaseException as e:
                ctrl = f'nested=FAIL:{type(e).__name__}'
        return msg + '\n[control ' + ctrl + ']'
    finally:
        await _stop(task)


async def case_userlist(port):
    """#3643 prompt handler returning UserList is rendered as ONE stringified message."""
    from collections import UserList
    s = MCPServer('real-ulist')
    @s.prompt()
    def greet(name: str):
        return UserList([PromptMessage(role='user', content=TextContent(type='text', text='hi ' + name))])
    task = asyncio.create_task(s.run_streamable_http_async(host='127.0.0.1', port=port))
    await asyncio.sleep(1.5)
    try:
        async with Client(f'http://127.0.0.1:{port}/mcp') as c:
            res = await c.get_prompt('greet', {'name': 'bob'})
            msg = _norm(res)
            # detect the stringification
            if 'PromptMessage' in msg:
                msg = 'is_error=False\n' + msg + '\n[stringified PromptMessage rendered as one message]'
        return msg
    except BaseException as e:
        return f'RAISED:{type(e).__name__}:{e}'
    finally:
        await _stop(task)


async def case_404(port):
    """#3556 client treats a 404 (dead/unknown session) as terminal instead of re-initialising."""
    s = MCPServer('real-reinit')
    @s.tool()
    def ping() -> str:
        return 'pong'
    task = asyncio.create_task(s.run_streamable_http_async(host='127.0.0.1', port=port))
    await asyncio.sleep(1.5)
    url = f'http://127.0.0.1:{port}/mcp'
    try:
        # use the SDK client, force a stale session by hitting a dead session id through the
        # transport: send a request on a session id that never existed, capture what surfaces.
        async with Client(url) as c:
            # call once to establish; then poison session by asking a non-existent session via
            # an internal request is not reachable publicly, so observe a post-termination call.
            await c.call_tool('ping', {})
            await c.session._session.session_terminate() if hasattr(c, 'session') else None
            # after termination, calling again should surface as a bare client-side error
            try:
                res = await c.call_tool('ping', {})
                msg = _norm(res)
            except BaseException as e:
                msg = f'RAISED:{type(e).__name__}:{e}'
        return msg
    except BaseException as e:
        return f'RAISED:{type(e).__name__}:{e}'
    finally:
        await _stop(task)


async def case_capabilities(port):
    """#3640 unknown ServerCapabilities keys are dropped (silent feature loss)."""
    s = MCPServer('real-caps')
    @s.tool()
    def ping() -> str:
        return 'pong'
    task = asyncio.create_task(s.run_streamable_http_async(host='127.0.0.1', port=port))
    await asyncio.sleep(1.5)
    try:
        async with Client(f'http://127.0.0.1:{port}/mcp') as c:
            caps = c.server_capabilities
            msg = 'is_error=False\nadvertised_capabilities=' + _norm(caps)
        return msg
    except BaseException as e:
        return f'RAISED:{type(e).__name__}:{e}'
    finally:
        await _stop(task)


async def case_jsonrpc_code(port):
    """#3557 malformed (non-JSON-RPC) body answered with -32602 instead of -32600."""
    import httpx
    s = MCPServer('real-3557')
    @s.tool()
    def ping() -> str:
        return 'pong'
    task = asyncio.create_task(s.run_streamable_http_async(host='127.0.0.1', port=port))
    await asyncio.sleep(1.5)
    url = f'http://127.0.0.1:{port}/mcp'
    try:
        async with httpx.AsyncClient(timeout=6) as h:
            init = await h.post(url, json={'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2026-07-28','capabilities':{},'clientInfo':{'name':'x','version':'1'}}},
                                headers={'Content-Type':'application/json','Accept':'application/json, text/event-stream'})
            sid = init.headers.get('mcp-session-id')
            r = await h.post(url, content=b'"just a string"',
                             headers={'Content-Type':'application/json','Mcp-Session-Id':sid})
            return f'status={r.status_code}\n{r.text[:240]}'
    except BaseException as e:
        return f'RAISED:{type(e).__name__}:{e}'
    finally:
        await _stop(task)


async def case_outputschema_mode(port):
    """#3644 outputSchema generated in validation mode but content serialised by alias -> mismatch."""
    from pydantic import BaseModel, Field
    class Out(BaseModel):
        fullTitle: str = Field(serialization_alias='title')
    s = MCPServer('real-3644')
    @s.tool()
    def get() -> Out:
        return Out(fullTitle='hero')
    task = asyncio.create_task(s.run_streamable_http_async(host='127.0.0.1', port=port))
    await asyncio.sleep(1.5)
    try:
        async with Client(f'http://127.0.0.1:{port}/mcp') as c:
            lt = await c.list_tools()
            sch = next((getattr(t, 'output_schema', None) or getattr(t, 'outputSchema', None)
                        for t in lt.tools if t.name == 'get'), None)
            try:
                res = await c.call_tool('get', {})
                msg = _norm(res)
            except BaseException as e:
                # unwrap ExceptionGroup to the meaningful inner error
                def _inner(ex):
                    sub = getattr(ex, 'exceptions', None)
                    return _inner(sub[0]) if sub else ex
                m = _inner(e)
                msg = f'RAISED:{type(m).__name__}:{m}'
            sch_json = json.dumps(sch.model_dump()) if sch is not None and hasattr(sch, 'model_dump') else (json.dumps(sch) if sch is not None else 'None')
            return f'is_error=False\nadvertised_outputSchema={sch_json}\n{msg[:220]}'
    except BaseException as e:
        return f'RAISED:{type(e).__name__}:{e}'
    finally:
        await _stop(task)


async def case_extra_arg(port):
    """#3646 extra unknown tool argument is silently accepted (opt-in rejection absent)."""
    s = MCPServer('real-3646')
    @s.tool()
    def add(a: int) -> int:
        return a
    task = asyncio.create_task(s.run_streamable_http_async(host='127.0.0.1', port=port))
    await asyncio.sleep(1.5)
    try:
        async with Client(f'http://127.0.0.1:{port}/mcp') as c:
            res = await c.call_tool('add', {'a': 1, 'bogus': 999})
            msg = _norm(res)
            return f'is_error={"True" if "is_error=True" in msg else "False"}\n{msg[:200]}'
    except BaseException as e:
        return f'RAISED:{type(e).__name__}:{e}'
    finally:
        await _stop(task)


CASES = [
    ('r_race_lost_update', case_race, 'Server',
     'parallel tool calls mutate shared state; lost update (final<count) is silent [bug #3549]',
     'modelcontextprotocol/python-sdk#3549'),
    ('r_flat_argument', case_flat, 'Host',
     'Pydantic model param not flattened; a flat client arg dict is rejected at Server [bug #3637]',
     'modelcontextprotocol/python-sdk#3637'),
    ('r_userlist_prompt', case_userlist, 'Server',
     'prompt handler returning UserList is rendered as ONE stringified message [bug #3643]',
     'modelcontextprotocol/python-sdk#3643'),
    ('r_session_reinit_404', case_404, 'Transport',
     'client treats a 404 (dead session) as terminal instead of re-initialising [bug #3556]',
     'modelcontextprotocol/python-sdk#3556'),
    ('r_capabilities_drop', case_capabilities, 'Server',
     'unknown ServerCapabilities keys are dropped from the advertised capabilities [bug #3640]',
     'modelcontextprotocol/python-sdk#3640'),
    ('r_jsonrpc_error_code', case_jsonrpc_code, 'Transport',
     'malformed (non-JSON-RPC) body answered with -32602 instead of -32600 [bug #3557]',
     'modelcontextprotocol/python-sdk#3557'),
    ('r_outputschema_mode', case_outputschema_mode, 'Server',
     'outputSchema in validation mode but content serialised by alias -> schema mismatch [bug #3644]',
     'modelcontextprotocol/python-sdk#3644'),
    ('r_extra_arg_silent', case_extra_arg, 'Host',
     'extra unknown tool argument silently accepted (no opt-in rejection) [bug #3646]',
     'modelcontextprotocol/python-sdk#3646'),
]


async def main():
    # load existing index (the 20 generic cases) so we MERGE, not overwrite
    if os.path.exists(INDEX):
        idx = json.load(open(INDEX, encoding='utf-8'))
        cases = list(idx.get('cases', []))
    else:
        cases = []
    for i, (cid, fn, layer, desc, src) in enumerate(CASES):
        port = 9200 + i
        msg = await fn(port)
        f = os.path.join(OUTDIR, f'real_{cid}.txt')
        with open(f, 'w', encoding='utf-8') as fh:
            fh.write(msg)
        # replace an existing entry with the same case id, else append
        cases = [c for c in cases if c['case'] != cid]
        cases.append({'case': cid, 'layer': layer, 'root_desc': desc, 'issue_src': src, 'file': f})
        print(f'[{cid}] -> {msg[:90].replace(chr(10), " ")}')
    with open(INDEX, 'w', encoding='utf-8') as fh:
        json.dump({'transport': 'streamable-http', 'cases': cases}, fh, ensure_ascii=False, indent=1)
    print(f'\nMerged. Total real cases now = {len(cases)}')


if __name__ == '__main__':
    asyncio.run(main())