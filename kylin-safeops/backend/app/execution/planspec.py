import re


ALLOWED_SERVICES = ["nginx", "redis", "mysql", "sshd"]
DEFAULT_SERVICE = "nginx"
DEFAULT_PORTS = {
    "nginx": [80, 443],
    "redis": [6379],
    "mysql": [3306],
    "sshd": [22],
}


def build_diagnosis_plan(query: str, source: dict | None = None) -> dict:
    scenario = _detect_scenario(query, source)
    service = _detect_service(query, source)
    port = _detect_port(query, source, service)

    if scenario == "resource":
        return _resource_plan(query)
    if scenario == "network":
        return _network_plan(query, port, service)
    if scenario == "log":
        return _log_plan(query, service)
    return _service_plan(query, service, port)


def build_nginx_failure_plan(query: str) -> dict:
    return _service_plan(query, "nginx", 80)


def _detect_scenario(query: str, source: dict | None) -> str:
    text = f"{query} {source or ''}".lower()
    if any(token in text for token in ["cpu", "memory", "mem", "disk", "load", "磁盘", "内存", "资源", "负载"]):
        return "resource"
    if any(token in text for token in ["port", "listen", "network", "socket", "端口", "监听", "网络"]):
        return "network"
    if any(token in text for token in ["journal", "log", "日志", "报错", "error"]):
        return "log"
    return "service"


def _detect_service(query: str, source: dict | None) -> str:
    if source:
        raw = str(source.get("service") or source.get("process") or "").replace(".service", "")
        if raw in ALLOWED_SERVICES:
            return raw
    text = query.lower()
    for service in ALLOWED_SERVICES:
        if service in text:
            return service
    return DEFAULT_SERVICE


def _detect_port(query: str, source: dict | None, service: str) -> int:
    if source and source.get("port"):
        return _clamp_port(source.get("port"), DEFAULT_PORTS.get(service, [80])[0])
    match = re.search(r"\b([1-9][0-9]{1,4})\b", query)
    if match:
        return _clamp_port(match.group(1), DEFAULT_PORTS.get(service, [80])[0])
    return DEFAULT_PORTS.get(service, [80])[0]


def _clamp_port(value, fallback: int) -> int:
    try:
        port = int(value)
    except (TypeError, ValueError):
        return fallback
    return port if 1 <= port <= 65535 else fallback


def _base_plan(query: str, plan_id: str, goal: str, intent: str, scope: dict, required_evidence: list[str], steps: list[dict]) -> dict:
    return {
        "id": plan_id,
        "goal": goal,
        "user_query": query,
        "intent": intent,
        "safety_level": "readonly_diagnosis",
        "scope": scope,
        "forbidden_actions": [
            "delete_file",
            "modify_config",
            "read_sensitive_file",
            "stop_unrelated_service",
            "restart_without_confirm",
        ],
        "required_evidence": required_evidence,
        "steps": steps,
    }


def _service_plan(query: str, service: str, port: int) -> dict:
    ports = sorted(set(DEFAULT_PORTS.get(service, [port]) + [port]))
    return _base_plan(
        query,
        f"plan_service_{service}",
        f"Diagnose {service}.service failure with service, log, network, process, and resource evidence",
        "service_failure_diagnosis",
        {"services": [service], "ports": ports, "logs": [f"{service}.service"]},
        [
            "service_status",
            "error_log",
            "port_occupancy",
            "network_context",
            "lsof_process_context",
            "process_owner",
            "cpu_context",
            "memory_context",
            "disk_context",
        ],
        [
            _step("step_1", "systemctl_status", {"service": service}, "Confirm systemd service state before guessing.", "service_status"),
            _step("step_2", "journalctl_unit", {"unit": service, "lines": 80}, "Read recent unit logs for explicit failure signals.", "error_log"),
            _step("step_3", "ss_listen", {"port": port}, "Check whether the expected TCP port is already listening.", "port_occupancy"),
            _step("step_4", "netstat_listen", {"port": port}, "Cross-check socket state with netstat.", "network_context"),
            _step("step_5", "lsof_port", {"port": port}, "Map the listening port back to process and user.", "lsof_process_context"),
            _step("step_6", "ps_process", {"pid": "$from_port_evidence"}, "Resolve the owning process identity.", "process_owner"),
            _step("step_7", "cpu_stat", {}, "Collect CPU pressure from /proc/stat.", "cpu_context"),
            _step("step_8", "memory_info", {}, "Collect memory pressure from /proc/meminfo.", "memory_context"),
            _step("step_9", "disk_usage", {"mount": "/"}, "Collect root filesystem usage with df -h.", "disk_context"),
        ],
    )


def _resource_plan(query: str) -> dict:
    return _base_plan(
        query,
        "plan_resource_pressure",
        "Diagnose system resource pressure with CPU, memory, and disk evidence",
        "resource_pressure_diagnosis",
        {"services": [], "ports": [], "logs": []},
        ["cpu_context", "memory_context", "disk_context"],
        [
            _step("step_1", "cpu_stat", {}, "Collect CPU utilization and load average from /proc.", "cpu_context"),
            _step("step_2", "memory_info", {}, "Collect memory availability from /proc/meminfo.", "memory_context"),
            _step("step_3", "disk_usage", {"mount": "/"}, "Collect root filesystem usage with df -h.", "disk_context"),
        ],
    )


def _network_plan(query: str, port: int, service: str) -> dict:
    return _base_plan(
        query,
        f"plan_network_port_{port}",
        f"Diagnose TCP port {port} listener and process ownership",
        "network_port_diagnosis",
        {"services": [service], "ports": [port], "logs": [f"{service}.service"]},
        ["port_occupancy", "network_context", "lsof_process_context", "process_owner"],
        [
            _step("step_1", "ss_listen", {"port": port}, "Inspect listening sockets with ss.", "port_occupancy"),
            _step("step_2", "netstat_listen", {"port": port}, "Cross-check listener state with netstat.", "network_context"),
            _step("step_3", "lsof_port", {"port": port}, "Resolve listener owner with lsof.", "lsof_process_context"),
            _step("step_4", "ps_process", {"pid": "$from_port_evidence"}, "Resolve process identity for the owning PID.", "process_owner"),
        ],
    )


def _log_plan(query: str, service: str) -> dict:
    return _base_plan(
        query,
        f"plan_log_{service}",
        f"Diagnose recent {service}.service journal errors",
        "log_anomaly_diagnosis",
        {"services": [service], "ports": DEFAULT_PORTS.get(service, []), "logs": [f"{service}.service"]},
        ["service_status", "error_log", "cpu_context", "memory_context", "disk_context"],
        [
            _step("step_1", "systemctl_status", {"service": service}, "Confirm service state linked to the log request.", "service_status"),
            _step("step_2", "journalctl_unit", {"unit": service, "lines": 120}, "Read recent logs and isolate error patterns.", "error_log"),
            _step("step_3", "cpu_stat", {}, "Add CPU context for log anomaly interpretation.", "cpu_context"),
            _step("step_4", "memory_info", {}, "Add memory context for OOM or pressure interpretation.", "memory_context"),
            _step("step_5", "disk_usage", {"mount": "/"}, "Add disk context for write or log rotation failures.", "disk_context"),
        ],
    )


def _step(step_id: str, tool: str, args: dict, reason: str, expected_evidence: str) -> dict:
    return {
        "id": step_id,
        "tool": tool,
        "args": args,
        "risk": "readonly",
        "reason": reason,
        "expected_evidence": expected_evidence,
    }
