"""A minimal two-tool MCP server, built to learn the protocol.

This is a learning scaffold, not part of the MCPGuard architecture. It exposes
two tools (`add` and `read_file`) over the stdio transport so we can see exactly
how the MCP Python SDK turns a plain Python function into a tool an AI agent can
discover and call.

Run it directly with:  python examples/hello_server.py
(though it expects an MCP client on the other end of stdin/stdout).
"""

from pathlib import Path

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("hello-mcpguard")


@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two integers and return their sum.

    Args:
        a: The first integer.
        b: The second integer.

    Returns:
        The sum of ``a`` and ``b``.
    """
    return a + b


@mcp.tool()
def read_file(path: str) -> str:
    """Read a UTF-8 text file and return its contents.

    Args:
        path: Filesystem path to the file to read.

    Returns:
        The file's contents, or a human-readable error message if the file
        does not exist or cannot be decoded as UTF-8.
    """
    target = Path(path)
    try:
        return target.read_text(encoding="utf-8")
    except FileNotFoundError:
        return f"Error: no file found at {path!r}"
    except UnicodeDecodeError:
        return f"Error: {path!r} is not valid UTF-8 text"


if __name__ == "__main__":
    mcp.run(transport="stdio")
