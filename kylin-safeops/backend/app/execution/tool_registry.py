from backend.app.execution.tool_contract import TOOL_CONTRACTS


def _port_schema() -> dict:
    return {
        "type": "object",
        "properties": {"port": {"type": "integer", "minimum": 1, "maximum": 65535}},
        "required": ["port"],
    }


TOOL_DESCRIPTIONS = {
    "systemctl_status": {
        "description": "Read systemd service status with systemctl.",
        "input_schema": {
            "type": "object",
            "properties": {"service": {"type": "string", "enum": ["nginx", "redis", "mysql", "sshd"]}},
            "required": ["service"],
        },
        "collects": ["service_state"],
    },
    "journalctl_unit": {
        "description": "Read recent journal logs for an allowed systemd unit.",
        "input_schema": {
            "type": "object",
            "properties": {
                "unit": {"type": "string", "enum": ["nginx", "redis", "mysql", "sshd"]},
                "lines": {"type": "integer", "minimum": 1, "maximum": 200},
            },
            "required": ["unit"],
        },
        "collects": ["log_error"],
    },
    "ss_listen": {
        "description": "Inspect listening TCP sockets with ss.",
        "input_schema": _port_schema(),
        "collects": ["port_occupancy"],
    },
    "netstat_listen": {
        "description": "Inspect listening TCP sockets with netstat.",
        "input_schema": _port_schema(),
        "collects": ["network_context"],
    },
    "lsof_port": {
        "description": "Find the process owning a listening TCP port with lsof.",
        "input_schema": _port_schema(),
        "collects": ["process_owner"],
    },
    "ps_process": {
        "description": "Read process identity for a PID with ps.",
        "input_schema": {
            "type": "object",
            "properties": {"pid": {"type": "integer", "minimum": 1}},
            "required": ["pid"],
        },
        "collects": ["process_identity"],
    },
    "cpu_stat": {
        "description": "Collect CPU utilization and load average from /proc/stat and /proc/loadavg.",
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
        "collects": ["cpu_percent", "loadavg"],
    },
    "memory_info": {
        "description": "Collect memory utilization from /proc/meminfo.",
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
        "collects": ["memory_percent"],
    },
    "disk_usage": {
        "description": "Collect disk usage for an allowed mount with df -h.",
        "input_schema": {
            "type": "object",
            "properties": {"mount": {"type": "string", "enum": ["/", "/home", "/var", "/boot", "/tmp"]}},
            "required": ["mount"],
        },
        "collects": ["disk_percent"],
    },
    "restart_service": {
        "description": "Guarded service restart contract. It is listed for policy visibility and requires confirmation.",
        "input_schema": {
            "type": "object",
            "properties": {"service": {"type": "string", "enum": ["nginx", "redis", "mysql"]}},
            "required": ["service"],
        },
        "collects": ["restart_request"],
    },
}


def list_tool_specs() -> list[dict]:
    items = []
    for name, contract in TOOL_CONTRACTS.items():
        meta = TOOL_DESCRIPTIONS.get(name, {})
        items.append({
            "name": name,
            "description": meta.get("description", ""),
            "inputSchema": meta.get("input_schema", {"type": "object"}),
            "risk": contract.get("risk", "unknown"),
            "side_effect": bool(contract.get("side_effect")),
            "requires_human_confirm": bool(contract.get("requires_human_confirm")),
            "requires_shadow_execution": bool(contract.get("requires_shadow_execution")),
            "allowed_args": contract.get("allowed_args", {}),
            "collects": meta.get("collects", []),
        })
    return items


def get_tool_spec(name: str) -> dict | None:
    return next((item for item in list_tool_specs() if item["name"] == name), None)
