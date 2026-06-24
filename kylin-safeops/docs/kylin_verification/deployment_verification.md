# openKylin 部署验证说明

本文档记录 KylinSafeOps 在 openKylin 2.0 SP2 环境中的最终部署与验证步骤，可用于复现实机或虚拟机验收。

## 1. 验证环境

| 项目 | 内容 |
| --- | --- |
| 宿主机 | Windows 11 |
| 虚拟化平台 | Oracle VirtualBox |
| 客体系统 | openKylin 2.0 SP2 (nile) |
| 故障目标端口 | `8000`，由 `kytensor` 占用，用于真实端口冲突诊断 |
| SafeOps 后端端口 | `8010` |
| SafeOps 前端端口 | `5173` |
| 后端模式 | `SAFEOPS_MODE=real` |

## 2. 端口口径

最终演示采用“双端口”口径：

- `8000`：保留为故障现场端口，证明系统面对真实端口占用。
- `8010`：SafeOps 后端 API 服务端口，避免破坏故障现场。
- `5173`：Vite 前端页面端口。

故障现场验证：

```bash
sudo ss -lntp | grep :8000
```

预期看到 `127.0.0.1:8000` 与 `kytensor` 进程。

## 3. 系统与依赖检查

```bash
cat /etc/os-release
uname -a
git --version
node -v
npm -v
python3 --version
```

预期结果：

- `/etc/os-release` 显示 `NAME="openKylin"`。
- `PRETTY_NAME` 显示 `openKylin 2.0 SP2`。
- Python、Node.js、npm、git 均可执行。

## 4. 后端启动

在项目根目录执行：

```bash
cd /media/sf_bs/kylin-safeops
source ~/safeops-venv/bin/activate
SAFEOPS_MODE=real BACKEND_PORT=8010 bash scripts/start_backend_kylin.sh
```

预期结果：

```text
Uvicorn running on http://0.0.0.0:8010
```

如后端已在运行，可用以下命令验证监听：

```bash
sudo ss -lntp | grep :8010
```

预期看到 `0.0.0.0:8010` 与 `python`/`uvicorn` 进程。

## 5. API 验证

健康检查：

```bash
curl -s http://127.0.0.1:8010/health; echo
```

预期输出：

```json
{"status":"ok"}
```

环境探测：

```bash
curl -s http://127.0.0.1:8010/api/environment/probe | grep -E "effective_mode|openKylin|kylin-real-adapter|real_ready"
```

预期关键字段：

- `effective_mode` 为 `real`
- `real_ready` 为 `true`
- `adapter` 为 `kylin-real-adapter`
- `os_release.name` 为 `openKylin`

## 6. Agent 诊断验证

```bash
curl -s -X POST http://127.0.0.1:8010/api/agent/diagnose \
-H "Content-Type: application/json" \
-d '{"query":"帮我诊断 nginx 为什么无法绑定 8000 端口"}' \
| python3 -c 'import sys,json; d=json.load(sys.stdin); print(json.dumps({k:d.get(k) for k in ["answer","root_cause","evidence_summary","safety_boundary","audit_id","replay_id","audit_export_url","diagnosis_contract"]}, ensure_ascii=False, indent=2))'
```

预期重点：

- 根因指出 `8000` 端口监听冲突已验证。
- 若非 root 采集不到 PID，结果应标记“进程归属待补证”，而不是直接执行修复。
- `safety_boundary` 明确真实修复默认关闭，`restart_service` 必须经过 Shadow Execution 与人工确认。
- 返回 `audit_id`、`replay_id`、`audit_export_url`。

## 7. Shadow / Audit / RedTeam / MCP

Shadow Execution：

```bash
curl -s -X POST http://127.0.0.1:8010/api/shadow/preview \
-H "Content-Type: application/json" \
-d '{"service":"nginx","port":8000}'
```

Audit Export：

```bash
audit_id=$(basename $(ls -t data/audit/*.json | head -1) .json)
curl http://127.0.0.1:8010/api/audit/$audit_id/export
```

RedTeam：

```bash
curl -s -X POST http://127.0.0.1:8010/api/redteam/run \
| python3 -c 'import sys,json; d=json.load(sys.stdin); print(json.dumps({k:d[k] for k in ["total_cases","passed","failed","score","blocked","allowed","block_rate"]}, ensure_ascii=False, indent=2))'
```

MCP stdio：

```bash
source ~/safeops-venv/bin/activate
bash scripts/test_mcp_server_stdio.sh
```

MCP 预期看到：

- `ListToolsRequest`
- `ListResourcesRequest`
- `ListPromptsRequest`
- `READ os://release`
- `RESTART_BLOCKED`

## 8. 前端验证

```bash
BACKEND_PORT=8010 bash scripts/start_frontend_kylin.sh
```

打开 openKylin 桌面浏览器：

```text
http://localhost:5173
```

最终截图页面：

- 运维驾驶舱
- 攻击面地图
- 审计中心

审计中心 UI 重叠问题已修复，最终截图需证明“执行时间线”“证据摘要”“决策与结论”与上方会话列表/详情区域不重叠。

## 9. 验证完成清单

| 项目 | 状态 |
| --- | --- |
| openKylin 系统识别 | 通过 |
| 运行依赖检查 | 通过 |
| 8000 故障现场 | 通过 |
| 8010 后端监听 | 通过 |
| `/health` | 通过 |
| `/api/environment/probe` | 通过 |
| Real Mode | 通过 |
| Kylin Real Adapter | 通过 |
| Agent Diagnose | 待最终截图 |
| Shadow Execution | 待最终截图 |
| Audit Export | 待最终截图 |
| RedTeam | 通过 |
| MCP stdio | 通过 |
| 前端页面打开 | 通过 |
| 审计中心 openKylin 布局 | 已修复，待最终截图 |
