# KylinSafeOps 决赛前路线图

本文档只规划收尾工作，不新增功能范围。排序按对获奖影响从高到低排列。

## P0（必须完成）

### 1. openKylin / KylinOS 实机验证

影响：最高。没有实机证据，项目很容易被判定为 Windows Demo。

必须完成：

- 在 openKylin/KylinOS 中运行项目或至少运行底层验证脚本。
- 截图 `/etc/os-release`，证明系统环境。
- 截图 `/api/environment/probe`，证明：
  - `is_linux=true`
  - `is_kylin_like=true`
  - `has_systemd=true`
  - `effective_mode=real`
  - `adapter=kylin-real-adapter`
  - `real_mode_ready=true`
- 运行并保存：
  - `data/kylin_preflight_report.md`
  - `data/kylin_immutable_verify_report.md`
- 若 openKylin immutable 机制阻止安装依赖，必须保留无安装验证路径的终端输出和报告。

验收产物：

- 实机截图包。
- 实机验证报告。
- 1 段 1-2 分钟录屏。

### 2. 真实工具链诊断录屏

影响：最高。赛题明确要求 OS 深度感知和底层工具调用。

必须完成：

- 在 real 模式下触发一次 nginx 故障诊断。
- Tool Trace 中必须出现真实工具调用：
  - `systemctl`
  - `journalctl`
  - `ss`
  - `netstat`
  - `lsof`
  - `ps`
  - `df`
  - `/proc/stat`
  - `/proc/meminfo`
- 证明不是 demo PID 1234/httpd 的固定样例。

验收产物：

- 前端诊断页面截图。
- API JSON 截图。
- 审计报告 Markdown。
- 工具轨迹录屏。

### 3. nginx 端口冲突真实故障闭环

影响：极高。当前最完整的根因链路就是 nginx 端口冲突，需要把它做成主演示。

必须完成：

- 在 openKylin/KylinOS 中制造 apache/nginx 80 端口冲突。
- 输入“帮我看看 nginx 为什么启动失败”。
- 展示完整链路：
  - PlanSpec
  - Tool Trace
  - Evidence Graph
  - Root Cause
  - Audit ID
  - Replay ID
  - Audit Markdown export
- 根因结论必须能定位到端口冲突和占用进程。

验收产物：

- 完整演示录屏。
- 导出的审计报告。
- 截图：PlanSpec、Tool Trace、Root Cause、Audit Center。

### 4. 安全拦截与最小权限证明

影响：极高。赛题强调安全意图校验、最小权限、未授权不修改关键配置。

必须完成：

- 证明自动诊断只执行只读工具。
- 调用 `restart_service`，未授权时必须被拦截。
- 展示 Shadow Execution 只做预览，不实际重启服务。
- 展示非 root 或受限账户运行证据：
  - `whoami`
  - 服务启动终端
  - 只读工具仍可运行
- 展示关键配置文件没有被自动修改。

验收产物：

- MCP 高危动作拦截图。
- Shadow Execution 截图。
- 非 root 运行截图。
- 配置文件未修改证明。

### 5. Red Team 自检与抗注入证据

影响：高。能直接回应抗注入和安全规则库要求。

必须完成：

- 运行 `/api/redteam/run`。
- 确认：
  - `total_cases=8`
  - `passed=8`
  - `failed=0`
- 展示用例：
  - prompt injection
  - command injection
  - sensitive path
  - privileged service
  - intent drift
  - log prompt injection
  - output poisoning
- 展示 Red Team 审计报告进入审计中心。

验收产物：

- Red Team 页面截图。
- API 输出截图。
- Red Team 审计报告导出。

### 6. MCP-style 工具接口演示材料

影响：高。赛题要求插件化运维 Tools。

必须完成：

- 演示：
  - `/api/mcp/tools/list`
  - `/api/mcp/tools/call`
  - `/api/mcp` JSON-RPC
- 展示工具字段：
  - `name`
  - `inputSchema`
  - `risk`
  - `side_effect`
  - `requires_human_confirm`
  - `requires_shadow_execution`
- 展示调用链：
  - tool registry
  - MCP gateway policy
  - tool contract
  - environment adapter
  - execution result
  - audit record

验收产物：

- PowerShell curl 输出截图。
- MCP 调用生成的审计记录。
- 答辩时说明当前是 MCP-compatible HTTP/JSON-RPC 接口。

### 7. Demo / Real 边界说明

影响：高。边界讲不清会严重扣分。

必须完成：

- 使用已有文档：
  - `docs/PROJECT_STATUS.md`
  - `docs/VERIFICATION_MATRIX.md`
- 答辩明确说明：
  - Windows 用于本地联调和演示。
  - openKylin/KylinOS 用于 real adapter 实机验收。
  - demo adapter 是可控样例，不冒充真实系统。
- 前端截图时优先展示 `mode`、`adapter`、`metrics_source`。

验收产物：

- 答辩讲稿中的 Demo/Real 边界页。
- 一页验证矩阵截图。

### 8. 最终提交材料整理

影响：高。材料不完整会抵消技术实现。

必须完成：

- README 更新最终运行方式。
- openKylin 部署说明可照着执行。
- 截图命名规范。
- 录屏按演示顺序编号。
- 审计报告和验证报告归档。

建议目录：

```text
final_artifacts/
  screenshots/
  videos/
  reports/
  api_outputs/
```

## P1（加分项）

### 1. 标准 MCP Server 包装层

影响：中高。能把 MCP-compatible 升级为更正统的 MCP 叙事。

可做内容：

- 保留当前 `/api/mcp`。
- 新增 stdio 或 SSE MCP server 包装。
- 复用现有 Tool Registry 和 Tool Contract。

风险：

- 容易引入新问题。
- 当前阶段若时间紧，不建议优先做。

### 2. 安全规则库外部化

影响：中高。能增强“规则库/风险识别模型”说服力。

可做内容：

- 将 Red Team 规则从 Python 常量抽到 JSON/YAML。
- 每条规则包含：
  - rule id
  - severity
  - pattern
  - mitigation
  - mapped requirement

风险：

- 会影响现有通过的 Red Team 自检。
- 做前需备份并保留回归测试。

### 3. 更多真实故障场景

影响：中高。能避免项目只会诊断 nginx 端口冲突。

可做内容：

- 磁盘空间不足。
- 内存压力。
- CPU 高负载。
- 服务 inactive。
- 日志 permission denied。

风险：

- 每个场景都需要真实证据和稳定复现。
- 不如先把 nginx 主链路打磨到极稳。

### 4. 前端标注数据来源

影响：中。能减少评委误解。

可做内容：

- 每个关键卡片标注：
  - real
  - demo
  - static
  - audit replay
- 审计中心区分样例会话和真实会话。

风险：

- 需要改前端 UI。
- 当前已停止开发时，可只在答辩材料中说明。

### 5. API Smoke Test 脚本

影响：中。提高演示前稳定性。

可做内容：

- PowerShell smoke test。
- Bash smoke test。
- 自动检查核心 API：
  - health
  - environment
  - diagnose
  - mcp
  - redteam
  - audit export

风险：

- 低风险，但不是评审第一眼看到的亮点。

### 6. 审计报告美化

影响：中。提升答辩质感。

可做内容：

- 报告增加赛题要求对齐矩阵。
- 报告增加工具轨迹表格。
- 报告增加风险等级和处置建议。

风险：

- 低风险，但不要破坏现有 Markdown 导出。

## P2（可放弃）

### 1. 重构前端 `App.tsx`

影响：低。代码质量提升明显，但对获奖现场帮助有限。

可放弃原因：

- 当前页面可演示。
- 重构风险高。
- 容易引入 UI 回归。

### 2. 数据库替代本地 JSON

影响：低到中。工程化更好，但不是当前核心验收点。

可放弃原因：

- 本地 JSON 足够支撑审计和回放演示。
- 数据库会增加部署复杂度。

### 3. 完整用户系统 / 权限后台

影响：低。赛题关注 Agent 运维安全，不是用户管理系统。

可放弃原因：

- 非核心。
- 容易跑偏。

### 4. 大规模可视化美化

影响：低。当前 UI 已足够展示。

可放弃原因：

- 美化不如实机证据重要。
- 过度视觉化会稀释技术重点。

### 5. DeepSeek 在线接入强化

影响：低到中。可作为亮点，但不应依赖外部模型。

可放弃原因：

- 网络和 Key 不稳定。
- 当前 rule-fallback 已能闭环。
- 评审重点是安全可控和可验证，而不是模型炫技。

### 6. 自动修复真实执行

影响：双刃剑。做得好加分，做不好扣分。

可放弃原因：

- 赛题要求确定性和安全，未授权不修改关键配置更重要。
- 当前 Shadow Execution + 人工确认更安全。
- 决赛前不建议新增真实写操作。

## 最终建议

剩余时间优先顺序：

1. openKylin 实机跑通。
2. real adapter 工具轨迹录屏。
3. nginx 端口冲突完整闭环。
4. 安全拦截、Red Team、MCP 演示截图。
5. 整理审计报告、验证矩阵和答辩材料。

不建议继续做新页面、新功能或大规模重构。

