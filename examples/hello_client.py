"""A minimal MCP client that drives ``hello_server.py``.

This is the other half of the learning scaffold. It launches the server as a
subprocess over stdio, performs the MCP handshake, lists the available tools,
and calls each one. Run it with:  python examples/hello_client.py
"""

import asyncio

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

server_params = StdioServerParameters(
    command="python",
    args=["examples/hello_server.py"],
)


async def main() -> None:
    """Connect to the hello server, list its tools, and call each one."""
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            print("Tools the agent can see (this is the tools/list response):")
            for tool in tools.tools:
                print(f"  - {tool.name}: {tool.description}")

            add_result = await session.call_tool("add", {"a": 2, "b": 40})
            print(f"\nadd(2, 40) -> {add_result.content[0].text}")

            file_result = await session.call_tool("read_file", {"path": "LICENSE"})
            first_line = file_result.content[0].text.splitlines()[0]
            print(f"read_file('LICENSE') first line -> {first_line}")


if __name__ == "__main__":
    asyncio.run(main())
