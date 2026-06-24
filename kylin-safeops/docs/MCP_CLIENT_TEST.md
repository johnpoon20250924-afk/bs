# MCP Client Test Guide

This document explains how to test the KylinSafeOps MCP Server with external MCP clients.

Important: Cherry Studio, Cursor, Claude Desktop, and other MCP clients are only test clients. They are not competition deliverables and are not required for the KylinSafeOps B/S frontend to run.

## 1. Prepare Dependencies

From the project root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

For openKylin real-mode verification:

```bash
export SAFEOPS_MODE=real
```

For local Windows/Linux demo-mode verification:

```bash
export SAFEOPS_MODE=demo
```

## 2. Start MCP Server With stdio

```bash
bash scripts/start_mcp_server_stdio.sh
```

Equivalent command:

```bash
python3 -m backend.app.mcp_server --transport stdio
```

## 3. Smoke Test With Bundled Script

```bash
bash scripts/test_mcp_server_stdio.sh
```

Expected output:

- Tool list includes `systemctl_status`, `journalctl_unit`, `ss_listen`, `lsof_port`, `ps_process`, `restart_service`.
- Resource list includes `os://release`, `network://listen`, `logs://journal/nginx`, `cpu://stat`, `memory://info`.
- Prompt list includes `nginx_start_failure_diagnosis`, `port_conflict_rca`, `security_policy_review`, `safe_remediation_plan`.
- `restart_service` returns a blocked/safe response unless human confirmation is explicitly provided.

## 4. Cherry Studio Test

Add a custom MCP Server:

```json
{
  "name": "kylin-safeops-mcp",
  "command": "python3",
  "args": [
    "-m",
    "backend.app.mcp_server",
    "--transport",
    "stdio"
  ],
  "env": {
    "SAFEOPS_MODE": "real"
  }
}
```

Set the working directory to the project root if the client supports it. If not, use an absolute module path strategy or wrap the command with `bash scripts/start_mcp_server_stdio.sh`.

Manual checks:

1. List tools.
2. Read resource `os://release`.
3. Read resource `network://listen`.
4. Call tool `journalctl_unit` with `{"unit":"nginx","lines":80}`.
5. Call tool `restart_service` with `{"service":"nginx"}` and confirm it is blocked.

## 5. Cursor Test

Example MCP configuration:

```json
{
  "mcpServers": {
    "kylin-safeops": {
      "command": "python3",
      "args": [
        "-m",
        "backend.app.mcp_server",
        "--transport",
        "stdio"
      ],
      "env": {
        "SAFEOPS_MODE": "real"
      }
    }
  }
}
```

Expected client-visible capabilities:

- Tools: systemd, journal, network, process, resource metrics, and guarded restart.
- Resources: OS release, uname, logs, process list, network listens, CPU/memory/disk.
- Prompts: nginx diagnosis, port conflict RCA, policy review, remediation plan.

## 6. Claude Desktop Test

Example `claude_desktop_config.json` entry:

```json
{
  "mcpServers": {
    "kylin-safeops": {
      "command": "python3",
      "args": [
        "-m",
        "backend.app.mcp_server",
        "--transport",
        "stdio"
      ],
      "env": {
        "SAFEOPS_MODE": "real"
      }
    }
  }
}
```

Use absolute paths if Claude Desktop is launched outside the project directory.

## 7. Optional SSE Test

If the installed Python MCP SDK supports SSE transport:

```bash
bash scripts/start_mcp_server_sse.sh
```

SSE support is optional for the competition hardening. The required local validation path is stdio.

## 8. Evidence To Capture

For final competition material, capture:

- MCP client tool list.
- MCP client resource list.
- `os://release` showing openKylin.
- `journalctl_unit`, `ss_listen`, `lsof_port`, `ps_process` calls.
- `restart_service` blocked result.
- Generated audit/replay files after MCP calls.
- B/S frontend still running independently at `http://localhost:5173`.
