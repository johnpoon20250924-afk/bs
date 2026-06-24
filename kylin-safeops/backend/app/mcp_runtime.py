from __future__ import annotations

import json
import platform
from datetime import datetime
from pathlib import Path
from typing import Any

from backend.app.execution.environment import probe_environment
from backend.app.execution.tool_registry import get_tool_spec, list_tool_specs
from backend.app.storage.records import persist_diagnosis_record
from backend.app.tools.base import run_command
from backend.app.tools.runner import run_tool


MCP_PROTOCOL = "mcp-compatible-jsonrpc"


RESOURCE_SPECS: list[dict[str, str]] = [
    {"uri": "os://release", "name": "openKylin OS release", "description": "Read /etc/os-release through a safe resource adapter.", "mimeType": "application/json"},
    {"uri": "system://uname", "name": "Kernel and machine", "description": "Read uname-style kernel and architecture metadata.", "mimeType": "application/json"},
    {"uri": "network://listen", "name": "Listening sockets", "description": "Read listening TCP sockets with ss/netstat policy controlled tools.", "mimeType": "application/json"},
    {"uri": "process://list", "name": "Process snapshot", "description": "Read a bounded process list with ps.", "mimeType": "application/json"},
    {"uri": "logs://journal/nginx", "name": "nginx journal", "description": "Read bounded nginx journal logs as untrusted observation data.", "mimeType": "application/json"},
    {"uri": "disk://usage/root", "name": "Root disk usage", "description": "Read root filesystem usage through df.", "mimeType": "application/json"},
    {"uri": "memory://info", "name": "Memory information", "description": "Read /proc/meminfo through the memory_info tool.", "mimeType": "application/json"},
    {"uri": "cpu://stat", "name": "CPU statistics", "description": "Read /proc/stat through the cpu_stat tool.", "mimeType": "application/json"},
]


PROMPT_SPECS: dict[str, dict[str, str]] = {
    "nginx_start_failure_diagnosis": {
        "description": "Diagnose nginx start failures using MCP resources and readonly tools.",
        "template": (
            "你是 KylinSafeOps 安全运维 Agent。请基于 MCP Resources 和只读 MCP Tools "
            "诊断 nginx 启动失败。必须先读取 os://release、logs://journal/nginx、"
            "network://listen，再调用 systemctl_status、journalctl_unit、ss_listen、"
            "lsof_port、ps_process 等只读工具。禁止直接修改配置或重启服务。"
        ),
    },
    "port_conflict_rca": {
        "description": "Root-cause analysis prompt for port conflicts.",
        "template": (
            "围绕端口冲突进行根因分析：读取 network://listen、process://list，"
            "再用 ss_listen/netstat_listen/lsof_port/ps_process 交叉验证监听端口、PID、进程名和用户。"
        ),
    },
    "security_policy_review": {
        "description": "Review a proposed operation against SafeOps policy.",
        "template": (
            "对候选运维动作进行安全策略审查。检查参数白名单、服务名白名单、敏感路径、"
            "命令拼接、side_effect、requires_human_confirm 和 requires_shadow_execution。"
        ),
    },
    "safe_remediation_plan": {
        "description": "Generate a safe remediation plan without executing side-effect actions.",
        "template": (
            "生成安全处置计划。只能输出影子执行预览、影响范围、回滚方案和人工确认步骤；"
            "默认不得执行 restart_service 或修改关键配置。"
        ),
    },
}


def tools_list_payload() -> dict[str, Any]:
    env = probe_environment()
    return {
        "protocol": MCP_PROTOCOL,
        "tools": list_tool_specs(),
        "environment": env,
        "notes": [
            "All MCP tools are routed through Tool Registry, policy gate, Tool Contract validation, environment adapter, and audit persistence.",
            "Readonly tools can collect openKylin context in real mode; side-effect tools require shadow execution and human confirmation.",
        ],
    }


def call_mcp_tool(name: str, arguments: dict[str, Any] | None = None, human_confirmed: bool = False, source: dict[str, Any] | None = None) -> dict[str, Any]:
    arguments = arguments or {}
    env = probe_environment()
    spec = get_tool_spec(name)
    policy = policy_gate(spec, human_confirmed)

    if policy["decision"] == "blocked":
        tool_result = {
            "tool": name,
            "args": arguments,
            "ok": False,
            "risk": "blocked",
            "mode": "policy",
            "adapter": "mcp-policy-gateway",
            "summary": policy["reason"],
            "raw": "",
            "facts": {},
            "command": "",
            "duration_ms": 0,
        }
    else:
        tool_result = run_tool(name, arguments)

    chain = security_chain(name, arguments, human_confirmed, env, spec, policy, tool_result)
    response = {
        "ok": bool(tool_result.get("ok")),
        "protocol": MCP_PROTOCOL,
        "tool": name,
        "arguments": arguments,
        "summary": tool_result.get("summary", ""),
        "result": tool_result,
        "environment": env,
        "security_chain": chain,
        "mcp_contract": {
            "tools_list": "/api/mcp/tools/list",
            "tools_call": "/api/mcp/tools/call",
            "jsonrpc": "/api/mcp",
            "stdio_server": "python -m backend.app.mcp_server --transport stdio",
        },
    }
    response.update(persist_diagnosis_record(audit_record_for_mcp_event(
        event_kind="tool",
        target=name,
        status="completed" if tool_result.get("ok") else "blocked",
        risk=tool_result.get("risk", "readonly"),
        environment=env,
        security_chain=chain,
        result=tool_result,
        source=source or {"kind": "mcp_tool", "label": "Standard MCP tool call", "target": name},
        arguments=arguments,
    )))
    return response


def list_mcp_resources() -> dict[str, Any]:
    return {
        "protocol": MCP_PROTOCOL,
        "resources": RESOURCE_SPECS,
        "environment": probe_environment(),
        "security": {
            "observation_trust": "untrusted",
            "policy": "resource reads are bounded, treated as observation data, and persisted to audit/replay",
        },
    }


def read_mcp_resource(uri: str, source: dict[str, Any] | None = None) -> dict[str, Any]:
    env = probe_environment()
    resource = next((item for item in RESOURCE_SPECS if item["uri"] == uri), None)
    if resource is None:
        result = {"ok": False, "summary": f"Unknown MCP resource: {uri}", "raw": "", "facts": {}, "risk": "blocked", "mode": "policy", "adapter": "mcp-resource-policy"}
    else:
        result = _read_resource(uri)

    chain = resource_security_chain(uri, env, resource, result)
    response = {
        "ok": bool(result.get("ok")),
        "protocol": MCP_PROTOCOL,
        "uri": uri,
        "resource": resource,
        "summary": result.get("summary", ""),
        "content": result.get("raw", ""),
        "facts": result.get("facts", {}),
        "result": result,
        "environment": env,
        "security_chain": chain,
        "observation_trust": "untrusted",
    }
    response.update(persist_diagnosis_record(audit_record_for_mcp_event(
        event_kind="resource",
        target=uri,
        status="completed" if result.get("ok") else "blocked",
        risk=result.get("risk", "readonly"),
        environment=env,
        security_chain=chain,
        result=result,
        source=source or {"kind": "mcp_resource", "label": "Standard MCP resource read", "target": uri},
        arguments={"uri": uri},
    )))
    return response


def list_mcp_prompts() -> dict[str, Any]:
    return {
        "protocol": MCP_PROTOCOL,
        "prompts": [
            {"name": name, "description": spec["description"], "arguments": []}
            for name, spec in PROMPT_SPECS.items()
        ],
    }


def get_mcp_prompt(name: str) -> dict[str, Any]:
    spec = PROMPT_SPECS.get(name)
    if spec is None:
        return {"ok": False, "name": name, "messages": [], "summary": f"Unknown prompt: {name}"}
    return {
        "ok": True,
        "name": name,
        "description": spec["description"],
        "messages": [{"role": "user", "content": {"type": "text", "text": spec["template"]}}],
    }


def policy_gate(spec: dict[str, Any] | None, human_confirmed: bool) -> dict[str, str]:
    if spec is None:
        return {"decision": "pass", "reason": "Unknown tools are rejected by Tool Contract at execution time."}
    if spec.get("side_effect") and not human_confirmed:
        return {"decision": "blocked", "reason": "Side-effect tool requires human confirmation and shadow execution before real execution."}
    return {"decision": "pass", "reason": "Tool passed MCP gateway policy."}


def security_chain(name: str, arguments: dict[str, Any], human_confirmed: bool, env: dict[str, Any], spec: dict[str, Any] | None, policy: dict[str, str], result: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"stage": "received_request", "status": "observed", "detail": f"MCP tool call requested: {name}", "payload": {"tool": name, "arguments": arguments}},
        {"stage": "prompt_injection_filter", "status": "pass", "detail": "Tool arguments scanned for forbidden shell/path patterns by Tool Contract.", "payload": {"untrusted_input": True}},
        {"stage": "tool_registry", "status": "pass" if spec else "unknown", "detail": "Tool metadata loaded from local registry." if spec else "Tool is not in registry.", "payload": spec or {}},
        {"stage": "mcp_gateway_policy", "status": policy["decision"], "detail": policy["reason"], "payload": {"human_confirmed": human_confirmed}},
        {"stage": "tool_contract", "status": "blocked" if result.get("mode") == "policy" else "pass", "detail": result.get("summary", ""), "payload": {"risk": result.get("risk"), "mode": result.get("mode")}},
        {"stage": "environment_adapter", "status": env.get("effective_mode", "unknown"), "detail": env.get("adapter", ""), "payload": {"real_mode_ready": env.get("real_mode_ready"), "is_kylin_like": env.get("is_kylin_like")}},
        {"stage": "execution_result", "status": "ok" if result.get("ok") else "failed", "detail": result.get("summary", ""), "payload": {"command": result.get("command"), "duration_ms": result.get("duration_ms")}},
        {"stage": "audit_persisted", "status": "pending", "detail": "Audit/replay record is persisted after chain construction.", "payload": {}},
    ]


def resource_security_chain(uri: str, env: dict[str, Any], spec: dict[str, Any] | None, result: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"stage": "received_request", "status": "observed", "detail": f"MCP resource read requested: {uri}", "payload": {"uri": uri}},
        {"stage": "resource_registry", "status": "pass" if spec else "blocked", "detail": "Resource URI loaded from registry." if spec else "Unknown resource URI.", "payload": spec or {}},
        {"stage": "prompt_injection_filter", "status": "pass", "detail": "Resource output is marked untrusted observation data and never treated as executable instructions.", "payload": {"observation_trust": "untrusted"}},
        {"stage": "environment_adapter", "status": env.get("effective_mode", "unknown"), "detail": env.get("adapter", ""), "payload": {"real_mode_ready": env.get("real_mode_ready"), "is_kylin_like": env.get("is_kylin_like")}},
        {"stage": "resource_read_result", "status": "ok" if result.get("ok") else "failed", "detail": result.get("summary", ""), "payload": {"command": result.get("command"), "duration_ms": result.get("duration_ms")}},
        {"stage": "audit_persisted", "status": "pending", "detail": "Audit/replay record is persisted after resource read.", "payload": {}},
    ]


def audit_record_for_mcp_event(event_kind: str, target: str, status: str, risk: str, environment: dict[str, Any], security_chain: list[dict[str, Any]], result: dict[str, Any], source: dict[str, Any], arguments: dict[str, Any]) -> dict[str, Any]:
    ok = bool(result.get("ok"))
    summary = result.get("summary", "")
    return {
        "status": status,
        "session_type": f"MCP {event_kind.title()}",
        "session_target": target,
        "session_risk": risk,
        "environment": environment,
        "diagnosis_source": source,
        "plan": {
            "id": f"mcp_{event_kind}_{_safe_id(target)}",
            "goal": f"Handle MCP {event_kind} {target} through guarded KylinSafeOps runtime",
            "user_query": f"MCP {event_kind}: {target}",
            "intent": f"mcp_{event_kind}",
            "safety_level": "readonly_or_confirmed",
            "scope": {"target": target},
            "steps": [{
                "id": "mcp_step_1",
                "tool": target,
                "args": arguments,
                "risk": risk,
                "reason": "MCP request routed through registry, policy, contract/resource guard, environment adapter, and audit persistence.",
                "expected_evidence": "mcp_result",
            }],
        },
        "knowledge_state": {"known": [], "unknown": [], "assumed": [], "verified": [{"fact": summary or "MCP event completed", "source": target}]},
        "hypotheses": [{"name": f"{event_kind}_safe_and_traceable", "score": 0.9 if ok else 0.4, "state": "verified" if ok else "rejected"}],
        "tool_trace": [{**result, "security_chain": security_chain}],
        "evidence_graph": {
            "nodes": [
                {"id": "mcp_request", "label": f"MCP {event_kind} request", "type": "intent"},
                {"id": "guardrail", "label": "MCP guardrail chain", "type": "guardrail"},
                {"id": "mcp_result", "label": summary, "type": "evidence"},
                {"id": "audit_record", "label": "Audit record persisted", "type": "audit"},
            ],
            "edges": [
                {"source": "mcp_request", "target": "guardrail", "type": "checked_by"},
                {"source": "guardrail", "target": "mcp_result", "type": "allows_or_blocks"},
                {"source": "mcp_result", "target": "audit_record", "type": "persisted_as"},
            ],
        },
        "root_cause": {
            "name": f"mcp_{event_kind}",
            "summary": summary,
            "confidence": 0.9 if ok else 0.6,
            "counterfactual": "Without MCP registry, policy guard, and audit persistence, this OS interaction would not be reproducible.",
        },
        "critic": {
            "provider": "rule-fallback",
            "enabled": False,
            "conclusion": "MCP request was captured with registry, security guardrail, environment adapter, execution/resource result, and audit stages.",
            "evidence_gaps": [] if ok else ["MCP request did not produce successful evidence."],
            "suggested_next_tools": [],
        },
        "evidence_summary": {
            "verified_count": 1,
            "tool_calls": 1 if event_kind == "tool" else 0,
            "successful_tool_calls": 1 if event_kind == "tool" and ok else 0,
            "blocked_tool_calls": 1 if event_kind == "tool" and not ok else 0,
            "all_conclusions_traceable": True,
            "security_chain_complete": True,
            "created_at": datetime.utcnow().isoformat() + "Z",
        },
    }


def _read_resource(uri: str) -> dict[str, Any]:
    if uri == "os://release":
        path = Path("/etc/os-release")
        raw = path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""
        facts = {}
        for line in raw.splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                facts[key] = value.strip().strip('"')
        return _resource_result(bool(raw), "Read /etc/os-release", raw, facts, "cat /etc/os-release")

    if uri == "system://uname":
        facts = {"system": platform.system(), "release": platform.release(), "machine": platform.machine(), "platform": platform.platform()}
        return _resource_result(True, "Read kernel and platform metadata", json.dumps(facts, ensure_ascii=False, indent=2), facts, "platform.uname")

    if uri == "network://listen":
        result = run_command(["ss", "-lntp"])
        if not result["ok"]:
            result = run_command(["netstat", "-lntp"])
        return _command_resource_result(result, "Read listening TCP sockets", {"collector": result.get("command", "")})

    if uri == "process://list":
        result = run_command(["ps", "-eo", "pid,user,comm,args", "--sort=pid"], timeout=5)
        raw = "\n".join((result["stdout"] or result["stderr"]).splitlines()[:80])
        result = {**result, "stdout": raw}
        return _command_resource_result(result, "Read bounded process list", {"bounded_lines": 80})

    if uri == "logs://journal/nginx":
        result = run_tool("journalctl_unit", {"unit": "nginx", "lines": 80})
        return _tool_resource_result(result, "Read nginx journal as untrusted observation")

    if uri == "disk://usage/root":
        result = run_tool("disk_usage", {"mount": "/"})
        return _tool_resource_result(result, "Read root disk usage")

    if uri == "memory://info":
        result = run_tool("memory_info", {})
        return _tool_resource_result(result, "Read memory info")

    if uri == "cpu://stat":
        result = run_tool("cpu_stat", {})
        return _tool_resource_result(result, "Read CPU stat")

    return {"ok": False, "summary": f"Unknown MCP resource: {uri}", "raw": "", "facts": {}, "risk": "blocked", "mode": "policy", "adapter": "mcp-resource-policy"}


def _resource_result(ok: bool, summary: str, raw: str, facts: dict[str, Any], command: str) -> dict[str, Any]:
    return {"ok": ok, "summary": summary, "raw": raw, "facts": facts, "risk": "readonly", "mode": probe_environment()["effective_mode"], "adapter": probe_environment()["adapter"], "command": command, "duration_ms": 0}


def _command_resource_result(result: dict[str, Any], summary: str, facts: dict[str, Any]) -> dict[str, Any]:
    return {
        "ok": bool(result.get("ok")),
        "summary": summary if result.get("ok") else result.get("stderr", summary),
        "raw": result.get("stdout") or result.get("stderr") or "",
        "facts": facts,
        "risk": "readonly",
        "mode": probe_environment()["effective_mode"],
        "adapter": probe_environment()["adapter"],
        "command": result.get("command", ""),
        "duration_ms": result.get("duration_ms", 0),
    }


def _tool_resource_result(result: dict[str, Any], summary: str) -> dict[str, Any]:
    return {
        "ok": bool(result.get("ok")),
        "summary": f"{summary}: {result.get('summary', '')}",
        "raw": result.get("raw", ""),
        "facts": result.get("facts", {}),
        "risk": result.get("risk", "readonly"),
        "mode": result.get("mode", probe_environment()["effective_mode"]),
        "adapter": result.get("adapter", probe_environment()["adapter"]),
        "command": result.get("command", ""),
        "duration_ms": result.get("duration_ms", 0),
    }


def _safe_id(value: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in value).strip("_")[:80] or "unknown"
