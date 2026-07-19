"""An intentionally insecure MCP server used as the attack test target.

This server is the "before" half of the MCPGuard demo loop: every attack class
is fired at it to prove the exploit works, and only then is the gateway placed
in front of it to prove the exploit is blocked.

Every tool here is deliberately unsafe. There is no path validation, shell
commands run through ``shell=True``, and ``send_data`` is an exfiltration sink.

SECURITY: run this locally, over stdio, against a controlled client only.
Never expose it on a network and never deploy it.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("vulnerable-mcpguard-target")

EXFIL_LOG: list[dict[str, str]] = []


@mcp.tool()
def read_file(path: str) -> str:
    """Read a file and return its contents.

    Intentionally vulnerable: the path is used verbatim with no validation or
    canonicalization, so ``../../../etc/passwd`` resolves outside any intended
    directory. This is the target for the path-traversal payload.

    Args:
        path: Filesystem path to read.

    Returns:
        The file's contents, or a human-readable error string on failure.
    """
    try:
        return Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        return f"Error: no file found at {path!r}"
    except (UnicodeDecodeError, IsADirectoryError, PermissionError) as exc:
        return f"Error: could not read {path!r}: {exc}"


@mcp.tool()
def run_shell(cmd: str) -> str:
    """Run a shell command and return its combined output.

    Intentionally vulnerable: ``cmd`` is passed straight to the shell with
    ``shell=True``, so metacharacters like ``;`` and ``|`` let an attacker chain
    arbitrary commands. This is the target for the command-injection payload.

    Args:
        cmd: The shell command line to execute.

    Returns:
        The command's combined stdout and stderr, or an error string on failure.
    """
    try:
        completed = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
        return completed.stdout + completed.stderr
    except subprocess.TimeoutExpired:
        return f"Error: command timed out: {cmd!r}"


@mcp.tool()
def send_data(destination: str, content: str) -> str:
    """Send data to an external destination (simulated exfiltration sink).

    This does not make a real network call. It records the destination and
    content in ``EXFIL_LOG`` so a payload's ``verify_success`` can later confirm
    that data left the agent. It stands in for the endpoint an attacker would
    use to exfiltrate stolen file contents or command output.

    Args:
        destination: Where the data would be sent (host, URL, etc.).
        content: The payload of data being exfiltrated.

    Returns:
        A confirmation string describing what was "sent".
    """
    EXFIL_LOG.append({"destination": destination, "content": content})
    return f"Sent {len(content)} bytes to {destination}"


if __name__ == "__main__":
    mcp.run(transport="stdio")
