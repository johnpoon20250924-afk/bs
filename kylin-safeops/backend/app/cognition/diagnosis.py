from backend.app.cognition.knowledge_state import build_initial_knowledge_state
from backend.app.execution.environment import probe_environment
from backend.app.execution.planspec import build_diagnosis_plan
from backend.app.execution.intent_anchor import check_intent_anchor
from backend.app.llm.provider import critique_diagnosis
from backend.app.storage.records import persist_diagnosis_record
from backend.app.tools.runner import run_tool


def diagnose_nginx_failure(query: str, source: dict | None = None) -> dict:
    return diagnose_system_issue(query, source)


def diagnose_system_issue(query: str, source: dict | None = None) -> dict:
    environment = probe_environment()
    plan = build_diagnosis_plan(query, source)
    source_meta = _normalize_diagnosis_source(source)
    if source_meta:
        plan["source"] = source_meta
    traces = []
    facts: dict = {}

    for step in plan["steps"]:
        args = dict(step["args"])
        if step["tool"] == "ps_process":
            pid = facts.get("pid")
            if not pid:
                traces.append({
                    "tool": step["tool"],
                    "args": args,
                    "ok": False,
                    "summary": "缺少端口占用 PID，跳过进程归属验证",
                    "mode": "skip",
                    "adapter": environment["adapter"],
                    "facts": {},
                    "duration_ms": 0,
                })
                continue
            args["pid"] = pid

        anchor = check_intent_anchor(plan, step, args)
        if anchor["decision"] != "pass":
            traces.append({
                "tool": step["tool"],
                "args": args,
                "ok": False,
                "mode": "blocked",
                "adapter": environment["adapter"],
                "summary": anchor["reason"],
                "intent_anchor": anchor,
                "facts": {},
                "duration_ms": 0,
            })
            continue

        result = run_tool(step["tool"], args)
        result["intent_anchor"] = anchor
        traces.append(result)
        facts.update({key: value for key, value in result.get("facts", {}).items() if value is not None})
        if args.get("service"):
            facts["service"] = str(args["service"]).replace(".service", "")
        if args.get("unit"):
            facts["service"] = str(args["unit"]).replace(".service", "")
        if args.get("port"):
            facts["port"] = int(args["port"])

    knowledge = _normalize_dynamic_knowledge(_build_verified_knowledge(facts, source_meta), facts, source_meta)
    hypotheses = _score_hypotheses(facts)
    graph = _build_evidence_graph(facts, source_meta)
    root_cause = _root_cause(hypotheses, facts, source_meta)
    critic = critique_diagnosis(knowledge, hypotheses, traces)

    response = {
        "answer": root_cause["summary"],
        "status": "completed",
        "environment": environment,
        "plan": plan,
        "knowledge_state": knowledge,
        "evidence_promotion": _evidence_promotion(knowledge, traces, facts, source_meta),
        "hypotheses": hypotheses,
        "tool_trace": traces,
        "evidence_graph": graph,
        "root_cause": root_cause,
        "critic": critic,
        "ai_enhancement": _ai_enhancement_status(critic),
        "safety_boundary": _safety_boundary(),
        "evidence_summary": _evidence_summary(knowledge, traces),
    }
    if source_meta:
        response["diagnosis_source"] = source_meta
        response["session_type"] = "自动巡检诊断" if source_meta.get("kind") == "runtime_alert" else "攻击面联动诊断"
        response["session_target"] = source_meta.get("target") or f"{source_meta.get('service', 'nginx')} {source_meta.get('port', 80)}/TCP 联动诊断"
        response["session_risk"] = source_meta.get("risk") or "medium"
        if source_meta.get("kind") == "runtime_alert":
            response["alert_event"] = {
                "event_id": source_meta.get("event_id"),
                "source": source_meta.get("alert_source"),
                "detected_at": source_meta.get("detected_at"),
                "risk": source_meta.get("risk"),
                "label": source_meta.get("label"),
            }
    response.update(persist_diagnosis_record(response))
    response["diagnosis_contract"] = _diagnosis_contract(response)
    return response


def _normalize_diagnosis_source(source: dict | None) -> dict | None:
    if not source:
        return None
    port = int(source.get("port") or 80)
    service = source.get("service") or source.get("process") or "nginx"
    process = source.get("process") or service
    if source.get("kind") == "runtime_alert":
        return {
            "kind": "runtime_alert",
            "event_id": source.get("event_id"),
            "label": source.get("label") or f"自动巡检事件 {service}:{port}",
            "target": source.get("target") or f"{service} {port}/TCP 自动巡检诊断",
            "port": port,
            "service": service,
            "process": process,
            "bind": source.get("bind") or "0.0.0.0",
            "risk": source.get("risk") or "medium",
            "reason": source.get("reason") or "由自动巡检事件触发受控诊断",
            "alert_source": source.get("alert_source") or source.get("source"),
            "detected_at": source.get("detected_at"),
        }
    if source.get("kind") != "attack_surface_port":
        return None
    return {
        "kind": "attack_surface_port",
        "label": source.get("label") or f"攻击面地图节点 {service}:{port}",
        "target": source.get("target") or f"{service} {port}/TCP 端口风险诊断",
        "port": port,
        "service": service,
        "process": process,
        "bind": source.get("bind") or "0.0.0.0",
        "risk": source.get("risk") or "medium",
        "reason": source.get("reason") or "从攻击面地图节点发起联动诊断",
    }


def _build_verified_knowledge(facts: dict, source_meta: dict | None = None) -> dict:
    state = build_initial_knowledge_state()
    resolved = set()
    service = facts.get("service") or (source_meta or {}).get("service") or "service"
    port = facts.get("port") or (source_meta or {}).get("port") or 80
    if source_meta:
        source_label = source_meta["label"]
        source_name = "runtime_alert" if source_meta.get("kind") == "runtime_alert" else "attack_surface_map"
        state["known"].append({
            "key": "diagnosis_source",
            "value": f"{source_label} 已触发受控诊断",
            "source": source_name,
        })
    if facts.get("service_state"):
        state["known"].append({"key": "service_state", "value": f"{service} {facts['service_state']}", "source": "systemctl"})
        resolved.add("service_state")
    if facts.get("error") == "address_in_use":
        state["verified"].append({"fact": "日志出现 Address already in use", "source": "journalctl"})
        resolved.add("error_log")
    if facts.get("pid"):
        state["verified"].append({"fact": f"{port} 端口被 PID {facts['pid']} 占用", "source": facts.get("network_source", "ss")})
        resolved.add("port_owner")
    elif facts.get("ss_confirmed"):
        state["verified"].append({"fact": f"ss 确认 {port} 端口处于 LISTEN 状态，进程归属待补证", "source": "ss"})
        resolved.add("network_context")
    if facts.get("netstat_confirmed"):
        state["verified"].append({"fact": f"netstat 确认 {port} 端口处于 LISTEN 状态", "source": "netstat"})
        resolved.add("network_context")
    if facts.get("lsof_confirmed"):
        owner = facts.get("user") or "unknown"
        state["verified"].append({"fact": f"lsof 确认端口归属用户：{owner}", "source": "lsof"})
        resolved.add("lsof_process_context")
    if facts.get("process"):
        state["verified"].append({"fact": f"占用进程是 {facts['process']}", "source": "ps"})
        resolved.add("process_owner")
    if facts.get("cpu_percent") is not None:
        state["verified"].append({"fact": f"CPU 使用率 {facts['cpu_percent']}%", "source": facts.get("cpu_collector", facts.get("collector", "/proc/stat"))})
        resolved.add("cpu_context")
    if facts.get("memory_percent") is not None:
        state["verified"].append({"fact": f"内存使用率 {facts['memory_percent']}%", "source": facts.get("memory_collector", facts.get("collector", "/proc/meminfo"))})
        resolved.add("memory_context")
    if facts.get("disk_percent") is not None:
        mount = facts.get("mount") or facts.get("mounted_on") or "/"
        state["verified"].append({"fact": f"磁盘 {mount} 使用率 {facts['disk_percent']}%", "source": facts.get("disk_collector", facts.get("collector", "df -h"))})
        resolved.add("disk_context")
    state["unknown"] = [item for item in state["unknown"] if item["key"] not in resolved]
    return state


def _as_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _has_verified_port_listener(facts: dict) -> bool:
    return bool(
        facts.get("ss_confirmed")
        or facts.get("netstat_confirmed")
        or facts.get("lsof_confirmed")
        or facts.get("pid")
    )


def _has_verified_port_owner(facts: dict) -> bool:
    return bool(facts.get("pid") and facts.get("process"))


def _normalize_dynamic_knowledge(state: dict, facts: dict, source_meta: dict | None = None) -> dict:
    port = facts.get("port") or (source_meta or {}).get("port")
    service = facts.get("service") or (source_meta or {}).get("service")
    if not port and not service:
        return state

    for item in state.get("known", []):
        value = item.get("value")
        if service and isinstance(value, str) and value.startswith("nginx "):
            item["value"] = value.replace("nginx ", f"{service} ", 1)

    for item in state.get("verified", []):
        fact = item.get("fact")
        if not isinstance(fact, str):
            continue
        if port and ("80 " in fact or "80\t" in fact):
            item["fact"] = fact.replace("80", str(port), 1)
    return state


def _score_hypotheses(facts: dict) -> list[dict]:
    port_score = 0.33
    if facts.get("error") == "address_in_use":
        port_score += 0.27
    if _has_verified_port_listener(facts):
        port_score += 0.28
    if facts.get("pid"):
        port_score += 0.24
    if facts.get("netstat_confirmed"):
        port_score += 0.06
    if facts.get("ss_confirmed"):
        port_score += 0.06
    if facts.get("lsof_confirmed"):
        port_score += 0.06
    if facts.get("process"):
        port_score += 0.16
    port_score = min(port_score, 0.95)

    cpu_percent = _as_float(facts.get("cpu_percent"))
    memory_percent = _as_float(facts.get("memory_percent"))
    disk_percent = _as_float(facts.get("disk_percent"))
    cpu_score = 0.9 if cpu_percent >= 90 else 0.72 if cpu_percent >= 75 else 0.08
    memory_score = 0.88 if memory_percent >= 90 else 0.68 if memory_percent >= 80 else 0.08
    disk_score = 0.9 if disk_percent >= 92 else 0.7 if disk_percent >= 85 else 0.08

    remaining = max(0.0, 1.0 - max(port_score, cpu_score, memory_score, disk_score))
    candidates = [
        {"name": "port_conflict", "score": round(port_score, 2), "state": "verified" if _has_verified_port_owner(facts) or (facts.get("error") == "address_in_use" and _has_verified_port_listener(facts)) else "observed" if _has_verified_port_listener(facts) else "assumed"},
        {"name": "cpu_pressure", "score": round(cpu_score, 2), "state": "verified" if cpu_percent >= 90 else "assumed" if cpu_percent >= 75 else "rejected"},
        {"name": "memory_pressure", "score": round(memory_score, 2), "state": "verified" if memory_percent >= 90 else "assumed" if memory_percent >= 80 else "rejected"},
        {"name": "disk_pressure", "score": round(disk_score, 2), "state": "verified" if disk_percent >= 92 else "assumed" if disk_percent >= 85 else "rejected"},
        {"name": "config_error", "score": round(remaining * 0.6, 2), "state": "assumed"},
        {"name": "permission_denied", "score": round(remaining * 0.4, 2), "state": "assumed"},
    ]
    return sorted(candidates, key=lambda item: item["score"], reverse=True)


def _build_evidence_graph(facts: dict, source_meta: dict | None = None) -> dict:
    service = facts.get("service") or (source_meta or {}).get("service") or "nginx"
    port = facts.get("port") or (source_meta or {}).get("port") or 80
    nodes = [{"id": "symptom_service_failed", "label": f"{service} 启动/监听异常", "type": "symptom"}]
    edges: list[dict] = []

    if source_meta:
        source_node_id = "source_runtime_alert" if source_meta.get("kind") == "runtime_alert" else "source_attack_surface"
        nodes.append({
            "id": source_node_id,
            "label": f"来源：{source_meta['label']}",
            "type": "source",
        })
        edges.append({"source": source_node_id, "target": "symptom_service_failed", "type": "triggers"})

    if facts.get("service_state"):
        nodes.append({"id": "ev_service_state", "label": f"服务状态：{facts['service_state']}", "type": "verified"})
        edges.append({"source": "ev_service_state", "target": "symptom_service_failed", "type": "observes"})

    if facts.get("error") == "address_in_use":
        nodes.append({"id": "ev_log_address", "label": "日志现象：地址已被占用", "type": "verified"})
        edges.append({"source": "ev_log_address", "target": "symptom_service_failed", "type": "supports"})

    if facts.get("pid"):
        nodes.append({"id": "ev_port_listener", "label": f"端口状态：{port} 被 PID {facts['pid']} 占用", "type": "verified"})
        target = "ev_log_address" if facts.get("error") == "address_in_use" else "symptom_service_failed"
        edges.append({"source": "ev_port_listener", "target": target, "type": "explains"})

    if facts.get("netstat_confirmed"):
        nodes.append({"id": "ev_netstat", "label": f"netstat：{port}/TCP LISTEN", "type": "verified"})
        if facts.get("pid"):
            edges.append({"source": "ev_netstat", "target": "ev_port_listener", "type": "corroborates"})

    if facts.get("lsof_confirmed"):
        owner = facts.get("user") or "unknown"
        nodes.append({"id": "ev_lsof", "label": f"lsof：端口进程用户 {owner}", "type": "verified"})
        if facts.get("pid"):
            edges.append({"source": "ev_lsof", "target": "ev_port_listener", "type": "corroborates"})

    if facts.get("process"):
        nodes.append({"id": "ev_process", "label": f"进程归属：{facts['process']}", "type": "verified"})
        if facts.get("pid"):
            edges.append({"source": "ev_process", "target": "ev_port_listener", "type": "owns"})

    resource_node_ids = []
    if facts.get("cpu_percent") is not None:
        nodes.append({"id": "ev_cpu", "label": f"CPU：{facts['cpu_percent']}%", "type": "verified"})
        resource_node_ids.append("ev_cpu")
    if facts.get("memory_percent") is not None:
        nodes.append({"id": "ev_memory", "label": f"内存：{facts['memory_percent']}%", "type": "verified"})
        resource_node_ids.append("ev_memory")
    if facts.get("disk_percent") is not None:
        mount = facts.get("mount") or facts.get("mounted_on") or "/"
        nodes.append({"id": "ev_disk", "label": f"磁盘 {mount}：{facts['disk_percent']}%", "type": "verified"})
        resource_node_ids.append("ev_disk")
    for node_id in resource_node_ids:
        edges.append({"source": node_id, "target": "symptom_service_failed", "type": "context"})

    if _as_float(facts.get("cpu_percent")) >= 90:
        nodes.append({"id": "root_cpu_pressure", "label": "Root cause: CPU pressure", "type": "root_cause"})
        edges.append({"source": "ev_cpu", "target": "root_cpu_pressure", "type": "verifies"})

    if _as_float(facts.get("memory_percent")) >= 90:
        nodes.append({"id": "root_memory_pressure", "label": "Root cause: memory pressure", "type": "root_cause"})
        edges.append({"source": "ev_memory", "target": "root_memory_pressure", "type": "verifies"})

    if _as_float(facts.get("disk_percent")) >= 92:
        nodes.append({"id": "root_disk_pressure", "label": "Root cause: disk pressure", "type": "root_cause"})
        edges.append({"source": "ev_disk", "target": "root_disk_pressure", "type": "verifies"})

    if _has_verified_port_listener(facts):
        nodes.append({"id": "root_port_conflict", "label": f"根因：{port} 端口占用冲突", "type": "root_cause"})
        if facts.get("pid"):
            edges.append({"source": "ev_port_listener", "target": "root_port_conflict", "type": "verifies"})
        elif facts.get("netstat_confirmed"):
            edges.append({"source": "ev_netstat", "target": "root_port_conflict", "type": "verifies"})
        elif facts.get("lsof_confirmed"):
            edges.append({"source": "ev_lsof", "target": "root_port_conflict", "type": "verifies"})

        process = facts.get("process") or "占用进程待补证"
        nodes.extend([
            {"id": "action_review_owner", "label": f"建议：确认 {process} 是否应占用 {port} 端口", "type": "recommendation"},
            {"id": "cf_release_port", "label": f"反事实：释放 {port} 端口", "type": "counterfactual"},
            {"id": "cf_failure_disappears", "label": "结果推演：启动失败条件消失", "type": "counterfactual"},
        ])
        edges.extend([
            {"source": "root_port_conflict", "target": "action_review_owner", "type": "recommends"},
            {"source": "root_port_conflict", "target": "cf_release_port", "type": "counterfactual_if"},
            {"source": "cf_release_port", "target": "cf_failure_disappears", "type": "would_change"},
        ])

    return {"nodes": nodes, "edges": edges}


def _root_cause(hypotheses: list[dict], facts: dict | None = None, source_meta: dict | None = None) -> dict:
    facts = facts or {}
    port = facts.get("port") or (source_meta or {}).get("port") or 80
    service = facts.get("service") or (source_meta or {}).get("service") or "nginx"
    winner = max(hypotheses, key=lambda item: item["score"])
    if winner["name"] == "cpu_pressure" and winner["state"] == "verified":
        return {
            "name": "cpu_pressure",
            "summary": "已验证根因：CPU 压力过高，服务响应和运维操作可能受影响。",
            "confidence": winner["score"],
            "counterfactual": "如果降低高占用进程负载，CPU 饱和导致的异常应缓解。",
        }
    if winner["name"] == "memory_pressure" and winner["state"] == "verified":
        return {
            "name": "memory_pressure",
            "summary": "已验证根因：内存压力过高，系统可能出现 OOM、服务重启或响应变慢。",
            "confidence": winner["score"],
            "counterfactual": "如果释放内存或限制异常进程，内存压力相关异常应缓解。",
        }
    if winner["name"] == "disk_pressure" and winner["state"] == "verified":
        return {
            "name": "disk_pressure",
            "summary": "已验证根因：磁盘空间压力过高，日志写入、服务启动和包管理可能失败。",
            "confidence": winner["score"],
            "counterfactual": "如果释放磁盘空间，写入失败或服务启动失败条件应缓解。",
        }
    if winner["name"] == "port_conflict" and _has_verified_port_listener(facts):
        owner = facts.get("process")
        pid = facts.get("pid")
        if owner and pid:
            owner_text = f"占用进程已定位为 {owner} / PID {pid}"
            evidence_state = "verified"
            confidence = max(winner["score"], 0.86)
        else:
            owner_text = "端口监听状态已由 ss/netstat 验证，但非 root 采集未获得完整 PID/进程归属，进程归属待补证"
            evidence_state = "port_verified_owner_pending"
            confidence = max(winner["score"], 0.72)
        return {
            "name": "port_conflict",
            "summary": f"已验证端口冲突：{service} 目标监听端口 {port} 已处于 LISTEN 状态，导致服务启动或绑定条件不满足；{owner_text}。",
            "confidence": round(min(confidence, 0.95), 2),
            "counterfactual": f"若释放 {port} 端口或调整 {service} 监听端口，绑定失败条件应消失；真实修复前必须先经过 Shadow Execution 和人工确认。",
            "evidence_state": evidence_state,
            "owner_pending": not bool(owner and pid),
        }
    if winner["name"] == "port_conflict" and winner["state"] == "verified":
        return {
            "name": "port_conflict",
            "summary": f"已验证根因：{service} 目标监听端口 {port} 存在占用冲突，导致服务启动或绑定条件不满足。",
            "confidence": winner["score"],
            "counterfactual": f"若释放 {port} 端口，{service} 的 bind 失败条件将消失。",
        }
    return {
        "name": winner["name"],
        "summary": "当前证据不足，只能给出候选根因，需要继续取证。",
        "confidence": winner["score"],
        "counterfactual": "",
    }


def _evidence_summary(knowledge_state: dict, traces: list[dict]) -> dict:
    verified = knowledge_state.get("verified", [])
    succeeded = [item for item in traces if item.get("ok")]
    blocked = [item for item in traces if item.get("mode") in {"blocked", "policy"}]
    network_verified = any(
        item.get("tool") in {"ss_listen", "netstat_listen", "lsof_port"} and item.get("ok")
        for item in traces
    )
    return {
        "verified_count": len(verified),
        "tool_calls": len(traces),
        "successful_tool_calls": len(succeeded),
        "blocked_tool_calls": len(blocked),
        "all_conclusions_traceable": bool(verified) and (len(succeeded) >= 3 or network_verified),
    }


def _evidence_promotion(knowledge_state: dict, traces: list[dict], facts: dict, source_meta: dict | None) -> dict:
    port = facts.get("port") or (source_meta or {}).get("port") or 80
    service = facts.get("service") or (source_meta or {}).get("service") or "nginx"
    observed_tools = [item.get("tool") for item in traces if item.get("ok")]
    verified = knowledge_state.get("verified", [])
    root_ready = _has_verified_port_listener(facts)
    return {
        "policy": "用户输入和模型输出只能形成 Question/Assumed；工具证据经解析和安全校验后才能升级为 Verified。",
        "stages": [
            {"stage": "question", "status": "captured", "detail": f"诊断 {service} 在 {port}/TCP 上的启动或监听异常。"},
            {"stage": "assumed", "status": "tracked", "detail": "端口冲突、配置错误、权限不足、资源压力均作为候选根因保留。"},
            {"stage": "observed", "status": "collected" if observed_tools else "missing", "detail": "、".join(observed_tools) or "等待工具采集"},
            {"stage": "verified", "status": "passed" if verified else "partial", "detail": f"已验证证据 {len(verified)} 条。"},
            {"stage": "root_cause", "status": "verified" if root_ready else "candidate", "detail": "端口监听证据可验证端口冲突；PID/进程归属缺失时标记为待补证，不执行破坏性修复。"},
        ],
        "target": {"service": service, "port": port},
    }


def _ai_enhancement_status(critic: dict) -> dict:
    provider = critic.get("provider", "rule-fallback")
    enabled = bool(critic.get("enabled"))
    return {
        "deepseek_enabled": enabled and provider == "deepseek",
        "provider": provider,
        "role": "诊断解释、修复建议生成、认知审查 Critic",
        "fallback": "DeepSeek 不可用时自动切换规则兜底；系统仍可完成环境感知、诊断、安全校验、审计和回放。",
        "execution_boundary": "DeepSeek 不直接执行命令，不绕过 Tool Contract，不把日志内容当作指令。",
    }


def _safety_boundary() -> dict:
    return {
        "real_remediation": "disabled_by_default",
        "restart_policy": "restart_service 必须先经过 Shadow Execution 和人工确认；当前演示默认阻断真实重启。",
        "config_mutation": "未授权情况下不修改 nginx、systemd 或关键配置文件。",
        "tool_outputs": "日志、命令输出和 MCP Resources 均作为 untrusted observation data。",
    }


def _diagnosis_contract(response: dict) -> dict:
    checks = {
        "planspec": bool(response.get("plan", {}).get("steps")),
        "tool_trace": bool(response.get("tool_trace")),
        "evidence_graph": bool(response.get("evidence_graph", {}).get("nodes")),
        "root_cause": bool(response.get("root_cause", {}).get("summary")),
        "audit_id": bool(response.get("audit_id")),
    }
    return {
        "complete": all(checks.values()),
        "checks": checks,
        "required_outputs": ["PlanSpec", "工具轨迹", "证据图谱", "根因结论", "审计ID"],
        "missing_outputs": [key for key, ok in checks.items() if not ok],
    }
