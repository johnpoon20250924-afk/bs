# KylinSafeOps openKylin 迁移验证报告

## 1. 报告结论

KylinSafeOps 已在 openKylin 2.0 SP2 (nile) 国产操作系统环境完成真实运行验证。验证结果表明：

- 项目可在 openKylin 环境中完成运行依赖检查。
- FastAPI 后端可在 openKylin 上以 `SAFEOPS_MODE=real` 启动。
- 系统能够正确识别 openKylin，并启用 `kylin-real-adapter`。
- `/health` 与 `/api/environment/probe` 接口响应正常。
- 前端可在 openKylin 桌面浏览器中通过 `http://localhost:5173` 打开核心页面。
- 标准 MCP stdio Server 可列出 Tools、Resources、Prompts，并对高危 `restart_service` 调用进行阻断。
- Agent 可针对 `8000` 端口真实占用故障完成受控诊断，并生成 Audit/Replay。

因此，项目具备国产 Linux 操作系统兼容能力、迁移能力和端到端演示能力。

## 2. 验证环境

| 项目 | 内容 |
| --- | --- |
| 宿主机 | Windows 11 |
| 虚拟化平台 | Oracle VirtualBox |
| 国产操作系统 | openKylin 2.0 SP2 (nile) |
| 内核信息 | Linux 6.6.0-19-generic x86_64 |
| 项目目录 | `/media/sf_bs/kylin-safeops` |
| 故障目标端口 | `8000`，由 `kytensor` 占用 |
| 后端 API 端口 | `8010` |
| 前端端口 | `5173` |
| 运行模式 | `SAFEOPS_MODE=real` |

## 3. 系统识别验证

```bash
uname -a
cat /etc/os-release
```

关键结果：

```text
NAME="openKylin"
PRETTY_NAME="openKylin 2.0 SP2"
VERSION="2.0 SP2 (nile)"
ID=openkylin
VERSION_CODENAME=nile
```

证据截图：

- `screenshots/00_system_identity/01_uname_kylin_kernel.png`
- `screenshots/00_system_identity/02_os_release_openkylin.png`

## 4. 运行依赖验证

```bash
git --version
node -v
npm -v
python3 --version
```

关键结果：

```text
git version 2.43.0
node v18.19.1
npm 9.2.0
Python 3.12.2
```

## 5. 故障现场与后端启动

故障现场：

```bash
sudo ss -lntp | grep :8000
```

预期结果显示 `kytensor` 监听 `127.0.0.1:8000`。

后端启动：

```bash
cd /media/sf_bs/kylin-safeops
source ~/safeops-venv/bin/activate
SAFEOPS_MODE=real BACKEND_PORT=8010 bash scripts/start_backend_kylin.sh
```

后端监听验证：

```bash
sudo ss -lntp | grep :8010
```

预期结果显示 `python`/`uvicorn` 监听 `0.0.0.0:8010`。

## 6. API 验证

健康检查：

```bash
curl -s http://127.0.0.1:8010/health; echo
```

预期结果：

```json
{"status":"ok"}
```

环境探测：

```bash
curl -s http://127.0.0.1:8010/api/environment/probe | grep -E "effective_mode|openKylin|kylin-real-adapter|real_ready"
```

关键字段：

- `configured_mode=real`
- `effective_mode=real`
- `real_ready=true`
- `adapter=kylin-real-adapter`
- `os_release.name=openKylin`

## 7. Agent 与安全闭环验证

Agent 诊断：

```bash
curl -s -X POST http://127.0.0.1:8010/api/agent/diagnose \
-H "Content-Type: application/json" \
-d '{"query":"帮我诊断 nginx 为什么无法绑定 8000 端口"}'
```

验证重点：

- 自动生成 PlanSpec。
- 调用 `ss_listen`、`netstat_listen`、`lsof_port`、`ps_process` 等受控工具。
- 端口监听冲突被验证后，若 PID 不可见，则标记“进程归属待补证”。
- 不直接执行 `restart_service`。
- 返回 `audit_id`、`replay_id` 和审计导出地址。

安全闭环：

- Shadow Execution 只预演影响，不真实重启。
- RedTeam 自检 8/8 通过。
- Audit Export 输出 Markdown 审计报告。
- Replay 记录推理、工具调用、证据和结论。

## 8. MCP Server 验证

```bash
source ~/safeops-venv/bin/activate
bash scripts/test_mcp_server_stdio.sh
```

预期输出：

- `ListToolsRequest`
- `ListResourcesRequest`
- `ListPromptsRequest`
- Tools 包含 `systemctl_status`、`journalctl_unit`、`ss_listen`、`netstat_listen`、`lsof_port`、`ps_process` 等。
- Resources 包含 `os://release`、`system://uname`、`network://listen`、`process://list` 等。
- Prompts 包含 `nginx_start_failure_diagnosis`、`port_conflict_rca` 等。
- `restart_service` 被策略阻断。

## 9. 前端页面验证

验证地址：

```text
http://localhost:5173
```

验证结果：

| 页面 | 结果 | 说明 |
| --- | --- | --- |
| 运维驾驶舱 | 通过 | 展示诊断主线、证据图谱、Shadow Execution、认知审查 |
| 攻击面地图 | 通过 | 展示资产拓扑、暴露端口、风险分布 |
| 审计中心 | 通过 | UI 重叠问题已修复，展示审计列表、详情、时间线、证据和决策结论 |

## 10. 验收项对齐

| 验收项 | 结果 | 证据 |
| --- | --- | --- |
| 国产操作系统识别 | 通过 | `/etc/os-release` 显示 openKylin 2.0 SP2 |
| systemd 环境识别 | 通过 | `PID 1: systemd`，必要工具可用 |
| 后端启动 | 通过 | `8010` 端口监听 |
| 健康检查 | 通过 | `/health` 返回 `{"status":"ok"}` |
| Real Mode | 通过 | `effective_mode=real` |
| Kylin Real Adapter | 通过 | `adapter=kylin-real-adapter` |
| OS 上下文采集 | 通过 | `ss`、`netstat`、`lsof`、`ps`、`/proc` 工具链 |
| MCP Server | 通过 | stdio 客户端列出 Tools/Resources/Prompts |
| 安全护栏 | 通过 | RedTeam 8/8，通过策略阻断高危操作 |
| 审计回放 | 通过 | Audit Export 与 Replay 持久化 |
| 前端页面访问 | 通过 | openKylin 浏览器打开 `localhost:5173` |

## 11. 最终结论

本项目已在 openKylin 2.0 SP2 国产操作系统环境完成部署与运行验证。系统能够正确识别 openKylin 平台，后端服务正常启动，API 接口响应正常，并成功进入 Real Mode，启用 `kylin-real-adapter`。同时，系统具备标准 MCP Server 入口、安全策略拦截、Shadow Execution、Audit/Replay 和 B/S 前端展示能力，满足赛题对 openKylin 智能运维安全平台的核心要求。
