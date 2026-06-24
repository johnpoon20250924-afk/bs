import argparse
import json
import sys
from typing import Any

from backend.app.mcp_runtime import (
    PROMPT_SPECS,
    RESOURCE_SPECS,
    call_mcp_tool,
    get_mcp_prompt,
    read_mcp_resource,
)


SERVER_NAME = "kylin-safeops-mcp"


def _require_fastmcp():
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:
        raise SystemExit(
            "Python MCP SDK is not installed. Install backend dependencies first:\n"
            "  pip install -r backend/requirements.txt\n"
            "or install the SDK directly:\n"
            "  pip install mcp\n"
        ) from exc
    return FastMCP


def _json(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def build_mcp_server():
    FastMCP = _require_fastmcp()
    mcp = FastMCP(SERVER_NAME)

    @mcp.tool(description=_tool_description("systemctl_status"))
    def systemctl_status(service: str) -> str:
        return _json(call_mcp_tool("systemctl_status", {"service": service}))

    @mcp.tool(description=_tool_description("journalctl_unit"))
    def journalctl_unit(unit: str, lines: int = 80) -> str:
        return _json(call_mcp_tool("journalctl_unit", {"unit": unit, "lines": lines}))

    @mcp.tool(description=_tool_description("ss_listen"))
    def ss_listen(port: int) -> str:
        return _json(call_mcp_tool("ss_listen", {"port": port}))

    @mcp.tool(description=_tool_description("netstat_listen"))
    def netstat_listen(port: int) -> str:
        return _json(call_mcp_tool("netstat_listen", {"port": port}))

    @mcp.tool(description=_tool_description("lsof_port"))
    def lsof_port(port: int) -> str:
        return _json(call_mcp_tool("lsof_port", {"port": port}))

    @mcp.tool(description=_tool_description("ps_process"))
    def ps_process(pid: int) -> str:
        return _json(call_mcp_tool("ps_process", {"pid": pid}))

    @mcp.tool(description=_tool_description("cpu_stat"))
    def cpu_stat() -> str:
        return _json(call_mcp_tool("cpu_stat", {}))

    @mcp.tool(description=_tool_description("memory_info"))
    def memory_info() -> str:
        return _json(call_mcp_tool("memory_info", {}))

    @mcp.tool(description=_tool_description("disk_usage"))
    def disk_usage(mount: str = "/") -> str:
        return _json(call_mcp_tool("disk_usage", {"mount": mount}))

    @mcp.tool(description=_tool_description("restart_service"))
    def restart_service(service: str, human_confirmed: bool = False) -> str:
        return _json(call_mcp_tool("restart_service", {"service": service}, human_confirmed=human_confirmed))

    @mcp.resource("os://release", description="Read /etc/os-release as untrusted observation data.")
    def os_release() -> str:
        return _json(read_mcp_resource("os://release"))

    @mcp.resource("system://uname", description="Read kernel and machine metadata.")
    def system_uname() -> str:
        return _json(read_mcp_resource("system://uname"))

    @mcp.resource("network://listen", description="Read listening sockets with guarded collectors.")
    def network_listen() -> str:
        return _json(read_mcp_resource("network://listen"))

    @mcp.resource("process://list", description="Read a bounded process list.")
    def process_list() -> str:
        return _json(read_mcp_resource("process://list"))

    @mcp.resource("logs://journal/nginx", description="Read nginx journal logs as untrusted observation data.")
    def logs_journal_nginx() -> str:
        return _json(read_mcp_resource("logs://journal/nginx"))

    @mcp.resource("disk://usage/root", description="Read root disk usage.")
    def disk_usage_root() -> str:
        return _json(read_mcp_resource("disk://usage/root"))

    @mcp.resource("memory://info", description="Read memory information.")
    def memory_resource() -> str:
        return _json(read_mcp_resource("memory://info"))

    @mcp.resource("cpu://stat", description="Read CPU statistics.")
    def cpu_resource() -> str:
        return _json(read_mcp_resource("cpu://stat"))

    @mcp.prompt(description=PROMPT_SPECS["nginx_start_failure_diagnosis"]["description"])
    def nginx_start_failure_diagnosis() -> str:
        return get_mcp_prompt("nginx_start_failure_diagnosis")["messages"][0]["content"]["text"]

    @mcp.prompt(description=PROMPT_SPECS["port_conflict_rca"]["description"])
    def port_conflict_rca() -> str:
        return get_mcp_prompt("port_conflict_rca")["messages"][0]["content"]["text"]

    @mcp.prompt(description=PROMPT_SPECS["security_policy_review"]["description"])
    def security_policy_review() -> str:
        return get_mcp_prompt("security_policy_review")["messages"][0]["content"]["text"]

    @mcp.prompt(description=PROMPT_SPECS["safe_remediation_plan"]["description"])
    def safe_remediation_plan() -> str:
        return get_mcp_prompt("safe_remediation_plan")["messages"][0]["content"]["text"]

    return mcp


def _tool_description(name: str) -> str:
    from backend.app.execution.tool_registry import get_tool_spec

    spec = get_tool_spec(name) or {}
    flags = [
        f"risk={spec.get('risk', 'unknown')}",
        f"side_effect={bool(spec.get('side_effect'))}",
        f"requires_human_confirm={bool(spec.get('requires_human_confirm'))}",
        f"requires_shadow_execution={bool(spec.get('requires_shadow_execution'))}",
    ]
    return f"{spec.get('description', name)} ({', '.join(flags)}). Calls are audited and replayable."


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="KylinSafeOps standard MCP Server")
    parser.add_argument("--transport", choices=["stdio", "sse", "streamable-http"], default="stdio")
    args = parser.parse_args(argv)

    server = build_mcp_server()
    try:
        server.run(transport=args.transport)
    except TypeError:
        if args.transport == "streamable-http":
            server.run(transport="sse")
        else:
            raise
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
