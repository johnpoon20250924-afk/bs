# openKylin 迁移验证材料包

本目录用于归档 KylinSafeOps 在 openKylin 2.0 SP2 国产操作系统环境中的真实运行验证材料。验证环境为 Windows 11 宿主机、Oracle VirtualBox 虚拟机、openKylin 2.0 SP2 (nile) 客体系统。

## 最终验证口径

- `8000`：真实故障现场端口，由 `kytensor` 占用，用于证明端口冲突存在。
- `8010`：KylinSafeOps 后端 API 端口。
- `5173`：KylinSafeOps 前端页面端口。
- `SAFEOPS_MODE=real`：启用 openKylin Real Mode 与 `kylin-real-adapter`。

## 验证结论

项目已在 openKylin 2.0 SP2 上完成部署与运行验证。系统能够识别 openKylin 环境，后端 API 在 `8010` 端口运行，前端页面在 `5173` 端口打开，并可对 `8000` 端口真实占用故障进行诊断。MCP stdio Server、MCP Tools/Resources/Prompts、安全策略拦截、Shadow Execution、Audit Export、Replay 与 RedTeam 自检均已形成证据链。

## 材料清单

| 文件 | 用途 |
| --- | --- |
| [kylin_migration_report.md](./kylin_migration_report.md) | 国产系统迁移验证报告 |
| [deployment_verification.md](./deployment_verification.md) | 部署验证说明文档 |
| [final_validation_report.md](./final_validation_report.md) | 最终 P0 验证报告 |
| [screenshot_index.md](./screenshot_index.md) | 截图证据索引与取舍说明 |
| [ppt_screenshot_notes.md](./ppt_screenshot_notes.md) | 答辩 PPT 可直接使用的截图说明文字 |
| [frontend_verification_notes.md](./frontend_verification_notes.md) | openKylin 前端页面与审计中心 UI 修复说明 |
| [screenshots/](./screenshots/) | 验证过程截图 |

## 截图目录结构

```text
docs/kylin_verification/
  README.md
  kylin_migration_report.md
  deployment_verification.md
  final_validation_report.md
  screenshot_index.md
  ppt_screenshot_notes.md
  frontend_verification_notes.md
  screenshots/
    00_system_identity/
    01_runtime_dependencies/
    02_preflight/
    03_backend_api_real_mode/
    04_frontend_openkylin/
    05_mcp_server_openkylin/
    06_final_p0/
```

## 关键证据

| 验证项 | 建议截图 |
| --- | --- |
| openKylin 系统版本 | `screenshots/00_system_identity/02_os_release_openkylin.png` |
| 运行依赖可用 | `screenshots/01_runtime_dependencies/01_runtime_versions.png` |
| 8000 故障现场 | `screenshots/06_final_p0/01_port_8000_kytensor.png` |
| 8010 后端监听 | `screenshots/06_final_p0/02_backend_8010_listening.png` |
| `/health` 正常 | `screenshots/06_final_p0/03_health_8010_ok.png` |
| Real Mode 与 kylin-real-adapter | `screenshots/06_final_p0/04_environment_probe_real.png` |
| Agent 诊断链路 | `screenshots/06_final_p0/05_agent_diagnose_port_conflict.png` |
| Audit Export | `screenshots/06_final_p0/06_audit_export_report.png` |
| RedTeam 安全自检 | `screenshots/06_final_p0/07_redteam_passed.png` |
| MCP stdio Server | `screenshots/06_final_p0/08_mcp_stdio_tools_resources_prompts.png` |
| 前端 Dashboard | `screenshots/06_final_p0/09_frontend_dashboard.png` |
| 前端 Attack Surface | `screenshots/06_final_p0/10_frontend_attack_surface.png` |
| 前端 Audit Center | `screenshots/06_final_p0/11_frontend_audit_center.png` |

## 注意事项

- 旧截图中若出现 `8010 address already in use`、`Python MCP SDK is not installed`、`ls: 无法访问` 等错误，不进入最终材料。
- 攻击面地图页面可用于展示可视化能力；若左下角出现 Demo 样例字样，答辩时不要把该页面单独作为 Real Mode 证明。
- 审计中心 UI 重叠问题已在前端样式层修复，最终材料应使用修复后的重新截图。

## 答辩推荐表述

KylinSafeOps 已在 openKylin 2.0 SP2 国产操作系统环境完成真实运行验证。系统将 `8000` 作为被占用的故障现场端口，将 `8010` 作为 SafeOps 后端服务端口，从而在不破坏故障现场的情况下完成诊断。系统能够识别 openKylin 平台，进入 Real Mode，启用 `kylin-real-adapter`，并通过 MCP Server、Policy Guard、Shadow Execution、Audit/Replay 和 RedTeam 自检形成完整安全运维证据链。
