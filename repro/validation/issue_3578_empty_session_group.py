import platform
import traceback
from importlib.metadata import version
import anyio
import mcp_types as types
from mcp.client.client import Client
from mcp.client.session_group import ClientSessionGroup
from mcp.server.mcpserver import MCPServer

async def check(register_tool):
    server = MCPServer("local-session-group-check")
    if register_tool:
        @server.tool()
        def ping() -> str:
            return "pong"

    group = ClientSessionGroup()
    async with Client(server) as client:
        try:
            await group.connect_with_session(types.Implementation(name="local-check", version="1"), client.session)
        except KeyError as exc:
            frames = traceback.extract_tb(exc.__traceback__)
            print("one_tool" if register_tool else "empty", "KeyError",
                  " -> ".join(f"{frame.name}:{frame.lineno}" for frame in frames))
            return False
    print("one_tool" if register_tool else "empty", "CONNECTED")
    return True

async def main():
    for _ in range(3):
        assert not await check(False)
        assert await check(True)

print(f"mcp={version('mcp')} Python={platform.python_version()} OS={platform.system()} mode=in-process")
assert version("mcp") == "2.2.0"
anyio.run(main)
