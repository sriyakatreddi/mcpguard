# Concepts — review sheet

Lean notes on concepts learned building MCPGuard. Format: **what** ·
*mental model* · **interview one-liner**. Appended to as the project grows.

---

### SDK / Library / API
Pre-written code + tools for building on a platform. *A furniture kit: skip the
milling, just assemble.* The `mcp` package is the MCP SDK.
- Library = reusable code you call · SDK = kit of libraries + tools · API = the functions it exposes.
- **One-liner:** "You install an SDK and call its API."

### Virtual environment & pinning
Project-private folder of installed packages; pinning locks versions. *A sandbox
per project.* Never commit `.venv/` — rebuild it from `pyproject.toml`.
- **One-liner:** "Isolate deps per project and pin versions for reproducibility — kills 'works on my machine.'"

### pyproject.toml
PEP 621 file declaring name, Python version, and deps — the env's source of truth.
- `mcp>=1.27,<2` = "at least 1.27, never 2.0+" (pin the major to block breaking releases).
- **One-liner:** "Version ranges are interval logic; resolving them is constraint satisfaction."

### Decorators
A function that wraps another and returns the wrapped version; `@` = reassignment.
*Gift wrap: adds behavior around a function without editing its body.*
```python
@logged            # same as: add = logged(add)
def add(a, b): return a + b
```
- `@mcp.tool()` registers a function as a tool + reads its hints/docstring for the schema.
- **One-liner:** "A decorator is a higher-order function; `@` is sugar for reassignment."

### async / await
`async def` can pause at `await` to let other work run instead of blocking.
*A chef chopping veg while the oven heats.* Used for I/O-bound waiting.
- **One-liner:** "Cooperative concurrency for I/O — tasks yield on `await` so the event loop runs others."

### Context managers (`with` / `async with`)
Guarantee cleanup: setup on enter, cleanup on exit — on every path (return,
exception). `async with` = same, but enter/exit can `await`. *Boxes closed
inner-first (LIFO = stack).*
```python
with open("f.txt") as f:   # auto-closes even if read() raises
    f.read()
```
- **One-liner:** "Context manager = guaranteed cleanup on every exit path (like RAII)."

### Topological sort
Order a DAG so each node comes after its dependencies. *Socks before shoes.*
`pip` installs leaf deps first → that ordering is a topo sort.
- **One-liner:** "Orders a DAG by dependency — the core of 'Course Schedule.'"

### Secrets hygiene & .gitignore
`.gitignore` = files git never tracks. Commit source; ignore artifacts, machine
files, and secrets (`.env`), but keep an `.env.example` template (via `!`).
- **One-liner:** "Secrets live in ignored `.env` files or a secrets manager, never in git."

### MCP (project domain)
Lets an AI agent discover/call server **tools** over JSON-RPC. Two messages:
- `tools/list` — discover tools (name, description, `inputSchema`).
- `tools/call` — invoke a tool with arguments.
- MCPGuard proxies the middle, inspecting both before forwarding.
- **One-liner:** "MCP = `tools/list` (discovery) + `tools/call` (invocation); my gateway intercepts both."
