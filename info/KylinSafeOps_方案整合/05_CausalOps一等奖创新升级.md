# CausalOps 一等奖创新升级

> 文档目标：在不继续横向堆功能的前提下，提升 KylinSafeOps 的一等奖创新性。  
> 核心策略：从“安全运维 Agent”升级为“因果验证型安全运维 Agent”。  
> 推荐总叙事：SafeOps Runtime + CausalOps。

---

## 1. 为什么不继续堆模块

如果目标是冲一等奖，不建议继续增加：

- 更多系统工具。
- 更多页面。
- 更多安全规则。
- 更多普通诊断场景。

这些属于横向扩展，容易变成“功能多但记不住”。

一等奖更需要一个别人没想到、但又能真实演示的核心创新点。

本方案建议把创新集中到三个核心机制：

```text
PlanSpec Compiler
Intent Anchor
Counterfactual Evidence Graph
```

一句话：

> 系统不是总结日志，而是把运维请求编译成计划，锚定任务边界，并用反事实证据图验证根因。

---

## 2. 创新一：PlanSpec Compiler

### 2.1 核心思想

普通 Agent 流程：

```text
自然语言
  -> LLM
  -> Shell
```

本项目流程：

```text
自然语言
  -> PlanSpec
  -> 受控工具执行
```

PlanSpec 是 Agent 的运维 IR。

### 2.2 解决的问题

它解决三个问题：

- LLM 计划不透明。
- 工具调用不可审查。
- 诊断过程不可复盘。

### 2.3 最小落地

PlanSpec 不需要做成复杂 DSL，只要包含：

```json
{
  "goal": "诊断 nginx 启动失败",
  "scope": ["nginx.service", "port:80", "journal:nginx"],
  "forbidden": ["delete_file", "modify_config", "stop_unrelated_service"],
  "required_evidence": ["service_status", "error_log", "port_occupancy", "process_owner"],
  "steps": ["systemctl_status", "journalctl_unit", "ss_listen", "ps_process"]
}
```

### 2.4 答辩表达

> PlanSpec Compiler 将自然语言运维请求编译为可审查、可执行、可回放的运维中间表示，避免大模型直接驱动系统命令。

---

## 3. 创新二：Intent Anchor

### 3.1 核心思想

Agent 在长周期任务中可能跑偏。

例如原始目标是：

```text
诊断 nginx 启动失败
```

但执行中突然尝试：

```text
读取 /etc/shadow
扫描所有服务
删除日志
```

这些动作即使工具本身存在，也不属于当前任务。

Intent Anchor 用 PlanSpec 的目标、范围、禁止动作和证据需求，对每一步动作进行锚定检查。

### 3.2 检测维度

| 检测项 | 示例 | 结果 |
|---|---|---|
| 服务范围 | nginx 任务中操作 sshd | 漂移 |
| 端口范围 | nginx 任务中扫描全部端口 | 可能漂移 |
| 文件范围 | 读取 `/etc/shadow` | 漂移 |
| 动作类型 | 诊断任务中删除日志 | 漂移 |
| 数据源污染 | 日志内容伪装成指令 | 注入 |

### 3.3 页面展示

在 Tool Trace 中展示：

```text
Intent Anchor: PASS
scope: nginx.service
tool: journalctl_unit
risk: readonly
```

漂移时展示：

```text
Intent Drift Detected
reason: action read_sensitive_file is outside PlanSpec scope
decision: blocked
```

### 3.4 答辩表达

> 命令白名单只能判断命令是否危险，Intent Anchor 进一步判断当前动作是否仍然服务于原始运维目标，从而防止 Agent 目标漂移。

---

## 4. 创新三：Counterfactual Evidence Graph

### 4.1 从证据链到反事实验证

普通证据链：

```text
nginx failed
  <- 80 occupied
  <- httpd
```

反事实证据图：

```text
事实世界：
nginx failed
  <- 80 occupied
  <- httpd

反事实世界：
if stop_or_reconfigure(httpd)
  -> 80 free
  -> nginx bind condition satisfied
  -> failure condition disappears
```

### 4.2 解决的问题

它解决评委最可能问的问题：

> 你为什么确定这就是根因？

回答不再是：

```text
模型分析出来的。
```

而是：

```text
因为日志、端口和进程证据共同支持端口冲突，并且反事实推演显示：若移除 httpd 对 80 端口的占用，nginx 的 bind 失败条件将消失。
```

### 4.3 最小落地

只实现 Nginx 端口冲突这一个强场景即可。

节点：

- 症状：nginx failed。
- 日志证据：Address already in use。
- 端口证据：80 occupied。
- 进程证据：httpd owns PID。
- 根因：port conflict。
- 反事实：if release 80。
- 建议：stop httpd or change nginx port。

### 4.4 证据充分性评分

建议显示：

```text
必需证据：
[√] 服务状态
[√] 错误日志
[√] 端口占用
[√] 进程归属

证据充分性：4/4
根因可信度：0.91
```

注意：可信度用规则评分，不要包装成严格统计概率。

### 4.5 答辩表达

> Counterfactual Evidence Graph 不只是展示证据，而是通过反事实分支验证候选根因是否能够解释故障消失条件。

---

## 5. 展示增强一：PlanSpec Replay

PlanSpec Replay 是运维黑匣子。

保存：

- PlanSpec。
- Tool Trace。
- Evidence Graph。
- 策略命中。
- Agent 结论。

页面一键回放：

```text
Step 1: 生成 PlanSpec
Step 2: 调用 systemctl
Step 3: 调用 journalctl
Step 4: 调用 ss
Step 5: 调用 ps
Step 6: 构建反事实证据图
Step 7: 输出根因
```

价值：

- 开发量不大。
- 演示效果强。
- 很适合答辩。
- 能证明诊断不是事后编造。

优先级：P1。

---

## 6. 展示增强二：Host State Graph 数字孪生轻量版

不要一上来做完整数字孪生。只做轻量 Host State Graph：

```text
Host
  -> Service
  -> Port
  -> Process
  -> Connection
```

用于支撑 Shadow Execution：

```text
restart nginx
  -> nginx stop
  -> port 80 temporarily unavailable
  -> active connections affected
```

注意：只展示真实采集到的状态，不输出没有依据的影响时间预测。

优先级：P1/P2。

---

## 7. 展示增强三：Attack Surface Evolution

静态攻击面扫描不够新。

可以做攻击面演化：

```text
上一次扫描：
22, 80

本次扫描：
22, 80, 3306

新增暴露：
3306 / mysql / high risk
```

Agent 自动解释：

```text
风险变化：新增 MySQL 对外开放，攻击面扩大，建议限制监听地址或配置防火墙。
```

优先级：P2。

---

## 8. 一等奖版本 P0/P1/P2

### P0：必须完成

```text
Dashboard
PlanSpec Compiler
Intent Anchor
Tool Contract
Tool Trace
Counterfactual Evidence Graph
Kylin/openKylin 真实运行材料
```

### P1：强烈建议

```text
PlanSpec Replay
Shadow Execution with Host State Graph
Audit Report
日志注入检测
```

### P2：最后增强

```text
Red Team Lab
Attack Surface Evolution
Capability Token 可视化
多场景诊断
```

---

## 9. 最终答辩主线

推荐答辩顺序：

1. 普通 Agent 的问题：LLM 直接调用命令，不安全、不可解释、不可复盘。
2. 我们的改进：自然语言先编译成 PlanSpec。
3. 安全控制：Intent Anchor 和 Tool Contract 防止跑偏和越权。
4. 根因分析：Counterfactual Evidence Graph 验证端口冲突根因。
5. 工程落地：Kylin/openKylin 驾驶舱真实运行。
6. 可复盘：PlanSpec Replay 和 Audit Report。

---

## 10. 最终一句话

> 本项目提出 SafeOps Runtime + CausalOps：一种面向麒麟智能运维 Agent 的因果验证执行框架。系统将自然语言请求编译为 PlanSpec，通过 Intent Anchor 防止任务漂移，通过 Tool Contract 约束工具执行，并利用 Counterfactual Evidence Graph 验证根因，实现安全、可解释、可回放的智能运维。

