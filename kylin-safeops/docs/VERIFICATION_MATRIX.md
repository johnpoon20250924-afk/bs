# KylinSafeOps Final Verification Matrix

Scope: final QA validation only. No new features, no refactor, no UI beautification.

Important live-check note: during this QA pass, `curl.exe http://127.0.0.1:8000/health` returned connection refused from the shell. The matrix below is therefore based on repository inspection plus previously reported Windows validation results. Before competition, all P0 items must be re-run manually on the active backend process.

## Capability Status Matrix

| Capability | Status | API | Frontend | Evidence | Remaining Risk |
| --- | --- | --- | --- | --- | --- |
| Audit Export | Working | `GET /api/audit/{audit_id}/export` | Audit Center export buttons; diagnosis panel export button | `routes_audit.py` exports Markdown with `text/markdown; charset=utf-8`; `frontend/src/api/client.ts` calls `exportAuditMarkdown`; user reported audit/export passed on Windows | Requires a valid `audit_id`; final run should prove exported Markdown contains current audit, PlanSpec, tool trace, root cause |
| Replay | Working | `GET /api/replay/{replay_id}` | Diagnosis flow loads replay after `diagnose`; Audit Center can load replay from audit | `routes_replay.py` loads replay from `data/replay`; `persist_diagnosis_record` writes replay JSON; frontend calls `getReplay` after diagnosis and when opening linked audit | Needs explicit final human verification of direct replay API and UI timeline, because user report named audit/export but not replay separately |
| Red Team | Working | `POST /api/redteam/run` | Red Team Lab run button | `routes_redteam.py` calls `run_redteam_suite`; suite has 8 cases and persists audit; user reported redteam passed on Windows | Windows result is policy self-test, not openKylin real OS proof; final run should capture `passed=8`, `failed=0`, `audit_id` |
| MCP Tool Registry | Working | `GET /api/mcp/tools/list` and JSON-RPC `tools/list` | No dedicated full MCP page; API/manual curl evidence | `routes_mcp.py` exposes `/tools/list`; `tool_registry.py` returns names, schemas, risk, side-effect flags; user reported MCP passed | Needs final screenshot of full tool list; current API is MCP-compatible HTTP/JSON-RPC, not standalone stdio/SSE MCP server |
| MCP Tool Call | Working | `POST /api/mcp/tools/call` | No dedicated full MCP page; API/manual curl evidence | `routes_mcp.py` routes calls through gateway policy, Tool Contract, environment adapter, audit persistence; user reported MCP passed | Must re-test both readonly success and side-effect blocking before demo |
| MCP JSON-RPC | Working | `POST /api/mcp` | No dedicated frontend entry | `routes_mcp.py` supports `initialize`, `tools/list`, `tools/call`, error for unknown method | Needs explicit final curl screenshot; may not have been separately human-validated if "MCP" only covered REST endpoints |
| Environment Probe | Working | `GET /api/environment/probe` | Governance/settings environment section; dashboard summary also embeds environment | `routes_environment.py` returns `probe_environment`; environment code detects OS, systemd, tools, adapter, DeepSeek config; user reported environment passed on Windows | Windows expected mode is demo; openKylin must still prove `real`, `kylin-real-adapter`, `real_mode_ready=true` |
| Dashboard Summary | Partial | `GET /api/dashboard/summary`, `GET /api/dashboard/metrics` | Dashboard first screen and status cards | API exists and calls `probe_environment` plus `cpu_stat`, `memory_info`, `disk_usage`; frontend calls summary on load | Services and ports in summary are static examples; Windows metrics are demo unless real adapter is ready |
| Runtime Alerts | Partial | `GET /api/runtime/alerts`, `GET /api/runtime/status`, `POST /api/runtime/scan`, `POST /api/runtime/alerts/{event_id}/status` | Active alert card and Runtime Alert Center | `runtime/alerts.py` has scheduler, scan, event state, status update; frontend polls alerts and can link diagnosis | Windows/demo events are synthetic; real openKylin scheduler behavior and linked audit update need manual proof |
| Attack Surface | Partial | `GET /api/attack-surface` | Attack Surface map page; port click can trigger diagnosis | `routes_attack_surface.py` calls `get_attack_surface`; real mode parses `ss -lntp`; frontend normalizes and displays ports | Windows/demo returns sample surface; frontend can backfill demo ports if API data is sparse; openKylin real `ss` proof is required |
| Agent Diagnose | Working | `POST /api/agent/diagnose` | Agent diagnosis input; dashboard diagnosis flow; attack/runtime linked diagnosis | `routes_agent.py` calls `diagnose_system_issue`; diagnosis builds PlanSpec, runs tools, builds evidence graph/root cause, persists audit/replay; user reported diagnose passed | Windows is demo adapter unless real ready; final proof must show current backend live and generated `audit_id`/`replay_id` |
| Shadow Execution | Partial | `POST /api/shadow/preview` | Shadow Execution panel | `routes_shadow.py` calls `preview_restart_service`; preview validates `restart_service`, checks status/port, returns impact/rollback/requires_confirm | It is preview-only by design; no actual authorized execution or rollback verification exists |

## Detailed Capability Findings

### Audit Export

- Capability: Audit Export
- Status: Working
- Frontend Entry: Audit Center export button; diagnosis panel export button
- Backend API: `GET /api/audit/{audit_id}/export`
- Evidence: `routes_audit.py` returns Markdown via `export_audit_markdown`; response media type is `text/markdown; charset=utf-8`; frontend `exportAuditMarkdown` downloads text.
- Missing Pieces: Needs final manual export from a fresh audit generated during final demo.
- How to Verify Manually:
  1. Run Agent Diagnose or Red Team to generate an `audit_id`.
  2. Open Audit Center.
  3. Click `导出审计报告` or run the curl command in the P0 checklist.
  4. Expected: Markdown opens/downloads and contains PlanSpec, Tool Trace, Evidence, Root Cause.

### Replay

- Capability: Replay
- Status: Working
- Frontend Entry: diagnosis flow loads replay after diagnosis; Audit Center can load replay from selected audit
- Backend API: `GET /api/replay/{replay_id}`
- Evidence: `persist_diagnosis_record` writes `data/replay/{replay_id}.json`; `routes_replay.py` reads it; frontend calls `getReplay` after diagnose.
- Missing Pieces: Direct human validation of replay endpoint and visible timeline should be repeated.
- How to Verify Manually:
  1. Generate a diagnosis.
  2. Copy `replay_id`.
  3. Call `GET /api/replay/{replay_id}`.
  4. Expected: JSON includes replay id, audit chain/stages, and source diagnosis data.

### Red Team

- Capability: Red Team
- Status: Working
- Frontend Entry: Red Team Lab, run self-check button
- Backend API: `POST /api/redteam/run`
- Evidence: 8 explicit policy cases in `security/redteam.py`; route persists an audit record; user reported Windows validation passed.
- Missing Pieces: Final proof screenshot must show `8/8`, `failed=0`, audit id.
- How to Verify Manually:
  1. Open Red Team Lab.
  2. Click `运行自检` or equivalent run button.
  3. Expected: all cases pass and an audit record is generated.

### MCP Tool Registry

- Capability: MCP Tool Registry
- Status: Working
- Frontend Entry: no dedicated complete page; manual API verification
- Backend API: `GET /api/mcp/tools/list`
- Evidence: `tool_registry.py` lists tool metadata; `routes_mcp.py` exposes registry with environment.
- Missing Pieces: Final screenshot of tool schemas and side-effect flags.
- How to Verify Manually:
  1. Run `curl.exe http://127.0.0.1:8000/api/mcp/tools/list`.
  2. Expected: `protocol=mcp-compatible-jsonrpc`, `tools` array, names such as `journalctl_unit`, `lsof_port`, `restart_service`.

### MCP Tool Call

- Capability: MCP Tool Call
- Status: Working
- Frontend Entry: no dedicated complete page; manual API verification
- Backend API: `POST /api/mcp/tools/call`
- Evidence: tool calls pass through `_policy_gate`, `run_tool`, `security_chain`, and audit persistence.
- Missing Pieces: Final proof for one readonly success and one side-effect block.
- How to Verify Manually:
  1. Call `lsof_port` with port 80.
  2. Call `restart_service` without confirmation.
  3. Expected: readonly returns result and audit id; restart is blocked.

### MCP JSON-RPC

- Capability: MCP JSON-RPC
- Status: Working
- Frontend Entry: none
- Backend API: `POST /api/mcp`
- Evidence: JSON-RPC handler supports `initialize`, `tools/list`, `tools/call`.
- Missing Pieces: Human final screenshot likely still needed.
- How to Verify Manually:
  1. POST `{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}`.
  2. Expected: response has `jsonrpc`, `id`, `result.tools`.

### Environment Probe

- Capability: Environment Probe
- Status: Working
- Frontend Entry: Governance/settings environment panel; dashboard summary
- Backend API: `GET /api/environment/probe`
- Evidence: `probe_environment` checks OS, Kylin-like markers, systemd, tools, mode, adapter, blockers.
- Missing Pieces: openKylin real validation.
- How to Verify Manually:
  1. Call `/api/environment/probe`.
  2. On Windows expected: `effective_mode=demo`, `adapter=demo-adapter`.
  3. On openKylin expected: `effective_mode=real`, `adapter=kylin-real-adapter`, `real_mode_ready=true`.

### Dashboard Summary

- Capability: Dashboard Summary
- Status: Partial
- Frontend Entry: main dashboard
- Backend API: `GET /api/dashboard/summary`, `GET /api/dashboard/metrics`
- Evidence: endpoints exist; frontend calls summary on load; metrics call tool runner for CPU/memory/disk.
- Missing Pieces: service and port summary values are static examples; real resource metrics require openKylin.
- How to Verify Manually:
  1. Open dashboard URL.
  2. Call summary/metrics APIs.
  3. Expected: summary includes environment and system metrics; Windows may state demo source.

### Runtime Alerts

- Capability: Runtime Alerts
- Status: Partial
- Frontend Entry: Active alert card and Runtime Alert Center
- Backend API: `/api/runtime/alerts`, `/api/runtime/status`, `/api/runtime/scan`, `/api/runtime/alerts/{event_id}/status`
- Evidence: scheduler and alert state exist; frontend polls alerts and supports linked audit flow.
- Missing Pieces: real runtime scan on openKylin and manual update-status verification.
- How to Verify Manually:
  1. Open Runtime Alert Center.
  2. Call `POST /api/runtime/scan`.
  3. Expected: alerts list returns items and runtime metadata; demo mode returns synthetic events.

### Attack Surface

- Capability: Attack Surface
- Status: Partial
- Frontend Entry: Attack Surface map
- Backend API: `GET /api/attack-surface`
- Evidence: route exists; demo mode returns fixed surface; real mode runs `ss -lntp` and parses ports.
- Missing Pieces: openKylin real `ss` proof; frontend may supplement demo ports.
- How to Verify Manually:
  1. Open Attack Surface page.
  2. Call `/api/attack-surface`.
  3. Expected on Windows/demo: sample ports; expected on openKylin/real: ports from actual `ss`.

### Agent Diagnose

- Capability: Agent Diagnose
- Status: Working
- Frontend Entry: Agent diagnosis input and linked diagnosis buttons
- Backend API: `POST /api/agent/diagnose`
- Evidence: builds PlanSpec, validates intent, runs tools, scores hypotheses, builds evidence graph, persists audit/replay; user reported diagnose passed.
- Missing Pieces: final fresh run and openKylin real tool trace.
- How to Verify Manually:
  1. Submit nginx failure query.
  2. Expected: `status=completed`, PlanSpec, Tool Trace, Evidence Graph, Root Cause, `audit_id`, `replay_id`.

### Shadow Execution

- Capability: Shadow Execution
- Status: Partial
- Frontend Entry: Shadow Execution panel
- Backend API: `POST /api/shadow/preview`
- Evidence: preview validates restart contract, runs status/port checks, returns impact and rollback guidance.
- Missing Pieces: no real authorized execution; no post-action rollback validation.
- How to Verify Manually:
  1. Call preview for `nginx`.
  2. Expected: `requires_confirm=true`, impact list, rollback list, no real restart.

## Not Yet Manually Validated By Human

Based on the conversation and repository evidence, the following still need explicit final human validation or re-validation:

1. Backend liveness at final demo time (`/health`) because the current QA shell saw connection refused.
2. Replay direct API and visible replay/timeline behavior.
3. MCP JSON-RPC endpoint as a separate proof from REST MCP.
4. Runtime manual scan and alert status update.
5. Runtime alert to diagnosis to linked audit workflow.
6. Attack Surface API in final run and port click to diagnosis flow.
7. Shadow Execution preview in final run.
8. Dashboard summary and metrics API in final run.
9. All openKylin/KylinOS real-adapter behavior.
10. Non-root / restricted account operation.
11. Real nginx port-conflict fault chain.
12. Real `systemctl`, `journalctl`, `ss`, `netstat`, `lsof`, `ps`, `df`, `/proc/stat`, `/proc/meminfo` tool traces.

## Prioritized Final Checklist

### P0 = Must Verify Before Competition

#### P0-1 Backend liveness

Commands:

```powershell
cd C:\Users\AAA\bs\kylin-safeops
curl.exe http://127.0.0.1:8000/health
```

Expected result:

```json
{"status":"ok"}
```

Screenshot requirement: terminal output showing URL and JSON.

If failed: backend is not running, wrong port, or reload crashed. Restart using the existing backend script only if the validation owner approves.

#### P0-2 Environment Probe

Command:

```powershell
cd C:\Users\AAA\bs\kylin-safeops
curl.exe http://127.0.0.1:8000/api/environment/probe
```

Expected Windows result:

- `effective_mode` is `demo`
- `adapter` is `demo-adapter`
- `tools` object exists
- `capabilities` array exists
- `content-type` includes `application/json; charset=utf-8`

Expected openKylin result:

- `effective_mode=real`
- `adapter=kylin-real-adapter`
- `real_mode_ready=true`
- `is_kylin_like=true`

Frontend URL/button:

- Open `http://localhost:5173`
- Navigate to governance/settings environment section if needed.

Screenshot requirement: JSON output plus frontend environment panel.

#### P0-3 Agent Diagnose

Command:

```powershell
cd C:\Users\AAA\bs\kylin-safeops
curl.exe -X POST http://127.0.0.1:8000/api/agent/diagnose `
  -H "Content-Type: application/json" `
  -d "{\"query\":\"帮我看看 nginx 为什么启动失败\"}"
```

Expected result:

- `status=completed`
- `plan.steps` exists
- `tool_trace` exists
- `evidence_graph.nodes` exists
- `root_cause.summary` exists
- `audit_id` exists
- `replay_id` exists

Frontend URL/button:

- Open `http://localhost:5173`
- Use Agent input box.
- Click the diagnosis/generate button.

Screenshot requirement: PlanSpec, Tool Trace, Root Cause, Audit ID.

#### P0-4 Audit Export

Commands:

```powershell
cd C:\Users\AAA\bs\kylin-safeops
$auditId = "REPLACE_WITH_AUDIT_ID"
curl.exe http://127.0.0.1:8000/api/audit/$auditId/export
curl.exe http://127.0.0.1:8000/api/audit/$auditId/export -o ".\data\audit\$auditId.final.md"
```

Expected result:

- Markdown is readable Chinese.
- Contains audit title.
- Contains PlanSpec / Tool Trace / Root Cause sections or equivalents.

Frontend URL/button:

- Open Audit Center.
- Select the fresh audit.
- Click `导出审计报告`.

Screenshot requirement: exported Markdown preview or terminal output.

#### P0-5 Replay

Command:

```powershell
cd C:\Users\AAA\bs\kylin-safeops
$replayId = "REPLACE_WITH_REPLAY_ID"
curl.exe http://127.0.0.1:8000/api/replay/$replayId
```

Expected result:

- JSON loads successfully.
- Contains replay id and diagnosis/audit chain data.

Frontend URL/button:

- After diagnosis, verify replay/timeline section updates.

Screenshot requirement: replay JSON or visible replay timeline.

#### P0-6 Red Team

Command:

```powershell
cd C:\Users\AAA\bs\kylin-safeops
curl.exe -X POST http://127.0.0.1:8000/api/redteam/run
```

Expected result:

- `total_cases=8`
- `passed=8`
- `failed=0`
- `score=1.0`
- `audit_id` exists
- Cases include prompt injection, command injection, sensitive path, privileged service, intent drift, log injection, output poisoning.

Frontend URL/button:

- Open Red Team Lab.
- Click `运行自检` or the visible run button.

Screenshot requirement: Red Team score and case list.

#### P0-7 MCP Tool Registry

Command:

```powershell
cd C:\Users\AAA\bs\kylin-safeops
curl.exe http://127.0.0.1:8000/api/mcp/tools/list
```

Expected result:

- `protocol=mcp-compatible-jsonrpc`
- `tools` array exists
- Includes `journalctl_unit`, `lsof_port`, `restart_service`
- Tool metadata includes `risk`, `side_effect`, `requires_human_confirm`

Screenshot requirement: terminal output showing tool list.

#### P0-8 MCP Tool Call readonly success

Command:

```powershell
cd C:\Users\AAA\bs\kylin-safeops
curl.exe -X POST http://127.0.0.1:8000/api/mcp/tools/call `
  -H "Content-Type: application/json" `
  -d "{\"name\":\"lsof_port\",\"arguments\":{\"port\":80}}"
```

Expected result:

- `protocol=mcp-compatible-jsonrpc`
- `tool=lsof_port`
- `result` exists
- `security_chain` exists
- `audit_id` exists

Screenshot requirement: result summary and security chain.

#### P0-9 MCP side-effect block

Command:

```powershell
cd C:\Users\AAA\bs\kylin-safeops
curl.exe -X POST http://127.0.0.1:8000/api/mcp/tools/call `
  -H "Content-Type: application/json" `
  -d "{\"name\":\"restart_service\",\"arguments\":{\"service\":\"nginx\"}}"
```

Expected result:

- `ok=false`
- `risk=blocked`
- summary says side-effect tool requires human confirmation and shadow execution
- `security_chain` exists

Screenshot requirement: blocked result.

#### P0-10 MCP JSON-RPC

Command:

```powershell
cd C:\Users\AAA\bs\kylin-safeops
curl.exe -X POST http://127.0.0.1:8000/api/mcp `
  -H "Content-Type: application/json" `
  -d "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"tools/list\",\"params\":{}}"
```

Expected result:

- `jsonrpc=2.0`
- `id=1`
- `result.tools` exists

Screenshot requirement: JSON-RPC response.

#### P0-11 Shadow Execution

Command:

```powershell
cd C:\Users\AAA\bs\kylin-safeops
curl.exe -X POST http://127.0.0.1:8000/api/shadow/preview `
  -H "Content-Type: application/json" `
  -d "{\"service\":\"nginx\"}"
```

Expected result:

- `operation` references restart nginx
- `requires_confirm=true`
- `impact` list exists
- `rollback` list exists
- no real restart is executed

Frontend URL/button:

- Dashboard Shadow Execution panel.
- Confirm it shows preview/impact, not actual execution.

Screenshot requirement: Shadow panel or API output.

#### P0-12 Runtime Alerts

Commands:

```powershell
cd C:\Users\AAA\bs\kylin-safeops
curl.exe http://127.0.0.1:8000/api/runtime/alerts
curl.exe -X POST http://127.0.0.1:8000/api/runtime/scan
```

Expected result:

- `runtime` object exists
- `items` array exists
- `scheduler_state` exists
- `scan_count` changes after scan

Frontend URL/button:

- Open Runtime Alert Center.
- Click manual scan if exposed.
- Click an alert diagnosis action if available.

Screenshot requirement: runtime alert list and scan response.

#### P0-13 Attack Surface

Command:

```powershell
cd C:\Users\AAA\bs\kylin-safeops
curl.exe http://127.0.0.1:8000/api/attack-surface
```

Expected Windows result:

- `items` array exists
- demo ports may be present
- summary indicates demo if not real

Expected openKylin result:

- ports reflect real `ss -lntp` output

Frontend URL/button:

- Open Attack Surface page.
- Click a port, then trigger linked diagnosis.

Screenshot requirement: map, port list, selected port details.

#### P0-14 openKylin real adapter

Commands on openKylin:

```bash
cd kylin-safeops
bash scripts/kylin_preflight.sh
bash scripts/kylin_immutable_verify.sh
SAFEOPS_MODE=real bash scripts/start_backend_kylin.sh
```

Expected result:

- preflight report generated
- immutable verification report generated
- `/api/environment/probe` shows real mode and Kylin adapter
- diagnosis tool trace shows real OS commands

Screenshot requirement: terminal, probe JSON, tool trace, generated reports.

### P1 = Nice To Verify

1. Dashboard metrics API separately:
   - `curl.exe http://127.0.0.1:8000/api/dashboard/metrics`
2. Runtime alert status update:
   - `POST /api/runtime/alerts/{event_id}/status`
3. Attack Surface port-click linked diagnosis.
4. Audit Center refresh list after generating Red Team and Agent diagnosis audits.
5. JSON UTF-8 header:
   - `curl.exe -D - http://127.0.0.1:8000/api/environment/probe`
6. Frontend mobile-width screenshots if final deck includes responsive claims.

### P2 = Optional

1. Governance/settings sliders and toggles.
2. Cognitive graph static page.
3. Hypothesis simulation static page.
4. DeepSeek enabled path, unless a valid API key and network are guaranteed.
5. Long-run background scheduler stability.

## Final QA Assessment

- Strongest currently implemented capabilities: Agent Diagnose, Audit Export, Red Team, Environment Probe, MCP Registry/Call, Tool Contract, audit/replay persistence.
- Partial capabilities requiring careful wording: Dashboard Summary, Runtime Alerts, Attack Surface, Shadow Execution.
- Demo-only or static surfaces should not be presented as real implementation: cognitive graph page, hypothesis simulation page, most governance editor controls, default historical audit samples.
- Biggest competition risk: no fresh backend liveness at this QA pass and no openKylin real-adapter proof captured in this repository session.

