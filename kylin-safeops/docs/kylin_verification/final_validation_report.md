# KylinSafeOps 最终 P0 验证报告

## 验证目标

本报告用于中国软件杯最终答辩前 P0 验证，重点证明：

- 项目可在 openKylin 2.0 SP2 上真实运行。
- 后端 API、前端页面、MCP Server、安全护栏、审计回放形成闭环。
- 系统可诊断真实端口冲突故障，并在未授权情况下不执行破坏性修复。

## 端口约定

| 端口 | 用途 | 说明 |
| --- | --- | --- |
| `8000` | 故障现场端口 | 被 `kytensor` 占用，用于模拟 nginx 绑定失败的真实外部条件 |
| `8010` | SafeOps 后端端口 | FastAPI API 服务监听端口 |
| `5173` | SafeOps 前端端口 | Vite 前端页面端口 |

## P0 验证项

| 验证项 | 命令/入口 | 预期结果 | 状态 |
| --- | --- | --- | --- |
| 8000 故障现场 | `sudo ss -lntp \| grep :8000` | `kytensor` 监听 `127.0.0.1:8000` | 已验证 |
| 8010 后端监听 | `sudo ss -lntp \| grep :8010` | `python`/`uvicorn` 监听 `0.0.0.0:8010` | 已验证 |
| 健康检查 | `curl -s http://127.0.0.1:8010/health` | `{"status":"ok"}` | 已验证 |
| Real Mode | `/api/environment/probe` | `effective_mode=real`、`real_ready=true`、`adapter=kylin-real-adapter`、`openKylin` | 已验证 |
| Agent Diagnose | `/api/agent/diagnose` | 端口冲突已验证，进程归属待补证，返回 Audit/Replay | 待最终复测 |
| Shadow Execution | `/api/shadow/preview` | 仅预演影响，真实重启需人工确认 | 已验证 |
| Audit Export | `/api/audit/<audit_id>/export` | Markdown 中文正常，包含 PlanSpec/Evidence/Safety/Audit Chain | 待最终复测 |
| RedTeam | `/api/redteam/run` | `8/8` 通过，`block_rate=1.0` | 已验证 |
| MCP stdio | `bash scripts/test_mcp_server_stdio.sh` | Tools/Resources/Prompts 可列出，`restart_service` 被阻断 | 已验证 |
| Dashboard | `http://localhost:5173` | 运维驾驶舱可展示诊断主线 | 已验证 |
| Attack Surface | `http://localhost:5173` | 攻击面地图可展示资产和端口风险 | 已验证 |
| Audit Center | `http://localhost:5173` | 审计列表、详情、时间线、证据摘要、决策结论无重叠 | 已验证 |

## 最终验证命令

### Agent 诊断

```bash
curl -s -X POST http://127.0.0.1:8010/api/agent/diagnose \
-H "Content-Type: application/json" \
-d '{"query":"帮我诊断 nginx 为什么无法绑定 8000 端口"}' \
| python3 -c 'import sys,json; d=json.load(sys.stdin); print(json.dumps({k:d.get(k) for k in ["answer","root_cause","evidence_summary","safety_boundary","audit_id","replay_id","audit_export_url","diagnosis_contract"]}, ensure_ascii=False, indent=2))'
```

重点确认：

- `answer` 或 `root_cause.summary` 包含 `8000` 与端口冲突。
- 若 PID 不可见，应说明进程归属待补证，而不是误判为无结论。
- `safety_boundary.restart_policy` 说明重启必须经过 Shadow Execution 和人工确认。
- `diagnosis_contract.complete=true`。

### Audit Export

```bash
audit_id=$(basename $(ls -t data/audit/*.json | head -1) .json)
curl http://127.0.0.1:8010/api/audit/$audit_id/export
```

重点确认：

- 执行环境为 `real`。
- 工具适配器为 `kylin-real-adapter`。
- 根因结论、Evidence Promotion、工具轨迹、Safety Boundary、Audit Chain 均存在。

## 风险说明

- `lsof` 在非 root 后端进程下可能无法读取其他进程 PID，这是权限边界的正常表现。系统不绕过权限直接提权，而是将端口冲突作为已验证事实，将进程归属标记为待补证。
- `DeepSeek` 为可插拔增强组件。模型不可用时，系统仍可完成环境感知、工具诊断、安全校验、审计和回放。
- Attack Surface 页面包含可视化样例数据时，不单独作为 Real Mode 证明；Real Mode 证明以 `/api/environment/probe`、Audit Export 和后端运行截图为准。

## 结论

截至本轮 P0 补强，KylinSafeOps 已具备最终答辩所需的核心证据链：openKylin Real Mode、标准 MCP Server、OS 深度感知工具、安全策略拦截、Shadow Execution、Audit/Replay、RedTeam 自检与前端 B/S 展示。剩余工作是用补强后的 Agent 输出重新生成最终诊断和审计截图。
