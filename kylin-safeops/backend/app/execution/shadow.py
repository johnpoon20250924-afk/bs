from backend.app.execution.tool_contract import ToolContractError, validate_tool_call
from backend.app.tools.runner import run_tool


def preview_restart_service(service: str = "nginx", port: int | None = None) -> dict:
    service = service.replace(".service", "")
    try:
        validate_tool_call("restart_service", {"service": service})
    except ToolContractError as exc:
        return {
            "operation": f"restart {service}.service",
            "allowed": False,
            "risk": "high",
            "summary": str(exc),
            "precheck": {},
            "impact": [],
            "rollback": [],
            "requires_confirm": True,
            "confirmation_mode": "dry_run_shadow_commit",
            "confirm_effect": "blocked_by_contract_no_restart",
            "real_execution": False,
            "production_executor": "disabled_by_default",
        }

    status = run_tool("systemctl_status", {"service": service})
    target_port = int(port or (80 if service == "nginx" else 0))
    port_check = run_tool("ss_listen", {"port": target_port}) if target_port else {"facts": {}, "summary": "无默认端口检查"}

    active_connections = _estimate_active_connections(port_check)
    precheck = {
        "service": f"{service}.service",
        "service_state": status.get("facts", {}).get("service_state", "unknown"),
        "listening_ports": [target_port] if target_port else [],
        "active_connections": active_connections,
        "config_will_change": False,
    }

    impact = [
        f"会影响当前 {service}.service 服务进程",
        f"当前端口 {target_port} 关联连接估计为 {active_connections} 个" if target_port else "未发现默认端口影响",
        "不会修改配置文件",
        "需要人工确认后才能执行真实重启",
    ]

    return {
        "operation": f"restart {service}.service",
        "allowed": True,
        "risk": "medium",
        "summary": "已完成影子执行前置检查，未执行真实重启。",
        "precheck": precheck,
        "impact": impact,
        "rollback": [
            f"若重启失败，可检查 journalctl -u {service}.service",
            f"可再次执行 systemctl start {service}.service 恢复服务",
        ],
        "requires_confirm": True,
        "confirmation_mode": "dry_run_shadow_commit",
        "confirm_effect": "record_audit_only_no_restart",
        "real_execution": False,
        "production_executor": "disabled_by_default",
        "tool_trace": [status, port_check],
    }


def _estimate_active_connections(port_check: dict) -> int:
    if port_check.get("mode", "").startswith("demo"):
        return 12
    raw = port_check.get("raw", "")
    return max(0, raw.count("ESTAB"))

