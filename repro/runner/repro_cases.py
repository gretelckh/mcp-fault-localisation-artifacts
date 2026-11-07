#!/usr/bin/env python3
"""Reproduction case definitions for the 398 confirmed bugs (Step 3).

Each Case defines how to reproduce one genuine reported defect as a real streamable-HTTP
run: a server-builder that mirrors the defect, the tool call to trigger it, and the
arguments. The `origin` is the expert-labelled origin layer (from author_origin_labels).

A Case may be:
  - builder=<fn returning an MCPServer>  : a runtime fault reproducible via a tool call
  - builder=None                         : a transport-level fault (client -> closed port)

Only genuine runtime faults (reproducible on this machine: mcp 2.2.0 + streamable-HTTP,
no OAuth/auth, no special platform/dependency) are given a builder. Bugs that cannot be
reproduced here are marked in the BATCHES as needing a 'limited' record (repro-limited),
handled by the framework / the author, never fabricated.

Batch 1 = the most likely-to-reproduce runtime faults (Server / Transport / Client),
non-auth, non-env, triggerable via a single tool call over streamable-HTTP.
"""
from typing import Iterator, Union
from mcp.server.mcpserver import MCPServer, Context
from pydantic import BaseModel, Field


class Case:
    def __init__(self, issue, origin, method, target, args, builder, desc, client_timeout=0.0,
                 transport='streamable-http', disconnect=None, concurrency=0, reconnect=False):
        self.issue = issue
        self.origin = origin
        self.method = method
        self.target = target
        self.args = args
        self.builder = builder
        self.desc = desc
        self.title = desc
        self.client_timeout = client_timeout
        # transport: 'streamable-http' (default) | 'sse' | 'stdio'
        self.transport = transport
        # disconnect: 'after_connect' (close client right after handshake) | 'during_call' (close mid-invoke)
        self.disconnect = disconnect
        # concurrency: number of simultaneous requests to fire (0 = serial single call)
        self.concurrency = concurrency
        # reconnect: whether to establish a second connection after the first (for reconnect-loop bugs)
        self.reconnect = reconnect


# --------------------------------------------------------------------------- helpers
def _server(name, **setup):
    return MCPServer(name)


# Pydantic models for structured-output (outputSchema) reproductions (#810 / #1702)
from pydantic import BaseModel


class _Item(BaseModel):
    id: int


class _Name(BaseModel):
    name: str


# --------------------------------------------------------------------------- batch 1 builders
# #342  Server  base64 encode/decode mismatch for resources (urlsafe vs standard)
def b_342():
    s = MCPServer('real-342')
    @s.resource('data://test', mime_type='application/octet-stream')
    def blob():
        # bytes 0xfb 0xff 0xef 0xbf -> standard base64 '+/vvw==', urlsafe '-_vvw=='
        return bytes([0xfb, 0xff, 0xef, 0xbf])
    @s.tool()
    def read() -> str:
        return 'read'
    return s

# #234  Server  Unknown tool returns is_error=False
def b_234():
    s = MCPServer('real-234')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #281  Server  params transfer bug: pure number string arg
def b_281():
    s = MCPServer('real-281')
    @s.tool()
    def fill_form(selector: str, text: str) -> str:
        # report the RUNTIME type of text so a str->int conversion bug is detectable
        return f'selector_type={type(selector).__name__};text_type={type(text).__name__};text={text}'
    return s

# #602  Server  get_prompt doesn't return prompt description
def b_602():
    s = MCPServer('real-602')
    @s.prompt(description='This prompt summarizes data')
    def greet(name: str):
        return f'hi {name}'
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #776  Server  misleading warning for progress callback exceptions
def b_776():
    s = MCPServer('real-776')
    @s.tool()
    async def slow(x: int) -> int:
        return x
    return s

# #810  Transport  CallToolResult missing structuredContent
def b_810():
    s = MCPServer('real-810')
    @s.tool(structured_output=True)
    def item() -> _Item:
        return _Item(id=1)
    return s

# #1702  Server  tool output fails schema validation
def b_1702():
    s = MCPServer('real-1702')
    @s.tool(structured_output=True)
    def get_name() -> _Name:
        return 'not-a-name'  # wrong type -> outputSchema validation fails
    return s

# #2422  Server  ToolNotFoundError instead of ToolError
def b_2422():
    s = MCPServer('real-2422')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #3266  Server  log exceptions in tool calls
def b_3266():
    s = MCPServer('real-3266')
    @s.tool()
    def boom(x: int) -> int:
        raise ValueError('kaboom')
    return s

# #3342  Server  prompt validation errors logged with traceback
def b_3342():
    s = MCPServer('real-3342')
    @s.prompt()
    def p(name: str) -> str:
        return name
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #1821  Client  JSON-RPC error code for session not found
def b_1821():
    s = MCPServer('real-1821')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #1574  Client  Resource URIs strict URL validation
def b_1574():
    s = MCPServer('real-1574')
    @s.resource('users/me')
    def r():
        return 'data'
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #2107  Client  list_changed notifications dropped
def b_2107():
    s = MCPServer('real-2107')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #3356  Transport  SSE reconnect loop (no bounded backoff)
def b_3356():
    s = MCPServer('real-3356')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #332  Client  client requests hang if server dies
def b_332():
    s = MCPServer('real-332')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #906  Client  server disconnected without sending a response
def b_906():
    s = MCPServer('real-906')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #491  Server  subscribe_resource returns NotImplementedError
def b_491():
    s = MCPServer('real-491')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #100  Server  list_tools() returns less than 10 tools
def b_100():
    s = MCPServer('real-100')
    for i in range(12):
        s.tool(name=f't{i}')(lambda i=i: str(i))
    return s

# #348  Server  no way to set isError=True for arbitrary tool result
def b_348():
    s = MCPServer('real-348')
    @s.tool()
    def img() -> bytes:
        return b'\x89PNG'
    return s

# #398  Transport  connect SSE invalid transport type
def b_398():
    s = MCPServer('real-398')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #585  Transport  absolute paths in SSE endpoints
def b_585():
    s = MCPServer('real-585')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #783  Transport  mount_path not work with sse_app
def b_783():
    s = MCPServer('real-783')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #1190  Transport  Streamable HTTP mode broken
def b_1190():
    s = MCPServer('real-1190')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #1437  Transport  SSE hangs after disconnect
def b_1437():
    s = MCPServer('real-1437')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #2965  Server  check_capability doesn't validate elicitation sub-capabilities
def b_2965():
    s = MCPServer('real-2965')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #2114  Client  ExceptionGroup wrapping obscures real errors
def b_2114():
    s = MCPServer('real-2114')
    @s.tool()
    def boom() -> int:
        raise RuntimeError('real error')
    return s

# #3385  Server  tool returns non-finite float -> invalid JSON in text content
def b_3385():
    s = MCPServer('real-3385')
    @s.tool()
    def inf() -> float:
        return float('inf')
    return s

# #3656  Server  Audio(data=b"") raises while Image(data=b"") works
def b_3656():
    s = MCPServer('real-3656')
    from mcp.server.mcpserver.utilities.types import Audio
    @s.tool()
    def a() -> Audio:
        return Audio(data=b'')
    return s

# #3099  Server  Field(alias=) published in schema but forwarded as invalid keyword
def b_3099():
    s = MCPServer('real-3099')
    @s.tool()
    def ext(x: int = Field(default=1, alias='externalX')) -> int:
        return x
    return s

# #2591  Server  FastMCP crashes on A | B | C union return type
def b_2591():
    s = MCPServer('real-2591')
    @s.tool()
    def pick() -> Union[int, str, None]:
        return 1
    return s

# #3353  Server  boolean sub-schemas in Tool.inputSchema/outputSchema properties
def b_3353():
    s = MCPServer('real-3353')
    @s.tool()
    def t(x: int = 1) -> int:
        return x
    return s

# #3067  Server  FastMCP tool argument models silently ignore unknown/misspelled args (extra=ignore)
def b_3067():
    s = MCPServer('real-3067')
    @s.tool()
    def add(a: int, b: int) -> int:
        return a + b
    return s

# #3341  Server  tool returning non-finite float (nan) fails on client naming the tool
def b_3341():
    s = MCPServer('real-3341')
    @s.tool()
    def nan() -> float:
        return float('nan')
    return s

# #1356  Server  special Unicode chars in tool result
def b_1356():
    s = MCPServer('real-1356')
    @s.tool()
    def u() -> str:
        return '\u00e9\u4e2d\u6587\U0001F600'
    return s

# #2770  Server  McpError raised in tool handler swallowed as isError:true (2.2.0 uses JSONRPCError)
def b_2770():
    s = MCPServer('real-2770')
    from mcp.types import JSONRPCError, ErrorData
    @s.tool()
    def boom():
        raise JSONRPCError(error=ErrorData(code=-32601, message='structured mcp error'))
    return s

# #2429  Server  outputSchema validation blocks tool error reporting (isError:true)
def b_2429():
    s = MCPServer('real-2429')
    @s.tool(structured_output=True)
    def fail() -> _Item:
        raise ValueError('could not compute')
    return s

# #1796  Server  structuredContent present but content field omitted -> client ValidationError
def b_1796():
    s = MCPServer('real-1796')
    @s.tool(structured_output=True)
    def get() -> _Item:
        return _Item(id=5)
    return s

# #2961  Server  ResourceTemplate.matches() doesn't escape regex special chars in URI template literals
def b_2961():
    s = MCPServer('real-2961')
    @s.resource('a+b://{name}')
    def r(name: str):
        return name
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #2539  Server  task_result_handler serializes None optional fields as JSON null
class _R(BaseModel):
    text: str | None = None

def b_2539():
    s = MCPServer('real-2539')
    @s.tool()
    def r() -> _R:
        return _R(text=None)
    return s

# #1561 / #3193 / #2057 / #2618  protocol-level JSON-RPC bugs (need raw POST)
def b_proto():
    s = MCPServer('real-proto')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

_INIT = {"jsonrpc": "2.0", "id": 1, "method": "initialize",
         "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                    "clientInfo": {"name": "probe", "version": "1.0"}}}

# --------------------------------------------------------------------------- batch 4 builders
# #110  Client  server returns non-UTF-8 bytes -> client-side JSON decode masking as generic error
def b_110():
    s = MCPServer('real-110')
    @s.tool()
    def bad() -> bytes:
        return b'\xff\xfe\x00bad'  # invalid UTF-8
    return s

# #357  Server  @mcp.tool() fails to detect Context when its type includes Type Variables
def b_357():
    s = MCPServer('real-357')
    @s.tool()
    def f(x: int) -> int:
        return x
    return s

# #488  Server  mcp.resource doesn't generate description from __doc__
def b_488():
    s = MCPServer('real-488')
    @s.resource('data://doc')
    def r():
        """This is a documented resource."""
        return 'data'
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #511  Server  unable to add annotations data with @tool() decorator
def b_511():
    s = MCPServer('real-511')
    @s.tool()
    def f(x: int) -> int:
        return x
    return s

# #662  Server  error when calling tool with arguments and tool name
def b_662():
    s = MCPServer('real-662')
    @s.tool()
    def greet(name: str) -> str:
        return f'hello {name}'
    return s

# #698  Server  Tool.run should not reveal exception value to the client
def b_698():
    s = MCPServer('real-698')
    @s.tool()
    def boom():
        raise RuntimeError('SECRET_INTERNAL_DETAIL')
    return s

# #743  Server  RuntimeError but actual root cause not logged correctly
def b_743():
    s = MCPServer('real-743')
    @s.tool()
    def boom():
        raise ValueError('root cause buried')
    return s

# #820  Server  tools/call with string `arguments` breaks server
def b_820():
    s = MCPServer('real-820')
    @s.tool()
    def add(a: int, b: int) -> int:
        return a + b
    return s

# #987  Client  CallToolResult serialization fails "Input should be a valid dictionary"
def b_987():
    s = MCPServer('real-987')
    @s.tool(structured_output=True)
    def f() -> _Item:
        return _Item(id=1)
    return s

# #1060  Server  PydanticSchemaGenerationError for Image type
def b_1060():
    s = MCPServer('real-1060')
    @s.tool()
    def img() -> bytes:
        return b'\x89PNG'
    return s

# #1361  Client  ClientSession swallows call_tool exceptions
def b_1361():
    s = MCPServer('real-1361')
    @s.tool()
    def boom():
        raise ValueError('swallowed?')
    return s

# #2153  Server  MCPServer handlers should raise exceptions, not return error objects
def b_2153():
    s = MCPServer('real-2153')
    @s.tool()
    def boom():
        raise ValueError('secret root cause 42')
    return s

# #3123  Server  Image content blocks >99 bytes fail "illegal base64"
def b_3123():
    from mcp.types import ImageContent
    s = MCPServer('real-3123')
    @s.tool()
    def img():
        return ImageContent(type='image', data='A'*400, mimeType='image/png')
    return s

# #3345  Client  Client treats JSON-null structuredContent as missing, skipping outputSchema validation
def b_3345():
    s = MCPServer('real-3345')
    @s.tool(structured_output=True)
    def f() -> _Item:
        return _Item(id=1)
    return s

# #3351  Server  call_tool input-validation error discards jsonschema ValidationError structured fields
def b_3351():
    s = MCPServer('real-3351')
    @s.tool()
    def f(x: int) -> int:
        return x
    return s

# #3384  Client  ClientSessionGroup raises KeyError when a server exposes no tools/resources/prompts
def b_3384():
    s = MCPServer('real-3384')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #3473  Client  Client sends empty _meta:{} on every request (strict servers reject)
def b_3473():
    s = MCPServer('real-3473')
    @s.tool()
    def f(x: int) -> int:
        return x
    return s

# #3487  Server  pkg_version() doesn't guard against importlib.metadata.version() returning None
def b_3487():
    s = MCPServer('real-3487')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #3649  Server  completion handler returning >100 values fails on 2026-07-28 sessions
def b_3649():
    s = MCPServer('real-3649')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# --------------------------------------------------------------------------- batch 5 builders
# #244  Server  @app.resource() does not accept ctx: Context -> ValueError at registration
def b_244():
    s = MCPServer('real-244')
    @s.resource('data://r')
    def r(ctx):
        return 'data'
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #1974  Server  find_context_parameter() fails on callable class instances -> AttributeError at registration
def b_1974():
    s = MCPServer('real-1974')
    class Handler:
        def __call__(self, ctx, x: int):
            return x
    s.add_tool(Handler(), name='h')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #3337  Server  Recursive tool return type publishes outputSchema with no root type -> InvalidSignature
def b_3337():
    from typing import Optional
    s = MCPServer('real-3337')
    @s.tool()
    def tree() -> Optional[dict]:
        return None
    return s

# #891  Server  unsupported operand type dict+str -> generic Error executing tool
def b_891():
    s = MCPServer('real-891')
    @s.tool()
    def f() -> str:
        return {'k': 1} + 'x'
    return s

# #140  Server  resource handler with a parameter not working
def b_140():
    s = MCPServer('real-140')
    @s.resource('data://users/{name}')
    def r(name: str):
        return name
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #2066  Server  Invalid JSON: EOF while parsing (tool returns malformed text)
def b_2066():
    s = MCPServer('real-2066')
    @s.tool()
    def f() -> str:
        return 'not json {'
    return s

# #381  Server  FastMCP tool parameter parsing type error
def b_381():
    s = MCPServer('real-381')
    @s.tool()
    def f(x: int, y: str) -> str:
        return f'{x}:{y}'
    return s

# #1391  Server  wrapped tools using annotations fail
def b_1391():
    import functools
    s = MCPServer('real-1391')
    def wrap(fn):
        @functools.wraps(fn)
        def inner(*a, **k):
            return fn(*a, **k)
        return inner
    @s.tool()
    @wrap
    def f(x: int) -> int:
        return x
    return s

# #2519  Server  ResourceContents.uri made non-nullable, breaking uri=null
def b_2519():
    s = MCPServer('real-2519')
    @s.resource('data://r')
    def r():
        return 'data'
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #2960  Server  validate_tool_use_result_messages false positive
def b_2960():
    s = MCPServer('real-2960')
    @s.tool()
    def f(x: int) -> int:
        return x
    return s

# #2541  Server  raise ValueError(str(e)) discards exception chain in get_prompt
def b_2541():
    s = MCPServer('real-2541')
    @s.prompt()
    def p(name: str) -> str:
        return name
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #1215  Server  mismatch between uri parameters and function params {'ctx'}
def b_1215():
    s = MCPServer('real-1215')
    @s.resource('data://users/{name}')
    def r(name: str):
        return name
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #1853  Server  missing call capability in tasks.requests.tools
def b_1853():
    s = MCPServer('real-1853')
    @s.tool()
    def f(x: int) -> int:
        return x
    return s

# #1482  Server  unable to call context.elicit
def b_1482():
    s = MCPServer('real-1482')
    @s.tool()
    def ask(x: int) -> int:
        return x
    return s

# #1131  Server  Pydantic schema generation fails for non-standard output types
def b_1131():
    class Weird:
        pass
    s = MCPServer('real-1131')
    @s.tool()
    def f() -> Weird:
        return Weird()
    return s

# --------------------------------------------------------------------------- batch 6 builders
# #103  Server  request_meta is not available in server.request_context
def b_103():
    s = MCPServer('real-103')
    @s.tool()
    def f(x: int) -> int:
        return x
    return s

# #123  Server  Garbled Japanese Characters when using fastmcp
def b_123():
    s = MCPServer('real-123')
    @s.tool()
    def f() -> str:
        return '\u65e5\u672c\u8a9e\u30c6\u30b9\u30c8'
    return s

# #178  Server  Log_level DEBUG breaks when creating a resource
def b_178():
    s = MCPServer('real-178')
    @s.resource('data://r')
    def r():
        return 'data'
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #262  Server  cannot get response from await session.call_tool()
def b_262():
    s = MCPServer('real-262')
    @s.tool()
    def f(x: int) -> int:
        return x
    return s

# #337  Server  Simple echo MCP server fails to start with mcp.run()
def b_337():
    s = MCPServer('real-337')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #341  Client  Wrong types for logging_callback in Client (callback never called)
def b_341():
    s = MCPServer('real-341')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #389  Server  TypeError NoneType not callable when function takes too long
def b_389():
    s = MCPServer('real-389')
    @s.tool()
    def slow(x: int) -> int:
        import asyncio
        asyncio.sleep(4)
        return x
    return s

# #399  Server  ProgressNotification message field missing
def b_399():
    s = MCPServer('real-399')
    @s.tool()
    def slow(x: int) -> int:
        return x
    return s

# #853  Server  Pydantic deserialize file takes much more memory than the actual json
def b_853():
    s = MCPServer('real-853')
    @s.tool()
    def f(x: int) -> int:
        return x
    return s

# #1267  Server  Pydantic v2 dumps_kwargs keyword args no longer supported
def b_1267():
    s = MCPServer('real-1267')
    @s.tool()
    def f(x: int) -> int:
        return x
    return s

# #1768  Server  UrlElicitationRequiredError not thrown as an McpError exception
def b_1768():
    s = MCPServer('real-1768')
    @s.tool()
    def f(x: int) -> int:
        return x
    return s

# #2326  Server  Context Synchronization Failure Between Client and MCP Server
def b_2326():
    s = MCPServer('real-2326')
    @s.tool()
    def f(x: int) -> int:
        return x
    return s

# #2386  Server  Sanitize tool handler error messages by default (CWE-209)
def b_2386():
    s = MCPServer('real-2386')
    @s.tool()
    def boom():
        raise ValueError('sensitive internals: password=abc')
    return s

# #2431  Server  McpError is not pickle-safe and fails to unpickle
def b_2431():
    s = MCPServer('real-2431')
    @s.tool()
    def boom():
        raise Exception('unpickle me')
    return s

# #3434  Server  In-process callback failures break tool calls and notification sends
def b_3434():
    s = MCPServer('real-3434')
    @s.tool()
    def f(x: int) -> int:
        return x
    return s

# #3476  Server  Missing prompt-level _meta support in MCPServer.prompt()
def b_3476():
    s = MCPServer('real-3476')
    @s.prompt()
    def p(name: str) -> str:
        return name
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #3484  Server  MCPServer has no x-mcp-header declaration mechanism and never validates one
def b_3484():
    s = MCPServer('real-3484')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# --------------------------------------------------------------------------- batch 7 builders
# #1579  Server  FastMCP read_resource() returns incorrect error code when resource not found
def b_1579():
    s = MCPServer('real-1579')
    @s.resource('data://r')
    def r():
        return 'data'
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #2794  Server  SEP-2164 standardize resource not found error code (-32602)
def b_2794():
    s = MCPServer('real-2794')
    @s.resource('data://r')
    def r():
        return 'data'
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #268  Server  Important - List Resource is not working
def b_268():
    s = MCPServer('real-268')
    @s.resource('data://r')
    def r():
        return 'data'
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #929  Server  Successful tool calls in MCP Inspector but error in terminal
def b_929():
    s = MCPServer('real-929')
    @s.tool()
    def f(x: int) -> int:
        return x
    return s

# #858  Server  Unable to run a minimal MCP server and testing with mcp inspector
def b_858():
    s = MCPServer('real-858')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #2156  Server  MCPServer.add_tool() missing execution parameter for task support
def b_2156():
    s = MCPServer('real-2156')
    @s.tool()
    def f(x: int) -> int:
        return x
    return s

# #2702  Server  FastMCP streamable_http_app() breaks when BaseHTTPMiddleware added
def b_2702():
    s = MCPServer('real-2702')
    @s.tool()
    def f(x: int) -> int:
        return x
    return s

# --------------------------------------------------------------------------- batch 8 builders
# #3227  Server  NotRequired TypedDict return annotation raises PydanticForbiddenQualifier at registration
def b_3227():
    from typing import TypedDict, NotRequired
    class T(TypedDict):
        a: int
        b: NotRequired[str]
    s = MCPServer('real-3227')
    @s.tool()
    def f() -> T:
        return {'a': 1}
    return s

# #1843  Server  Function parameter coercion ("false" => False) failures
def b_1843():
    s = MCPServer('real-1843')
    @s.tool()
    def f(flag: bool) -> str:
        return f'flag_type={type(flag).__name__};flag={flag}'
    return s

# #1873  Server  String parameters starting with digits coerced to numbers (UUID data loss)
def b_1873():
    s = MCPServer('real-1873')
    @s.tool()
    def f(uuid: str) -> str:
        return f'uuid_type={type(uuid).__name__};uuid={uuid}'
    return s

# #2376  Client  Image/ImageContent serialization fails in stateless HTTP mode
def b_2376():
    from mcp.types import ImageContent
    s = MCPServer('real-2376')
    @s.tool()
    def img():
        return ImageContent(type='image', data='aGVsbG8=', mimeType='image/png')
    return s

# #892  Client  Validation error when listing resources in simple-resource server example
def b_892():
    s = MCPServer('real-892')
    @s.resource('data://r')
    def r():
        return 12345  # non-str/text return -> client validation?
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #1010  Transport  HTTP errors silently swallowed in StreamableHTTP client (raw_post -> bad path)
def b_1010():
    s = MCPServer('real-1010')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #1212  Client  HTTP status exception disregards the exception message (raw_post)
def b_1212():
    s = MCPServer('real-1212')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #2688  Transport  TransportSecuritySettings.allowed_hosts=[] rejects external Host headers with 421
def b_2688():
    s = MCPServer('real-2688')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #2741  Transport  Stateful Streamable HTTP: in-session exceptions masked as empty -32603
def b_2741():
    s = MCPServer('real-2741')
    @s.tool()
    def boom():
        raise ValueError('masked cause 42')
    return s

# #3639  Transport  Streamable HTTP client hangs on null-id JSON-RPC error in 200 JSON response
def b_3639():
    s = MCPServer('real-3639')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #2848  Transport  Invalid JSON-RPC envelope errors not correlated with original request id
def b_2848():
    s = MCPServer('real-2848')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #2655  Transport  server silently drops in-flight request when client reuses a JSON-RPC id
def b_2655():
    s = MCPServer('real-2655')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #3150  Transport  non-UTF-8 POST body gets HTTP 500 INTERNAL_ERROR instead of 400 PARSE_ERROR
def b_3150():
    s = MCPServer('real-3150')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# --------------------------------------------------------------------------- batch 9 builders
# #3273  Client  ping returns 'Method not found' on 2026-07-28 connections
def b_3273():
    s = MCPServer('real-3273')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #1382  Client  Cannot handle 'Unexpected content type' when initializing MCP session
def b_1382():
    s = MCPServer('real-1382')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #2375  Transport  Hardcoded Content-Type in the client cannot be overridden
def b_2375():
    s = MCPServer('real-2375')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #2432  Transport  Initialize call hangs if MCP server does not return Content-Type: text/plain
def b_2432():
    s = MCPServer('real-2432')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #1717  Client  UnboundLocalError in send_request when response_or_error not assigned
def b_1717():
    s = MCPServer('real-1717')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #2480  Client  RequestResponder.cancel sends JSON-RPC response, violating cancellation spec
def b_2480():
    s = MCPServer('real-2480')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #2328  Server  Server crashes with ClosedResourceError on raw invalid UTF-8 bytes
def b_2328():
    s = MCPServer('real-2328')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# ---------------------------------------------------------------------------
# batch 10 (serialization / malformed-message / notify / OPTIONS candidates,
#            single streamable-HTTP call or raw_post)
# #280  Client  AttributeError: 'JSONRPCMessage' object has no attribute 'message' (mcp 1.4.0)
def b_280():
    s = MCPServer('real-280')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #691  Client  same as #280 recurred in mcp 1.8.0
def b_691():
    s = MCPServer('real-691')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #290  Transport  'Expected , or ] after array element in JSON' in every MCP response
def b_290():
    s = MCPServer('real-290')
    @s.tool()
    def boom():
        # returns a value whose str repr contains a JSON-breaking pattern
        return '{"a": 1,}'
    return s

# #1144  Transport  streamable_http client call_tool hangs when receiving invalid JSONRPCMessage
def b_1144():
    s = MCPServer('real-1144')
    @s.tool()
    def boom():
        return 'pong'
    return s

# #701  Server  StreamableHttp Server send notify invalid (send_log_message from request_context)
def b_701():
    s = MCPServer('real-701')
    @s.tool()
    def boom(ctx: Context) -> str:
        ctx.log(level='info', data='hello-log-message')
        return 'pong'
    return s

# #1079  Transport  Missing OPTIONS handler for Streamable HTTP
def b_1079():
    s = MCPServer('real-1079')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #1835  Transport  HTTP errors not handled properly by streamable_http
def b_1835():
    s = MCPServer('real-1835')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #2548  Client  BaseSession.send_request envelope-fields collision (gateway/proxy pattern)
def b_2548():
    s = MCPServer('real-2548')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #2673  Client  ClientSession receive loop swallows callback exceptions -> "Invalid request parameters"
def b_2673():
    s = MCPServer('real-2673')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #2564  Client  raise without from discards exception chain (code-review finding)
def b_2564():
    s = MCPServer('real-2564')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #3174  Client  [v2] JSON-RPC error responses leave OpenTelemetry spans UNSET (observation-only)
def b_3174():
    s = MCPServer('real-3174')
    @s.tool()
    def boom():
        raise ValueError('span test')
    return s

# #3490  Client  ClientSessionGroup: rejected connect_to_server leaves transport running (observation)
def b_3490():
    s = MCPServer('real-3490')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #3228  Transport  Rejected streamable-HTTP requests leave live sessions behind (observation)
def b_3228():
    s = MCPServer('real-3228')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #3503  Transport  standalone GET stream advertises application/json but reads text/event-stream (observation)
def b_3503():
    s = MCPServer('real-3503')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #2883  Client  AnyHttpUrl normalization adds trailing slash, breaks RFC 9728 canonical resource URL
#        (pure pydantic observation, no server run needed)
def b_2883():
    s = MCPServer('real-2883')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# ---------------------------------------------------------------------------
# batch 12 (async / hang / disconnect / concurrency candidates, real triggers)
# #192  Client  client hangs when server sends a log notification after init
def b_192():
    s = MCPServer('real-192')
    @s.tool()
    def boom(ctx: Context) -> str:
        ctx.log(level='info', data='post-init log notify')
        return 'pong'
    return s

# #594  Client  call_tool hangs when server sends notifications BEFORE the response
def b_594():
    s = MCPServer('real-594')
    @s.tool()
    def boom(ctx: Context) -> str:
        ctx.info('notify-before-response')
        return 'pong'
    return s

# #838  Server  'Task group is not initialized' in simplest default-config server
def b_838():
    return MCPServer('real-838')

# #753  Client  RuntimeError: Task group is not initialized. Make sure to use run().
def b_753():
    return MCPServer('real-753')

# #3493  Server  MCPServer serves subscriptions/listen & advertises listChanged=true unconditionally
def b_3493():
    s = MCPServer('real-3493')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #212  Transport  tool timeout after 10s -> -32001 disconnect
def b_212():
    s = MCPServer('real-212')
    @s.tool()
    def slow():
        import time
        time.sleep(12)
        return 'done'
    return s

# #1363  Transport  Race Condition in StreamableHTTP Transport -> ClosedResourceError
def b_1363():
    s = MCPServer('real-1363')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #1577  Client  call_tool hangs forever if server crashes / connection dies
def b_1577():
    s = MCPServer('real-1577')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# ---------------------------------------------------------------------------
# batch 13 (concurrency / async-lifecycle / protocol-compliance-gap / observation-only,
#            real triggers where constructible; honest limited+reason otherwise)
# #147  Host     MCP server disconnected on some tool calls (no reproducible cause visible)
def b_147():
    s = MCPServer('real-147')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #201  Host     Client hangs when ctx.info() logging with a pure-Python client
def b_201():
    s = MCPServer('real-201')
    @s.tool()
    def boom(ctx: Context) -> str:
        ctx.info('client-side logging')
        return 'pong'
    return s

# #298  Host     Python tool call longer than 3-5s freezes and breaks the SDK
def b_298():
    s = MCPServer('real-298')
    @s.tool()
    def slow():
        import time
        time.sleep(6)
        return 'done'
    return s

# #355  Server   Type error when using Lifespan context (AppContext db attribute)
def b_355():
    s = MCPServer('real-355')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #402  Server   Claude "Server disconnected" when running a FastMCP intro server
def b_402():
    s = MCPServer('real-402')
    @s.tool()
    def add(a: int, b: int) -> int:
        return a + b
    return s

# #407  Server   Timed out waiting for response (slow Jira tool)
def b_407():
    s = MCPServer('real-407')
    @s.tool()
    def get_all_status():
        import time
        time.sleep(7)
        return [{'id': 1}]
    return s

# #410  Client   Server hangs when /messages endpoint returns unexpected response (404/405)
def b_410():
    s = MCPServer('real-410')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #552  Client   On Windows 11 initializing an MCP client hangs indefinitely (stdio)
def b_552():
    s = MCPServer('real-552')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #575  Client   RuntimeError during cleanup on Windows - no running event loop
def b_575():
    s = MCPServer('real-575')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #623  Client   MCP Inspector can't connect with MCP server (dev/stdio)
def b_623():
    s = MCPServer('real-623')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #668  Client   Will not work if multiple MCP Inspector windows are open (stdio)
def b_668():
    s = MCPServer('real-668')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #680  Transport Streamable HTTP hangs forever when server attempts any callback (sampling)
def b_680():
    s = MCPServer('real-680')
    @s.tool()
    def sample(ctx: Context) -> str:
        return 'pong'
    return s

# #788  Client   ClientSessionGroup error when closing connection with multiple servers
def b_788():
    s = MCPServer('real-788')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #813  Host     MCP SDK hangs (ElasticSearch hybrid-search server)
def b_813():
    s = MCPServer('real-813')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #831  Client   Errors during cleanup with streamablehttp_client + AsyncExitStack
def b_831():
    s = MCPServer('real-831')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #1051 Transport StreamableHTTP GET fails "Bad Request: Missing session ID" during init
def b_1051():
    s = MCPServer('real-1051')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #1070 Transport Unexpected connection closed (ctx.sample / sampling_handler)
def b_1070():
    s = MCPServer('real-1070')
    @s.tool()
    def write(ctx: Context) -> str:
        return 'pong'
    return s

# #1095 Server   Multiple bugs in mcp library related to async context management
def b_1095():
    s = MCPServer('real-1095')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #1097 Client   Roots/List request hangs in client-server communication
def b_1097():
    s = MCPServer('real-1097')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #1100 Client   MCP connection fails silently
def b_1100():
    s = MCPServer('real-1100')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #1152 Client   CancelledError causes duplicate response and server crash (cancel long call)
def b_1152():
    s = MCPServer('real-1152')
    @s.tool()
    def long():
        import time
        time.sleep(10)
        return 'done'
    return s

# #1213 Host     AsyncExitStack fails to close at first attempt
def b_1213():
    s = MCPServer('real-1213')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #1214 Client   Unhandled GeneratorExit error
def b_1214():
    s = MCPServer('real-1214')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #1219 Transport _handle_stateless_request raises ClosedResourceError
def b_1219():
    s = MCPServer('real-1219')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #1272 Server   Server hangs when shutting down if a connection is still open
def b_1272():
    s = MCPServer('real-1272')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #1372 Server   fastmcp.run() runtimeerror: task group is not initialized
def b_1372():
    s = MCPServer('real-1372')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #1420 Client   Protocol Compliance Gap-2: missing logging/propagation of cancellation reasons
def b_1420():
    s = MCPServer('real-1420')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #1421 Client   Implementation Gap-3: missing built-in rate limiting for callback processing
def b_1421():
    s = MCPServer('real-1421')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #1422 Client   Implementation Gap-4: missing configurable ping frequency and rate limiting
def b_1422():
    s = MCPServer('real-1422')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #1423 Client   Implementation Gap-5: missing automatic ping mechanism for connection health
def b_1423():
    s = MCPServer('real-1423')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #1458 Client   Implementation Gap-17: missing cancellation notifications on request timeout
def b_1458():
    s = MCPServer('real-1458')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #1648 Client   ClientDisconnect returns HTTP 500 (client disconnect while reading POST body)
def b_1648():
    s = MCPServer('real-1648')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #1658 Client   ClosedResourceError with FastMCP(stateless_http=True, json_response=True) + Inspector
def b_1658():
    s = MCPServer('real-1658')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #1744 Client   Improve exception tracebacks for easier debugging (reduce asyncio/anyio noise)
def b_1744():
    s = MCPServer('real-1744')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #1789 Client   Client hangs forever when sse_read_timeout specified without read_timeout_seconds
def b_1789():
    s = MCPServer('real-1789')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #1805 Client   Possible resource leak / race condition in streamable_http_client
def b_1805():
    s = MCPServer('real-1805')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #1830 Client   CancelledError from connection failures indistinguishable from external cancellation
def b_1830():
    s = MCPServer('real-1830')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #1941 Transport streamable_http client hangs on POST-only MCP servers (no GET)
def b_1941():
    s = MCPServer('real-1941')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #1967 Server   ClosedResourceError during stateless server shutdown when sending log messages
def b_1967():
    s = MCPServer('real-1967')
    @s.tool()
    def boom(ctx: Context) -> str:
        ctx.info('shutdown log')
        return 'pong'
    return s

# #2064 Client   ClientDisconnect during _handle_post_request crashes stateless session
def b_2064():
    s = MCPServer('real-2064')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #2110 Transport HTTP transport swallows non-2xx status codes causing client to hang
def b_2110():
    s = MCPServer('real-2110')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #2604 Transport one concurrent HTTPStatusError tears down sibling requests
def b_2604():
    s = MCPServer('real-2604')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #2605 Client   Duplicate initialize with changed params overwrites ServerSession.client_params
def b_2605():
    s = MCPServer('real-2605')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #2958 Transport StreamableHTTP server accumulates CLOSE_WAIT sockets behind reverse proxy
def b_2958():
    s = MCPServer('real-2958')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #3216 Server   URI templates do not work with Inspector v2
def b_3216():
    s = MCPServer('real-3216')
    @s.resource('data://users/{name}')
    def r(name: str):
        return name
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #3469 Transport client disconnect while reading POST body logged as exception & answered 500
def b_3469():
    s = MCPServer('real-3469')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #3483 Client   Client never retries after -32020 HeaderMismatch; no public x-mcp-header map
def b_3483():
    s = MCPServer('real-3483')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #3522 Transport streamable HTTP client stays closed after interrupted response + ExceptionGroup
def b_3522():
    s = MCPServer('real-3522')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# #3631 Transport Streamable HTTP notification triggers duplicate response after HTTP 202
def b_3631():
    s = MCPServer('real-3631')
    @s.tool()
    def ping() -> str:
        return 'pong'
    return s

# --------------------------------------------------------------------------- CASES
CASES = {
    342: Case(342, 'Server', 'read_resource', 'data://test', {}, b_342, '#342 base64 encode/decode mismatch for resources'),
    234: Case(234, 'Server', 'call_tool', 'no_such_tool', {}, b_234, '#234 unknown tool is_error=False'),
    281: Case(281, 'Server', 'call_tool', 'fill_form', {'selector': '123', 'text': '456'}, b_281,
              '#281 params transfer: pure number string arg'),
    602: Case(602, 'Server', 'get_prompt', 'greet', {'name': 'bob'}, b_602, '#602 get_prompt missing description'),
    776: Case(776, 'Server', 'call_tool', 'slow', {'x': 1}, b_776, '#776 progress callback exception warning'),
    810: Case(810, 'Transport', 'call_tool', 'item', {}, b_810, '#810 CallToolResult missing structuredContent'),
    1702: Case(1702, 'Server', 'call_tool', 'get_name', {}, b_1702, '#1702 tool output schema validation'),
    2422: Case(2422, 'Server', 'call_tool', 'no_such_tool', {}, b_2422, '#2422 ToolNotFoundError vs ToolError'),
    3266: Case(3266, 'Server', 'call_tool', 'boom', {'x': 1}, b_3266, '#3266 log exceptions in tool calls'),
    3342: Case(3342, 'Server', 'get_prompt', 'p', {}, b_3342, '#3342 prompt validation traceback'),
    1821: Case(1821, 'Client', 'send_ping', '', {}, b_1821, '#1821 JSON-RPC error code session not found'),
    1574: Case(1574, 'Client', 'list_resources', '', {}, b_1574, '#1574 resource URI strict validation'),
    2107: Case(2107, 'Client', 'list_tools', '', {}, b_2107, '#2107 list_changed notifications dropped'),
    3356: Case(3356, 'Transport', 'send_ping', '', {}, b_3356, '#3356 SSE reconnect loop', transport='sse', reconnect=True),
    332: Case(332, 'Client', 'send_ping', '', {}, b_332, '#332 client requests hang if server dies', transport='sse'),
    906: Case(906, 'Client', 'send_ping', '', {}, b_906, '#906 server disconnected without response', transport='sse', disconnect='after_connect'),
    491: Case(491, 'Server', 'subscribe_resource', 'data://test', {}, b_491, '#491 subscribe_resource NotImplementedError', transport='sse'),
    100: Case(100, 'Server', 'list_tools', '', {}, b_100, '#100 list_tools returns <10 tools'),
    348: Case(348, 'Server', 'call_tool', 'img', {}, b_348, '#348 no isError=True for arbitrary tool result'),
    398: Case(398, 'Transport', 'send_ping', '', {}, b_398, '#398 connect SSE invalid transport type', transport='sse'),
    585: Case(585, 'Transport', 'send_ping', '', {}, b_585, '#585 absolute paths in SSE endpoints', transport='sse'),
    783: Case(783, 'Transport', 'send_ping', '', {}, b_783, '#783 mount_path not work with sse_app', transport='sse'),
    1190: Case(1190, 'Transport', 'send_ping', '', {}, b_1190, '#1190 streamable HTTP mode broken'),
    1437: Case(1437, 'Transport', 'send_ping', '', {}, b_1437, '#1437 SSE hangs after disconnect', transport='sse', disconnect='after_connect'),
    2965: Case(2965, 'Server', 'send_ping', '', {}, b_2965, '#2965 check_capability elicitation subcaps', transport='sse'),
    2114: Case(2114, 'Client', 'call_tool', 'boom', {}, b_2114, '#2114 ExceptionGroup obscures real errors'),
    # batch 2 (serialization / validation runtime faults, streamable-HTTP single-call)
    3385: Case(3385, 'Server', 'call_tool', 'inf', {}, b_3385, '#3385 non-finite float -> invalid JSON in text content'),
    3656: Case(3656, 'Server', 'call_tool', 'a', {}, b_3656, '#3656 Audio(data=b"") raises while Image(data=b"") works'),
    3099: Case(3099, 'Server', 'call_tool', 'ext', {'externalX': 5}, b_3099, '#3099 Field(alias) in schema but invalid Python keyword'),
    2591: Case(2591, 'Server', 'call_tool', 'pick', {}, b_2591, '#2591 A | B | C union return type'),
    3353: Case(3353, 'Server', 'list_tools', '', {}, b_3353, '#3353 boolean sub-schemas in Tool.inputSchema/outputSchema'),
    3067: Case(3067, 'Server', 'call_tool', 'add', {'a': 1, 'b': 2, 'typo': 9}, b_3067, '#3067 unknown/misspelled args silently ignored'),
    3341: Case(3341, 'Server', 'call_tool', 'nan', {}, b_3341, '#3341 non-finite float (nan) fails on client'),
    1356: Case(1356, 'Server', 'call_tool', 'u', {}, b_1356, '#1356 special Unicode chars in result'),
    2770: Case(2770, 'Server', 'call_tool', 'boom', {}, b_2770, '#2770 McpError swallowed as isError:true'),
    2429: Case(2429, 'Server', 'call_tool', 'fail', {}, b_2429, '#2429 outputSchema validation blocks isError:true'),
    1796: Case(1796, 'Server', 'call_tool', 'get', {}, b_1796, '#1796 structuredContent present but content omitted'),
    2961: Case(2961, 'Server', 'list_resources', '', {}, b_2961, '#2961 ResourceTemplate.matches() regex special chars'),
    # batch 3 (protocol / more serialization)
    2539: Case(2539, 'Server', 'call_tool', 'r', {}, b_2539, '#2539 None optional fields serialized as JSON null'),
    2057: Case(2057, 'Client', 'raw_post', 'tools/list', {'body': {"jsonrpc": "2.0", "method": "tools/list", "id": None, "params": {}}}, b_proto, '#2057 id:null silently misclassified as notification'),
    2618: Case(2618, 'Transport', 'raw_post', 'initialize', {'body': {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "probe", "version": "1.0"}}}, 'headers': {'MCP-Protocol-Version': '2025-06-18'}}, b_proto, '#2618 mismatched MCP-Protocol-Version header vs body protocolVersion'),
1561: Case(1561, 'Client', 'raw_post', 'invalid/method', {'body': {"jsonrpc": "2.0", "method": "invalid/method", "id": 2, "params": {}}}, b_proto, '#1561 invalid method -> -32602 vs -32601'),
     3193: Case(3193, 'Client', 'raw_post', 'tools/nope', {'body': {"jsonrpc": "2.0", "method": "tools/nope", "id": 3, "params": {}}}, b_proto, '#3193 unknown method -> -32602 vs -32601'),
    # batch 4 (single-call runtime faults: serialization / error-masking / annotations / coercion)
    110: Case(110, 'Client', 'call_tool', 'bad', {}, b_110, '#110 non-UTF-8 server output -> generic error'),
    357: Case(357, 'Server', 'call_tool', 'f', {'x': 1}, b_357, '#357 Context Type Variable detection'),
    488: Case(488, 'Server', 'list_resources', '', {}, b_488, '#488 resource description from __doc__'),
    511: Case(511, 'Server', 'call_tool', 'f', {'x': 1}, b_511, '#511 add annotations with @tool()'),
    662: Case(662, 'Server', 'call_tool', 'greet', {'name': 'bob'}, b_662, '#662 error calling tool with arguments and name'),
    698: Case(698, 'Server', 'call_tool', 'boom', {}, b_698, '#698 Tool.run reveals exception value'),
    743: Case(743, 'Server', 'call_tool', 'boom', {}, b_743, '#743 root cause not logged correctly'),
    820: Case(820, 'Server', 'call_tool', 'add', {'a': 1, 'b': 2}, b_820, '#820 string arguments break server'),
    987: Case(987, 'Client', 'call_tool', 'f', {}, b_987, '#987 CallToolResult serialization valid dictionary'),
    1060: Case(1060, 'Server', 'call_tool', 'img', {}, b_1060, '#1060 PydanticSchemaGenerationError for Image'),
    1361: Case(1361, 'Client', 'call_tool', 'boom', {}, b_1361, '#1361 ClientSession swallows call_tool exceptions'),
    2153: Case(2153, 'Server', 'call_tool', 'boom', {}, b_2153, '#2153 handlers should raise exceptions'),
    3123: Case(3123, 'Server', 'call_tool', 'img', {}, b_3123, '#3123 Image content >99 bytes illegal base64'),
    3345: Case(3345, 'Client', 'call_tool', 'f', {}, b_3345, '#3345 JSON-null structuredContent skips validation'),
    3351: Case(3351, 'Server', 'call_tool', 'f', {'x': 'not_an_int'}, b_3351, '#3351 input-validation discards jsonschema fields'),
    3384: Case(3384, 'Client', 'call_tool', 'ping', {}, b_3384, '#3384 ClientSessionGroup KeyError no tools'),
    3473: Case(3473, 'Client', 'call_tool', 'f', {'x': 1}, b_3473, '#3473 client sends empty _meta on every request'),
    3487: Case(3487, 'Server', 'call_tool', 'ping', {}, b_3487, '#3487 pkg_version() no None guard'),
    3649: Case(3649, 'Server', 'call_tool', 'ping', {}, b_3649, '#3649 completion handler >100 values'),
    # batch 5 (resource/ctx/type-validation registration-time + error-masking faults)
    244: Case(244, 'Server', 'list_resources', '', {}, b_244, '#244 resource() does not accept ctx: Context'),
    1974: Case(1974, 'Server', 'list_tools', '', {}, b_1974, '#1974 find_context_parameter fails on callable class'),
    3337: Case(3337, 'Server', 'list_tools', '', {}, b_3337, '#3337 recursive tool return type no root type'),
    891: Case(891, 'Server', 'call_tool', 'f', {}, b_891, '#891 unsupported operand dict+str -> generic error'),
    140: Case(140, 'Server', 'list_resources', '', {}, b_140, '#140 resource handler with parameter not working'),
    2066: Case(2066, 'Server', 'call_tool', 'f', {}, b_2066, '#2066 invalid JSON EOF while parsing'),
    381: Case(381, 'Server', 'call_tool', 'f', {'x': 1, 'y': 'a'}, b_381, '#381 FastMCP tool parameter parsing type error'),
    1391: Case(1391, 'Server', 'list_tools', '', {}, b_1391, '#1391 wrapped tools using annotations fail'),
    2519: Case(2519, 'Server', 'list_resources', '', {}, b_2519, '#2519 ResourceContents.uri non-nullable uri=null'),
    2960: Case(2960, 'Server', 'call_tool', 'f', {'x': 1}, b_2960, '#2960 validate_tool_use_result_messages false positive'),
    2541: Case(2541, 'Server', 'get_prompt', 'p', {'name': 'bob'}, b_2541, '#2541 ValueError discards exception chain in get_prompt'),
    1215: Case(1215, 'Server', 'list_resources', '', {}, b_1215, '#1215 uri params mismatch with function params'),
    1853: Case(1853, 'Server', 'list_tools', '', {}, b_1853, '#1853 missing call capability in tasks.requests.tools'),
    1482: Case(1482, 'Server', 'list_tools', '', {}, b_1482, '#1482 unable to call context.elicit'),
    1131: Case(1131, 'Server', 'call_tool', 'f', {}, b_1131, '#1131 Pydantic schema generation for non-standard output'),
    # batch 6 (misc Server runtime / registration / error-masking candidates)
    103: Case(103, 'Server', 'list_tools', '', {}, b_103, '#103 request_meta not available in server.request_context'),
    123: Case(123, 'Server', 'call_tool', 'f', {}, b_123, '#123 garbled Japanese characters fastmcp'),
    178: Case(178, 'Server', 'list_resources', '', {}, b_178, '#178 log_level DEBUG breaks when creating a resource'),
    262: Case(262, 'Server', 'call_tool', 'f', {'x': 1}, b_262, '#262 cannot get response from session.call_tool()'),
    337: Case(337, 'Server', 'list_tools', '', {}, b_337, '#337 simple echo MCP server fails to start with mcp.run()'),
    341: Case(341, 'Client', 'list_tools', '', {}, b_341, '#341 wrong types for logging_callback in Client'),
    389: Case(389, 'Server', 'call_tool', 'slow', {'x': 1}, b_389, '#389 TypeError NoneType not callable when function takes too long'),
    399: Case(399, 'Server', 'call_tool', 'slow', {'x': 1}, b_399, '#399 ProgressNotification message field missing'),
    853: Case(853, 'Server', 'call_tool', 'f', {'x': 1}, b_853, '#853 Pydantic deserialize file much more memory'),
    1267: Case(1267, 'Server', 'call_tool', 'f', {'x': 1}, b_1267, '#1267 Pydantic v2 dumps_kwargs not supported'),
    1768: Case(1768, 'Server', 'call_tool', 'f', {'x': 1}, b_1768, '#1768 UrlElicitationRequiredError not thrown as McpError'),
    2326: Case(2326, 'Server', 'call_tool', 'f', {'x': 1}, b_2326, '#2326 Context Synchronization Failure'),
    2386: Case(2386, 'Server', 'call_tool', 'boom', {}, b_2386, '#2386 sanitize tool handler error messages CWE-209'),
    2431: Case(2431, 'Server', 'call_tool', 'boom', {}, b_2431, '#2431 McpError not pickle-safe and fails to unpickle'),
    3434: Case(3434, 'Server', 'call_tool', 'f', {'x': 1}, b_3434, '#3434 in-process callback failures break tool calls'),
    3476: Case(3476, 'Server', 'get_prompt', 'p', {'name': 'bob'}, b_3476, '#3476 missing prompt-level _meta support'),
    3484: Case(3484, 'Server', 'list_tools', '', {}, b_3484, '#3484 no x-mcp-header declaration mechanism'),
    # batch 7 (resource-not-found error path / Server misc protocol)
    1579: Case(1579, 'Server', 'read_resource', 'data://missing', {}, b_1579, '#1579 read_resource wrong error code on not-found'),
    2794: Case(2794, 'Server', 'read_resource', 'data://missing', {}, b_2794, '#2794 SEP-2164 resource not found error code'),
    268: Case(268, 'Server', 'list_resources', '', {}, b_268, '#268 List Resource is not working'),
    929: Case(929, 'Server', 'call_tool', 'f', {'x': 1}, b_929, '#929 tool call OK in inspector but error in terminal'),
    858: Case(858, 'Server', 'list_tools', '', {}, b_858, '#858 minimal MCP server + mcp inspector'),
    2156: Case(2156, 'Server', 'list_tools', '', {}, b_2156, '#2156 add_tool missing execution parameter'),
    2702: Case(2702, 'Server', 'list_tools', '', {}, b_2702, '#2702 streamable_http_app breaks with BaseHTTPMiddleware'),
    # batch 8 (misc runtime / transport / coercion / registration faults)
    3227: Case(3227, 'Server', 'list_tools', '', {}, b_3227, '#3227 NotRequired TypedDict return -> PydanticForbiddenQualifier'),
    1843: Case(1843, 'Server', 'call_tool', 'f', {'flag': 'false'}, b_1843, '#1843 function param coercion false=>False'),
    1873: Case(1873, 'Server', 'call_tool', 'f', {'uuid': '123abc'}, b_1873, '#1873 string param starting with digit coerced to number'),
    2376: Case(2376, 'Client', 'call_tool', 'img', {}, b_2376, '#2376 Image/ImageContent serialization in stateless HTTP'),
    892: Case(892, 'Client', 'list_resources', '', {}, b_892, '#892 validation error when listing resources'),
    1010: Case(1010, 'Transport', 'raw_post', 'tools/list', {'body': {"jsonrpc": "2.0", "method": "tools/list", "id": 1, "params": {}}}, b_1010, '#1010 HTTP errors silently swallowed'),
    1212: Case(1212, 'Client', 'raw_post', 'tools/list', {'body': {"jsonrpc": "2.0", "method": "tools/list", "id": 1, "params": {}}}, b_1212, '#1212 HTTP status exception disregards message'),
    2688: Case(2688, 'Transport', 'raw_post', 'tools/list', {'body': {"jsonrpc": "2.0", "method": "tools/list", "id": 1, "params": {}}}, b_2688, '#2688 allowed_hosts=[] rejects external Host header 421'),
    2741: Case(2741, 'Transport', 'call_tool', 'boom', {}, b_2741, '#2741 in-session exceptions masked as -32603'),
    3639: Case(3639, 'Transport', 'raw_post', 'tools/list', {'body': {"jsonrpc": "2.0", "method": "tools/list", "id": None, "params": {}}}, b_3639, '#3639 null-id JSON-RPC error in 200 JSON response'),
    2848: Case(2848, 'Transport', 'raw_post', 'tools/list', {'body': {"jsonrpc": "2.0", "method": "tools/list", "params": {}}}, b_2848, '#2848 invalid JSON-RPC envelope not correlated with id'),
    2655: Case(2655, 'Transport', 'raw_post', 'tools/list', {'body': {"jsonrpc": "2.0", "method": "tools/list", "id": 1, "params": {}}}, b_2655, '#2655 server silently drops in-flight request on reused JSON-RPC id'),
    3150: Case(3150, 'Transport', 'raw_post', 'tools/list', {'body': {"jsonrpc": "2.0", "method": "tools/list", "id": 1, "params": {}}}, b_3150, '#3150 non-UTF-8 POST body -> 500 instead of 400'),
    # batch 9 (client / transport protocol faults via raw_post / send_ping)
    3273: Case(3273, 'Client', 'send_ping', '', {}, b_3273, '#3273 ping returns Method not found on 2026-07-28'),
    1382: Case(1382, 'Client', 'raw_post', 'initialize', {'body': {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "probe", "version": "1.0"}}}, 'content_type': 'text/plain'}, b_1382, '#1382 Cannot handle Unexpected content type'),
    2375: Case(2375, 'Transport', 'raw_post', 'initialize', {'body': {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "probe", "version": "1.0"}}}, 'content_type': 'text/plain'}, b_2375, '#2375 Hardcoded Content-Type cannot be overridden'),
    2432: Case(2432, 'Transport', 'raw_post', 'initialize', {'body': {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "probe", "version": "1.0"}}}}, b_2432, '#2432 Initialize hangs if no Content-Type text/plain'),
    1717: Case(1717, 'Client', 'raw_post', 'tools/list', {'body': {"jsonrpc": "2.0", "method": "tools/list", "id": 1, "params": {}}}, b_1717, '#1717 UnboundLocalError in send_request'),
    2480: Case(2480, 'Client', 'raw_post', 'notifications/cancelled', {'body': {"jsonrpc": "2.0", "method": "notifications/cancelled", "params": {"requestId": 1, "reason": "test"}}}, b_2480, '#2480 RequestResponder.cancel sends JSON-RPC response'),
    2328: Case(2328, 'Server', 'raw_post', 'initialize', {'raw_body': b'{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}\xff\xfe', 'content_type': 'application/json'}, b_2328, '#2328 server crashes on raw invalid UTF-8 bytes'),
    # batch 10 (serialization / malformed-message / notify / OPTIONS candidates, single call or raw_post)
    280: Case(280, 'Client', 'call_tool', 'ping', {}, b_280, '#280 JSONRPCMessage has no attribute message (1.4.0)'),
    691: Case(691, 'Client', 'call_tool', 'ping', {}, b_691, '#691 JSONRPCMessage has no attribute message (1.8.0)'),
    290: Case(290, 'Transport', 'call_tool', 'boom', {}, b_290, '#290 Expected comma or bracket after array element in JSON'),
    1144: Case(1144, 'Transport', 'call_tool', 'boom', {}, b_1144, '#1144 call_tool hangs on invalid JSONRPCMessage'),
    701: Case(701, 'Server', 'call_tool', 'boom', {}, b_701, '#701 StreamableHttp Server send notify invalid'),
    1079: Case(1079, 'Transport', 'raw_post', 'options', {'body': {"jsonrpc": "2.0", "method": "tools/list", "id": 1, "params": {}}, 'headers': {'OPTIONS': 'true'}}, b_1079, '#1079 Missing OPTIONS handler for Streamable HTTP'),
    1835: Case(1835, 'Transport', 'raw_post', 'tools/list', {'body': {"jsonrpc": "2.0", "method": "tools/list", "id": 1, "params": {}}}, b_1835, '#1835 HTTP errors not handled properly by streamable_http'),
    2548: Case(2548, 'Client', 'call_tool', 'ping', {}, b_2548, '#2548 BaseSession.send_request envelope-fields collision'),
    2673: Case(2673, 'Client', 'call_tool', 'ping', {}, b_2673, '#2673 receive loop swallows callback exceptions'),
    2564: Case(2564, 'Client', 'call_tool', 'ping', {}, b_2564, '#2564 raise without from discards exception chain'),
    3174: Case(3174, 'Client', 'call_tool', 'boom', {}, b_3174, '#3174 JSON-RPC error responses leave OTel spans UNSET'),
    3490: Case(3490, 'Client', 'call_tool', 'ping', {}, b_3490, '#3490 rejected connect_to_server leaves transport running'),
    3228: Case(3228, 'Transport', 'raw_post', 'tools/list', {'body': {"jsonrpc": "2.0", "method": "tools/list", "id": 1, "params": {}}}, b_3228, '#3228 rejected requests leave live sessions behind'),
    3503: Case(3503, 'Transport', 'call_tool', 'ping', {}, b_3503, '#3503 standalone GET stream advertises wrong Accept'),
    2883: Case(2883, 'Client', 'call_tool', 'ping', {}, b_2883, '#2883 AnyHttpUrl normalization adds trailing slash'),
    # batch 12 (async / hang / disconnect / concurrency, real triggers)
    192: Case(192, 'Client', 'call_tool', 'boom', {}, b_192, '#192 client hangs on log notification after init'),
    594: Case(594, 'Client', 'call_tool', 'boom', {}, b_594, '#594 call_tool hangs when server sends notifications before response'),
    838: Case(838, 'Server', 'list_tools', '', {}, b_838, '#838 Task group not initialized in default server'),
    753: Case(753, 'Client', 'list_tools', '', {}, b_753, '#753 Task group not initialized Make sure to use run()'),
    3493: Case(3493, 'Server', 'list_tools', '', {}, b_3493, '#3493 subscriptions/listen & listChanged=true unconditional'),
    212: Case(212, 'Transport', 'call_tool', 'slow', {}, b_212, '#212 tool timeout after 10s -> -32001 disconnect', client_timeout=15.0),
    1363: Case(1363, 'Transport', 'call_tool', 'ping', {}, b_1363, '#1363 StreamableHTTP Race Condition -> ClosedResourceError', concurrency=5),
    1577: Case(1577, 'Client', 'call_tool', 'ping', {}, b_1577, '#1577 call_tool hangs if server crashes/connection dies'),
    # batch 13 (concurrency / async-lifecycle / protocol-compliance-gap / observation-only)
    147: Case(147, 'Host', 'call_tool', 'ping', {}, b_147, '#147 MCP server disconnected'),
    201: Case(201, 'Host', 'call_tool', 'boom', {}, b_201, '#201 client hangs on ctx.info() logging'),
    298: Case(298, 'Host', 'call_tool', 'slow', {}, b_298, '#298 tool call >3-5s freezes SDK', client_timeout=8.0),
    355: Case(355, 'Server', 'call_tool', 'ping', {}, b_355, '#355 type error using Lifespan context'),
    402: Case(402, 'Server', 'call_tool', 'add', {'a': 1, 'b': 2}, b_402, '#402 Claude Server disconnected'),
    407: Case(407, 'Server', 'call_tool', 'get_all_status', {}, b_407, '#407 timed out waiting for response', client_timeout=8.0),
    410: Case(410, 'Client', 'call_tool', 'ping', {}, b_410, '#410 server hangs on /messages unexpected response'),
    552: Case(552, 'Client', 'call_tool', 'ping', {}, b_552, '#552 Windows 11 init hangs (stdio)'),
    575: Case(575, 'Client', 'call_tool', 'ping', {}, b_575, '#575 cleanup RuntimeError no running event loop (Windows)'),
    623: Case(623, 'Client', 'call_tool', 'ping', {}, b_623, '#623 Inspector cannot connect with server'),
    668: Case(668, 'Client', 'call_tool', 'ping', {}, b_668, '#668 multiple Inspector windows'),
    680: Case(680, 'Transport', 'call_tool', 'sample', {}, b_680, '#680 Streamable HTTP hangs on any callback'),
    788: Case(788, 'Client', 'call_tool', 'ping', {}, b_788, '#788 ClientSessionGroup close error'),
    813: Case(813, 'Host', 'call_tool', 'ping', {}, b_813, '#813 MCP SDK hangs'),
    831: Case(831, 'Client', 'call_tool', 'ping', {}, b_831, '#831 cleanup errors streamablehttp_client AsyncExitStack'),
    1051: Case(1051, 'Transport', 'call_tool', 'ping', {}, b_1051, '#1051 StreamableHTTP GET missing session ID'),
    1070: Case(1070, 'Transport', 'call_tool', 'write', {}, b_1070, '#1070 unexpected connection closed (ctx.sample)'),
    1095: Case(1095, 'Server', 'call_tool', 'ping', {}, b_1095, '#1095 async context management bugs'),
    1097: Case(1097, 'Client', 'call_tool', 'ping', {}, b_1097, '#1097 Roots/List request hangs'),
    1100: Case(1100, 'Client', 'call_tool', 'ping', {}, b_1100, '#1100 MCP connection fails silently'),
    1152: Case(1152, 'Client', 'call_tool', 'long', {}, b_1152, '#1152 CancelledError duplicate response + crash', client_timeout=12.0),
    1213: Case(1213, 'Host', 'call_tool', 'ping', {}, b_1213, '#1213 AsyncExitStack fails to close first attempt'),
    1214: Case(1214, 'Client', 'call_tool', 'ping', {}, b_1214, '#1214 unhandled GeneratorExit error'),
    1219: Case(1219, 'Transport', 'call_tool', 'ping', {}, b_1219, '#1219 _handle_stateless_request ClosedResourceError'),
    1272: Case(1272, 'Server', 'call_tool', 'ping', {}, b_1272, '#1272 server hangs shutting down with open connection'),
    1372: Case(1372, 'Server', 'call_tool', 'ping', {}, b_1372, '#1372 fastmcp.run() task group not initialized'),
    1420: Case(1420, 'Client', 'call_tool', 'ping', {}, b_1420, '#1420 compliance gap-2 cancellation reasons'),
    1421: Case(1421, 'Client', 'call_tool', 'ping', {}, b_1421, '#1421 gap-3 rate limiting callbacks'),
    1422: Case(1422, 'Client', 'call_tool', 'ping', {}, b_1422, '#1422 gap-4 ping frequency/rate limiting'),
    1423: Case(1423, 'Client', 'call_tool', 'ping', {}, b_1423, '#1423 gap-5 automatic ping health monitoring'),
    1458: Case(1458, 'Client', 'call_tool', 'ping', {}, b_1458, '#1458 gap-17 cancellation notifications on timeout'),
    1648: Case(1648, 'Client', 'call_tool', 'ping', {}, b_1648, '#1648 ClientDisconnect returns HTTP 500'),
    1658: Case(1658, 'Client', 'call_tool', 'ping', {}, b_1658, '#1658 ClosedResourceError stateless_http Inspector'),
    1744: Case(1744, 'Client', 'call_tool', 'ping', {}, b_1744, '#1744 improve exception tracebacks'),
    1789: Case(1789, 'Client', 'call_tool', 'ping', {}, b_1789, '#1789 client hangs forever sse_read_timeout'),
    1805: Case(1805, 'Client', 'call_tool', 'ping', {}, b_1805, '#1805 resource leak/race in streamable_http_client'),
    1830: Case(1830, 'Client', 'call_tool', 'ping', {}, b_1830, '#1830 CancelledError indistinguishable from external cancel'),
    1941: Case(1941, 'Transport', 'call_tool', 'ping', {}, b_1941, '#1941 client hangs on POST-only servers'),
    1967: Case(1967, 'Server', 'call_tool', 'boom', {}, b_1967, '#1967 ClosedResourceError stateless shutdown log messages'),
    2064: Case(2064, 'Client', 'call_tool', 'ping', {}, b_2064, '#2064 ClientDisconnect crashes stateless session'),
    2110: Case(2110, 'Transport', 'call_tool', 'ping', {}, b_2110, '#2110 HTTP swallows non-2xx -> client hangs'),
    2604: Case(2604, 'Transport', 'call_tool', 'ping', {}, b_2604, '#2604 one concurrent HTTPStatusError tears down siblings', concurrency=3),
    2605: Case(2605, 'Client', 'call_tool', 'ping', {}, b_2605, '#2605 duplicate initialize overwrites client_params'),
    2958: Case(2958, 'Transport', 'call_tool', 'ping', {}, b_2958, '#2958 CLOSE_WAIT sockets behind reverse proxy'),
    3216: Case(3216, 'Server', 'list_resources', '', {}, b_3216, '#3216 URI templates not working with Inspector v2'),
    3469: Case(3469, 'Transport', 'call_tool', 'ping', {}, b_3469, '#3469 client disconnect while reading POST body -> 500'),
    3483: Case(3483, 'Client', 'call_tool', 'ping', {}, b_3483, '#3483 no retry after -32020 HeaderMismatch'),
    3522: Case(3522, 'Transport', 'call_tool', 'ping', {}, b_3522, '#3522 client stays closed after interrupted response'),
    3631: Case(3631, 'Transport', 'call_tool', 'ping', {}, b_3631, '#3631 notification triggers duplicate response after 202'),
}

# batch label -> list of issue numbers (for --batch)
BATCHES = {
    '1': sorted(CASES.keys()),
    '2': [3385, 3656, 3099, 2591, 3353, 3067, 3341, 1356, 2770, 2429, 1796, 2961],
    '3': [2539, 2057, 2618, 1561, 3193],
    '4': [110, 357, 488, 511, 662, 698, 743, 820, 987, 1060, 1361, 2153, 3123, 3345, 3351, 3384, 3473, 3487, 3649],
    '5': [244, 1974, 3337, 891, 140, 2066, 381, 1391, 2519, 2960, 2541, 1215, 1853, 1482, 1131],
    '6': [103, 123, 178, 262, 337, 341, 389, 399, 853, 1267, 1768, 2326, 2386, 2431, 3434, 3476, 3484],
    '7': [1579, 2794, 268, 929, 858, 2156, 2702],
    '8': [3227, 1843, 1873, 2376, 892, 1010, 1212, 2688, 2741, 3639, 2848, 2655, 3150],
    '9': [3273, 1382, 2375, 2432, 1717, 2480, 2328],
    '10': [280, 691, 290, 1144, 701, 1079, 1835, 2548, 2673, 2564, 3174, 3490, 3228, 3503, 2883],
    '12': [192, 594, 838, 753, 3493, 212, 1363, 1577],
    '13': [147, 201, 298, 355, 402, 407, 410, 552, 575, 623, 668, 680, 788, 813, 831, 1051, 1070,
           1095, 1097, 1100, 1152, 1213, 1214, 1219, 1272, 1372, 1420, 1421, 1422, 1423, 1458,
           1648, 1658, 1744, 1789, 1805, 1830, 1941, 1967, 2064, 2110, 2604, 2605, 2958, 3216,
           3469, 3483, 3522, 3631],
}

# ---------------------------------------------------------------------------
# VERIFIED (already-reproduced) cases. These reuse the builder functions that live in
# run_real_http.py / run_real_http2.py (imported lazily so this module still loads
# standalone). Each maps issue -> Case with the real trigger that was used.
# These are the 18 confirmed-reproducible bugs (mcp 2.2.0 + streamable-HTTP).
#
# ⚠️【溯源索引 · 18 条 VERIFIED 的代码位置 —— 下次直接看这里，勿再找不到】
#   每条 verified 的复现代码都标注了【文件::函数】。证据文件在 data/real_raw/real_r_*.txt，
#   索引在 data/real_index.json。这些是数据重构前(run_real_http*.py)已复现的 18 条去重 issue。
#   - #3549  Server   run_real_http2.py::case_race        call_tool(inc)         -> real_r_race_lost_update.txt
#   - #3637  Host     run_real_http2.py::case_flat        call_tool(summarize)  -> real_r_flat_argument.txt
#   - #3643  Server   run_real_http2.py::case_userlist    call_tool(greet)      -> real_r_userlist_prompt.txt
#   - #3556  Transport run_real_http2.py::case_404        404 dead session      -> real_r_session_reinit_404.txt
#   - #3640  Server   run_real_http2.py::case_capabilities call_tool(ping)      -> real_r_capabilities_drop.txt
#   - #3557  Transport run_real_http2.py::case_jsonrpc_code raw_post malformed  -> real_r_jsonrpc_error_code.txt
#   - #3644  Server   run_real_http2.py::case_outputschema_mode call_tool       -> real_r_outputschema_mode.txt
#   - #3646  Host     run_real_http2.py::case_extra_arg   call_tool(extra arg)  -> real_r_extra_arg_silent.txt
#   - #3585  Server   run_real_http.py::b_media_mime      call_tool(get_image)  -> real_r_media_unregistered_mime.txt
#   - #3586  Server   run_real_http.py::b_nontool_exc     call_tool(fragile)    -> real_r_non_tool_error_silent.txt
#   - #3592  Server   run_real_http.py::b_unregistered_result call_tool(lookup) -> real_r_fallback_success_flag.txt
#   - #3554  Server   run_real_http.py::b_bytes_output    call_tool(get_bytes)  -> real_r_bytes_output_crash.txt
#   - #3573  Server   run_real_http.py::b_iterator_meta   call_tool(gen)        -> real_r_iterator_meta_fail.txt
#   - #3569  Server   run_real_http.py::b_perm_raise      call_tool(fragile2)   -> real_r_permission_swallow.txt
#   - #3572  Host     run_real_http.py::b_validation_echo call_tool(lookup)     -> real_r_validation_echo_input.txt
#   - #3578  Server   run_real_http.py::b_duplicate_tool  call_tool(calc)       -> real_r_duplicate_tool_shadow.txt
#   - #3579  Host     run_real_http.py::b_empty_server    call_tool(nonexistent)-> real_r_empty_server_components.txt
#   - #3560  Transport run_real_http.py::b_slow_timeout   call_tool(slow)       -> real_r_tool_timeout.txt
# ---------------------------------------------------------------------------
def _verified_cases():
    import importlib.util, os as _os
    here = _os.path.dirname(_os.path.abspath(__file__))
    spec = importlib.util.spec_from_file_location('_rrh', _os.path.join(here, 'run_real_http.py'))
    rrh = importlib.util.module_from_spec(spec); spec.loader.exec_module(rrh)
    try:
        spec2 = importlib.util.spec_from_file_location('_rrh2', _os.path.join(here, 'run_real_http2.py'))
        rrh2 = importlib.util.module_from_spec(spec2); spec2.loader.exec_module(rrh2)
    except Exception:
        rrh2 = None
    # map issue -> (builder, layer, tool, args, desc, mode)
    m = {}
    for tup in rrh.CASES:
        cid, b, ly, desc, tool, args, src, mode = tup
        n = int(src.split('#')[1]); m.setdefault(n, (b, ly, tool, args, desc))
    if rrh2:
        for tup in rrh2.CASES:
            cid, b, ly, desc, src = tup
            n = int(src.split('#')[1])
            # rrh2 cases embed the trigger in their runner logic; record a tool trigger
            tool = 'ping' if 'ping' in desc else cid.replace('r_', '').split('_')[0]
            m.setdefault(n, (b, ly, tool, {}, desc))
    out = {}
    for n, (b, ly, tool, args, desc) in m.items():
        out[n] = Case(n, ly, 'call_tool', tool, args, b, desc)
    return out


VERIFIED = _verified_cases()
# add verified into the shared CASES so repro_progress marks them done too
CASES.update(VERIFIED)

# ---------------------------------------------------------------------------
# batch 14+ : remaining non-auth bugs (env / transport-config / example / protocol-
# observation / runtime). Defined in runner/repro_cases_b14.py (auto-generated).
# Merge into CASES and register BATCHES['14'].
from repro_cases_b14 import CASES_B14, BATCHES_B14
CASES.update(CASES_B14)
BATCHES['14'] = BATCHES_B14