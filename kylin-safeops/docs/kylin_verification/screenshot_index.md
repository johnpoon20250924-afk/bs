# 最终截图证据索引

建议将最终可用截图统一放入：

```text
docs/kylin_verification/screenshots/06_final_p0/
```

## 必放截图

| 序号 | 建议文件名 | 截图内容 | 合格标准 |
| --- | --- | --- | --- |
| 01 | `01_port_8000_kytensor.png` | `sudo ss -lntp \| grep :8000` | 显示 `kytensor` 占用 `127.0.0.1:8000` |
| 02 | `02_backend_8010_listening.png` | `sudo ss -lntp \| grep :8010` | 显示 `python`/`uvicorn` 监听 `0.0.0.0:8010` |
| 03 | `03_health_8010_ok.png` | `/health` | 返回 `{"status":"ok"}` |
| 04 | `04_environment_probe_real.png` | `/api/environment/probe` | 显示 `real`、`openKylin`、`kylin-real-adapter`、`real_ready=true` |
| 05 | `05_agent_diagnose_port_conflict.png` | `/api/agent/diagnose` 精简输出 | 显示 root cause、safety boundary、audit/replay |
| 06 | `06_audit_export_report.png` | `/api/audit/<audit_id>/export` | 显示执行环境、根因、Evidence Promotion、Safety Boundary、Audit Chain |
| 07 | `07_redteam_passed.png` | `/api/redteam/run` 精简输出 | 显示 `total_cases=8`、`passed=8`、`failed=0`、`block_rate=1.0` |
| 08 | `08_mcp_stdio_tools_resources_prompts.png` | `scripts/test_mcp_server_stdio.sh` | 显示 Tools、Resources、Prompts、`READ os://release`、`RESTART_BLOCKED` |
| 09 | `09_frontend_dashboard.png` | 运维驾驶舱 | 展示 Real 模式、诊断主线、态势核心图 |
| 10 | `10_frontend_attack_surface.png` | 攻击面地图 | 展示资产拓扑、暴露端口、风险分布 |
| 11 | `11_frontend_audit_center.png` | 审计中心 | 展示会话列表、详情、执行时间线、证据摘要、决策结论，且无重叠 |

## 不建议放入最终材料的截图

- 出现 `address already in use` 且指向 SafeOps 后端 `8010` 启动失败的截图。
- 出现 `Python MCP SDK is not installed` 的 MCP 截图。
- 出现 `ls: 无法访问`、命令拼接错误或 shell 报错的截图。
- 仅显示中间变量赋值、没有输出证据的截图。
- 右下角大面积红色“维护模式”标注遮挡核心内容的截图。

## PPT 使用建议

- 一页放系统环境：openKylin 版本、依赖、Real Mode。
- 一页放故障诊断：8000 被占用、Agent Diagnose、Shadow Execution。
- 一页放安全闭环：RedTeam、MCP stdio、Audit Export。
- 一页放前端展示：Dashboard、Attack Surface、Audit Center。
