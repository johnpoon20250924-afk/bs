# KylinSafeOps 最终验证清单

本文用于比赛前最后一轮验收。当前演示策略：

- 故障目标端口：`8000`，保留为被 `kytensor` 占用的真实端口冲突现场。
- 后端 API 端口：`8010`，用于 SafeOps 服务自身运行。
- 修复动作：不真实执行，只展示 `Shadow Execution + requires_confirm + restart_service blocked`
- DeepSeek：作为可插拔增强，用于诊断解释、修复建议生成、认知审查；核心能力不依赖外部模型

## P0 必须验证

| 项目 | 命令或入口 | 预期结果 | 截图要求 |
| --- | --- | --- | --- |
| openKylin 系统身份 | `cat /etc/os-release` | `NAME="openKylin"`、`VERSION="2.0 SP2 (nile)"` | 必须 |
| 非 root 运行 | `whoami`；`ps -eo user,pid,cmd \| grep "uvicorn\|mcp_server"` | 用户为普通用户，例如 `wrg` | 必须 |
| 后端健康 | `curl http://127.0.0.1:8010/health` | `{"status":"ok"}` | 必须 |
| Real Mode | `curl http://127.0.0.1:8010/api/environment/probe` | `effective_mode=real`、`adapter=kylin-real-adapter`、`real_ready=true` | 必须 |
| 标准 MCP stdio | `bash scripts/test_mcp_server_stdio.sh` | 出现 `ListToolsRequest`、`ListResourcesRequest`、`ListPromptsRequest`、`RESTART_BLOCKED` | 必须 |
| MCP Resource Read | `/api/mcp/resources/read` 读取 `network://listen`、`process://list`、`memory://info`、`cpu://stat` | 返回真实命令或 `/proc` 数据，包含 audit/replay id | 必须 |
| Agent Diagnose | `POST /api/agent/diagnose`，问题包含 `nginx` 和 `8000` | 返回 PlanSpec、Knowledge State、Hypotheses、Tool Trace、Evidence Graph、Audit/Replay | 必须 |
| Shadow Execution | `POST /api/shadow/preview`，`{"service":"nginx","port":8000}` | `requires_confirm=true`，未执行真实重启 | 必须 |
| 高危动作阻断 | `POST /api/mcp/tools/call` 调用 `restart_service` | `ok=false`，summary 指出需要人工确认和影子执行 | 必须 |
| RedTeam | `curl -X POST http://127.0.0.1:8010/api/redteam/run` | `total_cases=8`、`failed=0`、`block_rate=1.0` | 必须 |
| Audit Export | `curl http://127.0.0.1:8010/api/audit/<audit_id>/export` | Markdown 中文正常，含 Evidence Promotion、Safety Boundary、DeepSeek 可插拔增强 | 必须 |
| 前端审计中心 | openKylin Firefox 打开 `http://localhost:5173`，进入审计中心 | 无重叠，审计会话和详情可读 | 必须 |

## P1 强烈建议

| 项目 | 预期价值 |
| --- | --- |
| DeepSeek 开启前后对比 | 展示 DeepSeek 是增强组件，不是系统依赖 |
| 8000 端口冲突诊断截图 | 展示真实端口占用、进程归属和反事实建议 |
| MCP 客户端配置说明 | Cherry Studio/Cursor 只是测试客户端，不是参赛交付物 |

## P2 可放弃

| 项目 | 原因 |
| --- | --- |
| SSE/streamable-http MCP 展示 | stdio 已满足标准 MCP Server 主证据 |
| 真实 restart_service 执行 | 安全风险高，当前比赛策略是默认阻断 |
| 多服务自动修复 | 容易分散主线，保留为后续路线图 |


