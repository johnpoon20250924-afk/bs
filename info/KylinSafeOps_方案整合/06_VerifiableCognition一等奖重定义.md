# Verifiable Cognition 一等奖重定义

> 文档目标：把 KylinSafeOps 从 Agent 工程化作品升级为具有研究问题意识的比赛作品。  
> 推荐顶层名称：KylinSafeOps：面向操作系统运维 Agent 的可验证认知框架。  
> 英文包装：Verifiable Cognition Framework for OS Operation Agents。

---

## 1. 为什么需要重新定义

当前方案中的 PlanSpec、Tool Contract、Capability Token、Shadow Execution、Red Team、Evidence Graph，本质上大多属于 Agent Engineering，也就是：

```text
如何让 Agent 安全地执行运维动作
```

这已经比普通 “LLM + Shell” 强很多，但如果目标是一等奖，还需要提出更底层的问题：

```text
AI 运维 Agent 是否真的理解操作系统状态？
AI 是否知道自己知道什么、不知道什么？
AI 为什么相信某个根因？
AI 如何避免运维幻觉？
```

因此，项目应升级为：

> 从“安全执行框架”升级为“可验证认知框架”。

---

## 2. 最终研究问题

推荐明确写成：

> 面向操作系统运维场景，大模型 Agent 容易在证据不足时生成幻觉诊断。如何让 Agent 显式维护自己的知识状态，在多种候选根因之间进行证据驱动的诊断，并确保未经验证的信息不能升级为最终结论？

一句话：

> 我们解决的不是“AI 如何调用命令”，而是“AI 如何证明自己为什么相信这个诊断结论”。

---

## 3. 总体框架

最终分三层：

```text
Verifiable Cognition Layer
  -> Knowledge State Graph
  -> Multi-Hypothesis Diagnosis
  -> Verifiable Evidence Promotion

SafeOps Execution Layer
  -> PlanSpec Compiler
  -> Intent Anchor
  -> Tool Contract

Causal Verification Layer
  -> Counterfactual Evidence Graph
  -> PlanSpec Replay
```

三层关系：

- Verifiable Cognition 解决“Agent 如何可靠思考”。
- SafeOps Execution 解决“Agent 如何安全执行”。
- Causal Verification 解决“Agent 如何验证根因”。

---

## 4. 创新一：Knowledge State Graph

### 4.1 核心思想

Agent 必须显式维护四类知识状态：

```text
Known：已经从系统中观察到的事实
Unknown：还没有验证的信息
Assumed：候选假设，但未被证据确认
Verified：已被工具证据验证的信息
```

Nginx 诊断示例：

```text
Known:
nginx.service failed

Unknown:
80 port owner
nginx error detail

Assumed:
可能是端口冲突
可能是配置错误
可能是权限不足

Verified:
httpd occupies port 80
```

### 4.2 解决的问题

普通 Agent 常见问题：

```text
没查端口，却说可能端口占用
没查权限，却说可能权限不足
只看日志，就直接下最终结论
```

Knowledge State Graph 的要求：

```text
Unknown
  -> Tool
  -> Evidence
  -> Verified
  -> Conclusion
```

未经工具验证的信息，只能停留在 Assumed，不能升级为 Root Cause。

### 4.3 页面展示

建议在主驾驶舱中给 Evidence Graph 增加一个小面板：

```text
Knowledge State

Known:
[√] nginx failed

Unknown:
[ ] port owner

Assumed:
[?] port conflict
[?] config error
[?] permission denied

Verified:
[√] httpd owns port 80
```

### 4.4 答辩表达

> Knowledge State Graph 让 Agent 显式区分“已知事实、未知信息、候选假设和已验证证据”，从机制上减少运维幻觉。

---

## 5. 创新二：Multi-Hypothesis Diagnosis

### 5.1 核心思想

Agent 不应该一开始就只盯着一个根因，而应同时维护多个候选故障世界。

例如：

```text
World A：端口冲突
World B：配置错误
World C：权限不足
```

随着工具证据增加，系统更新每个候选根因的可信度。

### 5.2 Nginx 示例

初始状态：

```text
端口冲突：0.33
配置错误：0.33
权限不足：0.33
```

读取 `journalctl` 后：

```text
日志出现 Address already in use

端口冲突：0.70
配置错误：0.20
权限不足：0.10
```

读取 `ss` 后：

```text
80 端口被占用

端口冲突：0.85
配置错误：0.10
权限不足：0.05
```

读取 `ps` 后：

```text
PID 属于 httpd

端口冲突：0.91
配置错误：0.06
权限不足：0.03
```

注意：这里的分数是规则评分，不包装成严格数学概率。

### 5.3 展示方式

可以在 PlanSpec 或 Evidence Graph 旁边展示：

```text
Candidate Root Causes

1. Port Conflict      0.91
2. Config Error       0.06
3. Permission Denied  0.03
```

### 5.4 答辩表达

> Multi-Hypothesis Diagnosis 让 Agent 在诊断过程中同时维护多个候选根因，并用工具证据逐步筛选，而不是凭模型直觉直接给出单一答案。

---

## 6. 创新三：Verifiable Evidence Promotion

### 6.1 核心思想

信息必须经过验证才能升级。

状态流转：

```text
Unknown
  -> Assumed
  -> Tool Observed
  -> Verified
  -> Root Cause
```

规则：

- 用户输入不能直接成为事实。
- LLM 猜测不能直接成为结论。
- 日志内容只能作为观察数据。
- 工具输出需要经过解析和策略检查。
- 至少满足证据充分性要求，才能输出明确根因。

### 6.2 Nginx 示例

错误做法：

```text
用户问 nginx 起不来。
Agent：可能是端口占用。
```

正确做法：

```text
Assumed: 可能端口占用
Required Evidence: service_status, error_log, port_occupancy, process_owner

Tool:
systemctl -> failed
journalctl -> Address already in use
ss -> 80 occupied
ps -> httpd owns PID

Verified Root Cause:
httpd 占用 80 端口导致 nginx bind 失败
```

### 6.3 证据升级门槛

推荐规则：

```text
明确根因：
必须满足 3 个及以上关键证据，并包含至少 1 个直接证据。

可能根因：
只有 1-2 个证据，或者缺少直接证据。

无法判断：
证据不足，必须继续采集。
```

### 6.4 答辩表达

> Verifiable Evidence Promotion 规定未经验证的信息不能升级为诊断结论，使 Agent 的推理过程从“猜测式回答”变成“证据驱动的状态提升”。

---

## 7. 与原方案的关系

原来的模块不废弃，而是重新分层。

| 原模块 | 新定位 |
|---|---|
| PlanSpec | 运维 IR，承载任务目标和证据需求 |
| Tool Contract | 证据采集和操作执行的安全边界 |
| Intent Anchor | 确保认知过程不偏离原始目标 |
| Evidence Graph | 升级为 Counterfactual Evidence Graph |
| Shadow Execution | 基于 Host State Graph 的动作推演 |
| Red Team | 作为安全评测，不作为主创新 |
| Attack Surface | 作为业务价值增强，不作为主创新 |
| Capability Token | 轻量权限记录，不作为主创新 |

---

## 8. 最小落地版本

不要把 Verifiable Cognition 做大。最小版本只需要围绕 Nginx 场景实现。

### P0 必做

```text
Knowledge State Graph
Multi-Hypothesis Diagnosis
Verifiable Evidence Promotion
PlanSpec Compiler
Tool Contract
Counterfactual Evidence Graph
Dashboard
```

### P1 加分

```text
PlanSpec Replay
Intent Anchor 可视化
Audit Report
Shadow Execution
```

### P2 增强

```text
KylinAgentBench
Attack Surface Evolution
Incident Memory Graph
多场景诊断
```

---

## 9. 不建议立刻做的内容

### 9.1 KylinAgentBench

Agent Safety Benchmark 很有创新性，但短期内容易拖垮工程。

建议定位为：

```text
后续扩展方向
```

可以在文档和答辩中展示小型评测集，但不要把它作为主交付。

### 9.2 Incident Memory Graph

运维记忆体很有潜力，但需要历史样本和相似度计算。短期可以做静态样例，不建议作为主线。

### 9.3 完整数字孪生

Digital Twin 包装很强，但完整实现成本高。建议只做轻量 Host State Graph 支撑 Shadow Execution。

---

## 10. 最终答辩口径

推荐 30 秒版本：

> 普通运维 Agent 最大问题不是不会调用工具，而是会在证据不足时产生诊断幻觉。KylinSafeOps 提出可验证认知框架，让 Agent 显式维护 Known、Unknown、Assumed、Verified 四类知识状态，同时保留多个候选根因，并要求信息经过工具证据验证后才能升级为结论。系统最终用反事实证据图解释并验证根因，从而实现可证明、可复盘、可审计的智能运维。

推荐 10 秒版本：

> 我们解决的是运维 Agent 的幻觉问题：它必须知道自己知道什么、不知道什么，并用证据证明自己为什么相信某个根因。

---

## 11. 最终定位

最终项目定位建议改为：

> KylinSafeOps：面向麒麟操作系统运维 Agent 的可验证认知与安全执行框架。

最终创新点：

```text
Knowledge State Graph
Multi-Hypothesis Diagnosis
Verifiable Evidence Promotion
Counterfactual Evidence Graph
```

最终可见作品：

```text
运维驾驶舱
  -> Agent 对话
  -> PlanSpec
  -> Knowledge State
  -> Candidate Root Causes
  -> Counterfactual Evidence Graph
  -> Tool Trace
  -> Audit Report
```

