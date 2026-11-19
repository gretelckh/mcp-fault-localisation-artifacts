# Local validation of issues #3578 and #3384

The [#3578 issue thread](https://github.com/modelcontextprotocol/python-sdk/issues/3578) records that maintainers closed it as a duplicate of [#3384](https://github.com/modelcontextprotocol/python-sdk/issues/3384). Both describe an empty-component ClientSessionGroup connection that raises KeyError.

The check was run on 2026-11-19 with mcp 2.2.0, Python 3.13.9 and Windows using an in-process client and server. It exercises the connect_with_session path. In each of three rounds, the connection to a server with zero components raised KeyError in _aggregate_components. A server with one registered tool connected in each round.

    python repro/validation/issue_3578_empty_session_group.py

Observed console output:

    mcp=2.2.0 Python=3.13.9 OS=Windows mode=in-process
    empty KeyError check:20 -> connect_with_session:291 -> _aggregate_components:420
    one_tool CONNECTED
    empty KeyError check:20 -> connect_with_session:291 -> _aggregate_components:420
    one_tool CONNECTED
    empty KeyError check:20 -> connect_with_session:291 -> _aggregate_components:420
    one_tool CONNECTED

The two issue IDs refer to a shared bug mechanism. The [linked capture](../captures/issue_3578.txt) records a different trigger. This validation is separate from the scored Study A input and its annotations.
