#!/usr/bin/env python3
"""Generic reproduction engine for the 398 confirmed bugs (Step 3).

Each bug is reproduced as a real streamable-HTTP run: start an MCPServer over uvicorn,
connect with the official `Client`, trigger the fault, capture the REAL return object
(or the raised exception) as text. The captured text is then classified by
analysis/parse_real_runs.exposure_channel into the three-channel exposure model.

A bug is defined in runner/repro_cases.py by:
    Case(issue, origin, tool_call, args, builder=<fn returning an MCPServer>, desc)

Progress is persisted in data/repro_progress.json so a session can be resumed after a
crash / token-limit stop. Status per bug:
    pending   - not yet attempted
    running   - in progress
    done      - reproduced (raw text captured, channel classified)
    limited   - repro-limited (reason recorded; NOT fabricated)

Usage:
    python runner/repro_all.py --batch 1           # run batch 1
    python runner/repro_all.py --batch all         # run all pending batches
    python runner/repro_all.py --only 342,810      # run specific issues
"""
import asyncio, sys, os, json, argparse
sys.stdout.reconfigure(encoding='utf-8')
from mcp.server.mcpserver import MCPServer
from mcp import Client
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client
import httpx

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTDIR = os.path.join(REPO, 'data', 'real_raw')
PROGRESS = os.path.join(REPO, 'data', 'repro_progress.json')
PORT_BASE = 9100


def norm(res):
    try:
        return str(res)
    except Exception as e:
        return f'<unprintable:{type(e).__name__}>'


def exc(e):
    """Recursively unwrap an ExceptionGroup to the innermost real exception."""
    subs = getattr(e, 'exceptions', None)
    if subs:
        return exc(subs[0])
    return e


async def run_case(case, port, client_timeout=0.0):
    """Run one Case; return a result dict with the captured message.

    The Case may specify a trigger method (how the fault is exercised) so that
    tool / prompt / resource / list / subscribe / init / reconnect faults are all
    reproducible, not just tool calls.
    """
    builder, method, target, args, origin = (case.builder, case.method, case.target,
                                             case.args, case.origin)
    if builder is None:
        # transport-level fault: point the client at a closed port (connection refused)
        url = f'http://127.0.0.1:{port}/mcp'
        try:
            client = Client(url, mode='auto',
                            read_timeout_seconds=(client_timeout if client_timeout > 0 else None))
            await client.__aenter__()
            try:
                res = await _invoke(client, method, target, args or {})
                msg = norm(res)
            except BaseException as e:
                m = exc(e)
                msg = f'RAISED:{type(m).__name__}:{m}'
            finally:
                try:
                    await client.__aexit__(None, None, None)
                except BaseException:
                    pass
            return {'message': msg, 'via': 'streamable-http/conn-refused'}
        except BaseException as e:
            m = exc(e)
            return {'message': f'RAISED:{type(m).__name__}:{m}', 'via': 'streamable-http/conn-refused'}
    if method == 'raw_post':
        # protocol-level fault: POST a raw JSON-RPC body to the /mcp endpoint (with optional
        # extra headers) and capture the server's response / HTTP status. args = {'body': ..., 'headers': {...}}.
        # If the body is NOT an 'initialize' request, a session is first established
        # (initialize + notifications/initialized) so the target request is evaluated with a valid session.
        url = f'http://127.0.0.1:{port}/mcp'
        try:
            server = builder()
        except BaseException as e:
            m = exc(e)
            return {'message': f'RAISED-AT-REG:{type(m).__name__}:{m}', 'via': 'streamable-http/registration'}
        srv_task = asyncio.create_task(server.run_streamable_http_async(host='127.0.0.1', port=port))
        await asyncio.sleep(1.5)
        try:
            async with httpx.AsyncClient(timeout=15) as c:
                body = args.get('body', {})
                hdrs = {'Accept': 'application/json, text/event-stream', 'Content-Type': 'application/json'}
                hdrs.update(args.get('headers', {}) or {})
                sid = None
                if body.get('method') != 'initialize':
                    init = {"jsonrpc": "2.0", "id": 1, "method": "initialize",
                            "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                                       "clientInfo": {"name": "probe", "version": "1.0"}}}
                    r0 = await c.post(url, json=init, headers=hdrs)
                    sid = r0.headers.get('mcp-session-id')
                    if sid:
                        await c.post(url, json={"jsonrpc": "2.0", "method": "notifications/initialized"},
                                     headers={**hdrs, 'Mcp-Session-Id': sid})
                if sid:
                    hdrs = {**hdrs, 'Mcp-Session-Id': sid}
                if 'content_type' in args:
                    hdrs['Content-Type'] = args['content_type']
                if 'raw_body' in args:
                    r = await c.post(url, content=args['raw_body'], headers=hdrs)
                else:
                    r = await c.post(url, json=body, headers=hdrs)
                return {'message': f'HTTP {r.status_code}\n{r.text[:500]}', 'via': 'streamable-http/raw-post',
                        'status': r.status_code, 'session_id': sid}
        finally:
            srv_task.cancel()
            try:
                await srv_task
            except BaseException:
                pass
    if case.transport == 'sse':
        # SSE-transport fault: start an SSE server, connect via mcp.client.sse.sse_client,
        # hand the streams to a ClientSession, and invoke. Supports disconnect / concurrency.
        try:
            server = builder()
        except BaseException as e:
            m = exc(e)
            return {'message': f'RAISED-AT-REG:{type(m).__name__}:{m}', 'via': 'sse/registration'}
        srv_task = asyncio.create_task(server.run_sse_async(host='127.0.0.1', port=port))
        await asyncio.sleep(1.5)
        url = f'http://127.0.0.1:{port}/sse'
        try:
            msg = await _run_sse(case, url)
            return {'message': msg, 'via': 'sse'}
        finally:
            srv_task.cancel()
            try:
                await srv_task
            except (asyncio.CancelledError, Exception):
                pass
    try:
        server = builder()
    except BaseException as e:
        m = exc(e)
        return {'message': f'RAISED-AT-REG:{type(m).__name__}:{m}', 'via': 'streamable-http/registration'}
    url = f'http://127.0.0.1:{port}/mcp'
    srv_task = asyncio.create_task(server.run_streamable_http_async(host='127.0.0.1', port=port))
    await asyncio.sleep(1.5)
    try:
        client = Client(url, mode='auto',
                        read_timeout_seconds=(client_timeout if client_timeout > 0 else None))
        await client.__aenter__()
        try:
            # capture the invocation result BEFORE the client context exits, so teardown
            # noise (e.g. server-cancel ExceptionGroup) is never mistaken for the fault.
            if getattr(case, 'concurrency', 0) and case.concurrency > 1:
                res = await asyncio.gather(
                    *[_invoke(client, method, target, args or {}) for _ in range(case.concurrency)],
                    return_exceptions=True)
                msg = repr(res)
            else:
                res = await _invoke(client, method, target, args or {})
                msg = norm(res)
        except BaseException as e:
            m = exc(e)
            msg = f'RAISED:{type(m).__name__}:{m}'
        finally:
            try:
                await client.__aexit__(None, None, None)
            except BaseException:
                pass
        return {'message': msg, 'via': 'streamable-http'}
    finally:
        srv_task.cancel()
        try:
            await srv_task
        except (asyncio.CancelledError, Exception):
            pass


async def _run_sse(case, url):
    """Run a Case over the SSE transport. Supports disconnect / concurrency / reconnect.

    - concurrency>0 : fire N simultaneous _invoke calls (for race / cross-wire bugs)
    - disconnect='after_connect' : establish session then close the SSE client before invoking
    - reconnect=True             : after the first connection, open a fresh second connection
    """
    method, target, args = case.method, case.target, case.args or {}
    if case.disconnect == 'after_connect':
        # establish a real SSE session, then close it immediately (honest observation: we
        # record that the connection was established and dropped without a genuine defect).
        try:
            async with sse_client(url) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                # session closed -> SSE dropped after handshake
            return 'sse-connect-dropped-after-handshake (no defect observed; disconnect-hang is observation-type)'
        except BaseException as e:
            m = exc(e)
            return f'RAISED:{type(m).__name__}:{m}'
    try:
        async with sse_client(url) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                if case.concurrency and case.concurrency > 1:
                    res = await asyncio.gather(
                        *[_invoke(session, method, target, args) for _ in range(case.concurrency)],
                        return_exceptions=True)
                    return repr(res)
                res = await _invoke(session, method, target, args)
                return norm(res)
    except BaseException as e:
        m = exc(e)
        return f'RAISED:{type(m).__name__}:{m}'


async def _invoke(client, method, target, args):
    """Dispatch a trigger operation on the client. method -> client API (mcp 2.2.0)."""
    if method == 'call_tool':
        return await client.call_tool(target, args)
    if method == 'list_tools':
        return await client.list_tools()
    if method == 'list_prompts':
        return await client.list_prompts()
    if method == 'list_resources':
        return await client.list_resources()
    if method == 'list_resource_templates':
        return await client.list_resource_templates()
    if method == 'get_prompt':
        return await client.get_prompt(target, arguments=args)
    if method == 'read_resource':
        return await client.read_resource(target)
    if method == 'subscribe_resource':
        return await client.subscribe_resource(target)
    if method == 'unsubscribe_resource':
        return await client.unsubscribe_resource(target)
    if method == 'send_ping':
        return await client.send_ping()
    if method == 'complete':
        return await client.complete(target, args)
    if method == 'set_logging_level':
        return await client.set_logging_level(target)
    # default: try a tool call
    return await client.call_tool(target, args)


def load_progress():
    if os.path.exists(PROGRESS):
        return json.load(open(PROGRESS, encoding='utf-8'))
    return {}


def save_progress(p):
    json.dump(p, open(PROGRESS, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--batch', help='batch label to run (defined in repro_cases.BATCHES)')
    ap.add_argument('--only', help='comma-separated issue numbers')
    ap.add_argument('--all', action='store_true', help='run all defined cases not yet done/limited')
    args = ap.parse_args()

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import repro_cases as rc

    progress = load_progress()
    os.makedirs(OUTDIR, exist_ok=True)

    if args.only:
        nums = [int(x) for x in args.only.split(',')]
        todo = [(n, rc.CASES[n]) for n in nums if n in rc.CASES]
    elif args.all:
        todo = [(n, c) for n, c in rc.CASES.items()
                if progress.get(str(n), {}).get('status') not in ('done', 'limited')]
    else:
        todo = []
        for n in rc.BATCHES.get(args.batch, []):
            if n in rc.CASES and progress.get(str(n), {}).get('status') not in ('done', 'limited'):
                todo.append((n, rc.CASES[n]))

    print(f'Batch to run: {len(todo)} cases')
    for i, (n, case) in enumerate(todo):
        progress[str(n)] = {'status': 'running', 'issue': n, 'origin': case.origin,
                            'title': case.title, 'desc': case.desc, 'updated': None}
        save_progress(progress)
        port = PORT_BASE + i
        ct = getattr(case, 'client_timeout', 0.0)
        try:
            r = asyncio.run(run_case(case, port, ct))
            f = os.path.join(OUTDIR, f'real_{n}.txt')
            with open(f, 'w', encoding='utf-8') as fh:
                fh.write(r['message'])
            msg = r['message']
            # determine whether a genuine defect was captured, vs a clean success
            lowered = msg.lower()
            # 'Method not found' from a generic send_ping is a transport artifact, NOT the
            # specific bug's defect, so it is NOT counted as a reproduction.
            if 'method not found' in lowered:
                defect = False
            else:
                defect = any(k in lowered for k in [
                    'error executing', 'unknown tool', 'iserror=True', 'is_error=true',
                    'validation error', 'field required', 'input should be',
                    'notimplementederror', 'runtimeerror', 'valueerror', 'typeerror',
                    'attributeerror', 'connectionerror', 'timeouterror', 'exceptiongroup',
                    'raised:', 'unexpectedtoolerror', 'mcp error', '500', '404', '401',
                    '403', '405', 'bad request', 'disconnected', 'not allowed'])
            progress[str(n)]['status'] = 'done' if defect else 'limited'
            progress[str(n)]['file'] = f
            progress[str(n)]['message'] = msg[:300]
            progress[str(n)]['via'] = r['via']
            progress[str(n)]['defect_captured'] = bool(defect)
            if not defect:
                progress[str(n)]['reason'] = ('no defect captured by this trigger '
                                              '(clean success); scenario not exercised')
            print(f'  [#{n}] {"DONE(defect)" if defect else "LIMITED(clean)"} -> {msg[:70]}')
        except BaseException as e:
            progress[str(n)]['status'] = 'limited'
            progress[str(n)]['reason'] = f'runner error: {type(e).__name__}: {e}'
            print(f'  [#{n}] LIMITED -> {type(e).__name__}: {e}')
        save_progress(progress)

    done = sum(1 for v in progress.values() if v['status'] == 'done')
    limited = sum(1 for v in progress.values() if v['status'] == 'limited')
    print(f'\nProgress so far: {done} done, {limited} limited, {len(progress)} tracked')


if __name__ == '__main__':
    main()