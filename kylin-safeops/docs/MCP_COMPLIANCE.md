# KylinSafeOps MCP Server Compliance

## Positioning

KylinSafeOps now provides two MCP-facing layers:

1. B/S application API: existing `/api/mcp`, `/api/mcp/tools/list`, `/api/mcp/tools/call`, plus resources and prompts compatibility endpoints.
2. Standard MCP Server entry: `backend.app.mcp_server`, intended for MCP clients through stdio and, where supported by the Python MCP SDK, SSE.

Cherry Studio, Cursor, Claude Desktop, and similar tools are only test clients. They are not part of the competition deliverable. The project itself remains a B/S application with its own frontend and FastAPI backend.

## Standard MCP Server Entry

```bash
python3 -m backend.app.mcp_server --transport stdio
```

Helper scripts:

```bash
bash scripts/start_mcp_server_stdio.sh
bash scripts/start_mcp_server_sse.sh
bash scripts/test_mcp_server_stdio.sh
```

The MCP Server uses Python MCP SDK / FastMCP. Install dependencies first:

```bash
pip install -r backend/requirements.txt
```

## MCP Tools

The MCP Server registers the following tools and reuses the existing KylinSafeOps Tool Registry, Tool Contract, policy guard, environment adapter, and audit persistence path:

| Tool | Purpose | Risk | Side Effect | Human Confirm | Shadow Execution |
| --- | --- | --- | --- | --- | --- |
| `systemctl_status` | Read systemd service state | readonly | false | false | false |
| `journalctl_unit` | Read bounded journal logs | readonly | false | false | false |
| `ss_listen` | Inspect listening TCP sockets | readonly | false | false | false |
| `netstat_listen` | Inspect listening TCP sockets | readonly | false | false | false |
| `lsof_port` | Find listening process owner | readonly | false | false | false |
| `ps_process` | Read process identity | readonly | false | false | false |
| `cpu_stat` | Read `/proc/stat` and loadavg | readonly | false | false | false |
| `memory_info` | Read `/proc/meminfo` | readonly | false | false | false |
| `disk_usage` | Read `df -h` for allowed mounts | readonly | false | false | false |
| `restart_service` | Guarded restart contract | medium | true | true | true |

All calls are persisted as audit/replay records through `persist_diagnosis_record`.

## MCP Resources

The MCP Server exposes system context as Resources:

| Resource | Purpose | Trust Level |
| --- | --- | --- |
| `os://release` | Read `/etc/os-release` | untrusted observation |
| `system://uname` | Read kernel and platform metadata | untrusted observation |
| `network://listen` | Read listening TCP sockets | untrusted observation |
| `process://list` | Read bounded process list | untrusted observation |
| `logs://journal/nginx` | Read nginx journal logs | untrusted observation |
| `disk://usage/root` | Read root disk usage | untrusted observation |
| `memory://info` | Read memory metrics | untrusted observation |
| `cpu://stat` | Read CPU metrics | untrusted observation |

Resource output is explicitly marked as untrusted observation data. It is not treated as instructions and is persisted into the same audit/replay chain.

## MCP Prompts

Minimal prompt templates:

| Prompt | Purpose |
| --- | --- |
| `nginx_start_failure_diagnosis` | Safe nginx failure diagnosis flow |
| `port_conflict_rca` | Port conflict root-cause workflow |
| `security_policy_review` | Risk and tool-policy review |
| `safe_remediation_plan` | Non-executing remediation planning |

## Safety Chain

Every MCP tool/resource path is routed through:

- Tool/resource registry resolution
- Parameter whitelist and service whitelist
- Sensitive path and shell composition filtering
- Side-effect blocking
- Human confirmation requirement for `restart_service`
- Shadow execution requirement marker
- Kylin/Linux real adapter selection
- Audit/replay persistence

For `restart_service`, direct execution is blocked by default unless `human_confirmed=true`. The expected competition demonstration is to show the block and the generated audit record.

## openKylin Real Mode

On openKylin, start the backend or MCP Server with:

```bash
export SAFEOPS_MODE=real
bash scripts/start_mcp_server_stdio.sh
```

Expected proof:

- `os://release` shows openKylin 2.0 SP2.
- `systemctl_status`, `journalctl_unit`, `ss_listen`, `lsof_port`, `ps_process`, `disk_usage`, `cpu_stat`, and `memory_info` return real system data.
- `restart_service` is blocked by default.
- Each call creates an audit/replay record under `data/audit` and `data/replay`.

## Remaining Non-Goals

- The B/S frontend does not depend on Cherry Studio, Cursor, or Claude Desktop.
- SSE depends on Python MCP SDK transport support in the installed version.
- Full plugin hot-unload/reload is a future enhancement; current tools are registered from the in-repository Tool Registry and Tool Contract.
