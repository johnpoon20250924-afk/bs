# 答辩 PPT 截图说明文字

以下文字可直接放入中国软件杯答辩 PPT。最终推荐截图位于 `docs/kylin_verification/screenshots/06_final_p0/`。

## 1. openKylin 系统环境证明

配图：

- `00_system_identity/02_os_release_openkylin.png`
- `00_system_identity/01_uname_kylin_kernel.png`

说明文字：

```text
项目部署于 openKylin 2.0 SP2 (nile) 国产操作系统环境。通过 /etc/os-release 和 uname 可确认运行环境为真实 openKylin 虚拟机，而非 Windows 本地环境或纯 Demo 环境。
```

## 2. 真实端口冲突故障现场

配图：

- `06_final_p0/01_port_8000_kytensor.png`

说明文字：

```text
验证环境中 8000 端口被 kytensor 进程占用，形成真实端口冲突现场。KylinSafeOps 不清理该进程，而是保留故障现场用于智能诊断，体现系统对真实 OS 上下文的感知能力。
```

## 3. SafeOps 后端服务独立运行

配图：

- `06_final_p0/02_backend_8010_listening.png`
- `06_final_p0/03_health_8010_ok.png`

说明文字：

```text
为避免破坏 8000 故障现场，SafeOps 后端服务监听 8010 端口。健康检查接口返回 {"status":"ok"}，证明 FastAPI 后端在 openKylin Real Mode 下正常运行。
```

## 4. Real Mode 与 kylin-real-adapter

配图：

- `06_final_p0/04_environment_probe_real.png`

说明文字：

```text
/api/environment/probe 显示 effective_mode=real、real_ready=true、adapter=kylin-real-adapter，并识别 os_release 为 openKylin，证明系统已进入国产系统真实适配模式。
```

## 5. Agent 智能诊断链路

配图：

- `06_final_p0/05_agent_diagnose_port_conflict.png`

说明文字：

```text
Agent 根据用户问题自动生成 PlanSpec，调用 ss、netstat、lsof、ps 等受控工具采集证据，并输出根因结论、安全边界、Audit ID 与 Replay ID。端口监听冲突被验证后，系统将进程归属缺失标记为待补证，而不是越权提权或直接执行修复。
```

## 6. Shadow Execution 与最小权限执行

配图：

- 可使用 Dashboard 中“影子执行”区域截图

说明文字：

```text
对于 restart_service 等有副作用操作，系统默认只进行 Shadow Execution 影响预演，不直接重启服务。真实修复必须经过人工确认，且不会在未授权情况下修改 nginx、systemd 或关键配置文件。
```

## 7. Audit Export 与 Replay

配图：

- `06_final_p0/06_audit_export_report.png`
- 前端 Audit Center 截图

说明文字：

```text
每次诊断都会持久化 Audit 与 Replay 记录，审计报告包含执行环境、PlanSpec、Evidence Promotion、工具轨迹、Safety Boundary、Audit Chain 与根因结论，支持赛后复盘和异常回溯。
```

## 8. 标准 MCP Server

配图：

- `06_final_p0/08_mcp_stdio_tools_resources_prompts.png`

说明文字：

```text
项目新增标准 MCP Server 入口，并通过 stdio MCP 客户端测试。截图显示 ListToolsRequest、ListResourcesRequest、ListPromptsRequest，能够列出 Tools、Resources、Prompts，读取 os://release，并阻断 restart_service 高风险工具调用，说明项目不是 REST API 模拟 MCP，而是具备标准 MCP Server 测试证据。
```

## 9. RedTeam 安全自检

配图：

- `06_final_p0/07_redteam_passed.png`

说明文字：

```text
RedTeam 自检覆盖提示词注入、命令拼接、工具滥用、敏感路径、高权限服务、目标漂移、日志污染和输出污染等 8 类风险样本。验证结果 8/8 通过，block_rate=1.0，证明安全护栏能够拦截高危意图。
```

## 10. B/S 前端展示

配图：

- `06_final_p0/09_frontend_dashboard.png`
- `06_final_p0/10_frontend_attack_surface.png`
- `06_final_p0/11_frontend_audit_center.png`

说明文字：

```text
项目自身保持 B/S 架构前端页面，不依赖 Cherry Studio、Cursor 等第三方 MCP 客户端作为交付前端。Dashboard 展示运维驾驶舱，Attack Surface 展示攻击面态势，Audit Center 展示审计会话、执行时间线、证据摘要与决策结论。
```

## 11. 最终答辩结论页

说明文字：

```text
KylinSafeOps 已在 openKylin 2.0 SP2 上完成真实运行验证。系统能够识别国产操作系统并进入 Real Mode，通过 MCP Server 封装 OS 运维工具与资源读取能力，通过 Policy Guard、Shadow Execution、Audit/Replay 和 RedTeam 自检建立安全闭环。项目核心能力不依赖外部大模型；DeepSeek 仅作为可插拔增强组件，用于诊断解释、修复建议和认知审查。
```
