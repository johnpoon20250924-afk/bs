# KylinSafeOps 最终答辩演示脚本

建议总时长：6 到 7 分钟。

端口约定：后端 API 监听 `8010`；`8000` 保留为被 `kytensor` 占用的诊断目标端口，用于展示真实端口冲突。

## 0:00 - 0:40 项目定位

讲法：

> KylinSafeOps 解决的不是“让大模型随便执行命令”，而是让运维 Agent 在 openKylin 上以可验证、可审计、可回放的方式完成系统感知、根因分析和安全决策。

展示：

- openKylin `/etc/os-release`
- 后端 `SAFEOPS_MODE=real`
- 前端驾驶舱首页

## 0:40 - 1:40 标准 MCP Server

命令：

```bash
cd /media/sf_bs/kylin-safeops
source ~/safeops-venv/bin/activate
bash scripts/test_mcp_server_stdio.sh
```

讲法：

> 这里不是 REST 模拟。测试脚本通过 Python MCP SDK 作为 stdio 客户端连接我们自主实现的 MCP Server，可以看到标准请求类型：ListToolsRequest、ListResourcesRequest、ListPromptsRequest。

必须展示：

- Tools：systemctl、journalctl、ss、netstat、lsof、ps、cpu、memory、disk、restart
- Resources：os、uname、network、process、logs、disk、memory、cpu
- Prompts：nginx diagnosis、port conflict RCA、policy review、safe remediation
- `restart_service` 被阻断

## 1:40 - 3:10 Agent 诊断主线

命令：

```bash
curl -X POST http://127.0.0.1:8010/api/agent/diagnose \
  -H "Content-Type: application/json" \
  -d '{"query":"帮我诊断 nginx 为什么无法绑定 8000 端口"}'
```

讲法：

> Agent 先生成 PlanSpec，再通过 Tool Contract 调用只读工具，工具输出只能作为不可信观察数据。只有经过解析和规则校验后，证据才会从 Observed 升级为 Verified。

重点指出：

- `plan`
- `knowledge_state`
- `evidence_promotion`
- `hypotheses`
- `tool_trace`
- `evidence_graph`
- `audit_id` / `replay_id`

## 3:10 - 4:10 Shadow Execution 与安全阻断

命令：

```bash
curl -X POST http://127.0.0.1:8010/api/shadow/preview \
  -H "Content-Type: application/json" \
  -d '{"service":"nginx","port":8000}'
```

```bash
curl -X POST http://127.0.0.1:8010/api/mcp/tools/call \
  -H "Content-Type: application/json" \
  -d '{"name":"restart_service","arguments":{"service":"nginx"}}'
```

讲法：

> 系统可以预演重启影响，但默认不真实执行。restart_service 属于有副作用工具，必须先经过影子执行和人工确认；未确认时策略层直接阻断。

## 4:10 - 5:10 RedTeam 与抗注入

命令：

```bash
curl -X POST http://127.0.0.1:8010/api/redteam/run
```

讲法：

> RedTeam 覆盖提示词注入、命令拼接、敏感路径、未授权工具、高危服务、日志污染、输出污染和目标漂移。8 个用例全部通过，说明安全护栏不是只在页面展示。

## 5:10 - 6:20 审计、回放、报告导出

命令：

```bash
audit_id=<替换为上一步返回的 audit_id>
curl http://127.0.0.1:8010/api/audit/$audit_id/export
```

讲法：

> 审计报告完整记录用户输入、环境感知、PlanSpec、工具轨迹、Evidence Promotion、认知审查、Safety Boundary 和最终根因，支持赛后回溯。

## 6:20 - 7:00 DeepSeek 可插拔增强

讲法：

> DeepSeek 在本项目中是 Critic，不是执行器。它用于诊断解释、修复建议生成和认知审查；它不能直接执行命令，不能绕过 Tool Contract。即使 DeepSeek 不可用，系统仍可通过规则兜底完成感知、诊断、安全校验、审计和回放。


