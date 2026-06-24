import os
import re
from pathlib import Path

from backend.app.execution.environment import probe_environment
from backend.app.execution.tool_contract import ToolContractError, validate_tool_call
from backend.app.tools.base import run_command


DEMO_PID = 1234


def run_tool(tool_name: str, args: dict) -> dict:
    try:
        validate_tool_call(tool_name, args)
    except ToolContractError as exc:
        return {
            "tool": tool_name,
            "args": args,
            "ok": False,
            "risk": "blocked",
            "mode": "policy",
            "adapter": "tool-contract",
            "summary": str(exc),
            "raw": "",
            "facts": {},
            "command": "",
            "duration_ms": 0,
        }

    env = probe_environment()
    mode = env["effective_mode"]
    if mode == "real" and env["real_mode_ready"]:
        result = _run_real(tool_name, args)
        return _with_metadata(result, tool_name, args, "real", env)

    if mode == "real" and not env["real_mode_ready"]:
        return {
            "tool": tool_name,
            "args": args,
            "ok": False,
            "risk": "environment",
            "mode": "real",
            "adapter": env["adapter"],
            "summary": "real 模式不可用：当前环境缺少 Linux/systemd 或必要系统工具",
            "raw": "",
            "facts": {},
            "command": "",
            "duration_ms": 0,
            "environment_blockers": env.get("real_mode_blockers", []),
        }

    result = _run_demo(tool_name, args)
    return _with_metadata(result, tool_name, args, mode, env)


def _with_metadata(result: dict, tool_name: str, args: dict, mode: str, env: dict) -> dict:
    result.update({
        "tool": tool_name,
        "args": args,
        "mode": mode,
        "adapter": env["adapter"],
        "risk": result.get("risk", "readonly"),
        "duration_ms": result.get("duration_ms", 0),
    })
    return result


def _run_demo(tool_name: str, args: dict) -> dict:
    if tool_name == "systemctl_status":
        raw = "Active: failed (Result: exit-code)\nnginx.service: Failed with result 'exit-code'."
        return {
            "ok": True,
            "summary": "nginx.service failed",
            "raw": raw,
            "facts": {"service_state": "failed"},
            "command": "systemctl status nginx.service --no-pager",
            "duration_ms": 32,
        }

    if tool_name == "journalctl_unit":
        raw = "nginx[888]: bind() to 0.0.0.0:80 failed (98: Address already in use)"
        return {
            "ok": True,
            "summary": "日志显示 Address already in use",
            "raw": raw,
            "facts": {"error": "address_in_use"},
            "command": "journalctl -u nginx.service -n 80 --no-pager",
            "duration_ms": 121,
        }

    if tool_name == "ss_listen":
        raw = f"LISTEN 0 511 0.0.0.0:80 0.0.0.0:* users:((\"httpd\",pid={DEMO_PID},fd=4))"
        return {
            "ok": True,
            "summary": f"80 端口被 PID {DEMO_PID} 占用",
            "raw": raw,
            "facts": {"port": 80, "pid": DEMO_PID, "network_source": "ss"},
            "command": "ss -lntp",
            "duration_ms": 18,
        }

    if tool_name == "netstat_listen":
        raw = f"tcp 0 0 0.0.0.0:80 0.0.0.0:* LISTEN {DEMO_PID}/httpd"
        return {
            "ok": True,
            "summary": f"netstat 确认 80 端口监听进程：PID {DEMO_PID}/httpd",
            "raw": raw,
            "facts": {"port": 80, "pid": DEMO_PID, "process": "httpd", "netstat_confirmed": True},
            "command": "netstat -lntp",
            "duration_ms": 21,
        }

    if tool_name == "lsof_port":
        raw = f"COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME\nhttpd {DEMO_PID} root 4u IPv4 12345 0t0 TCP *:http (LISTEN)"
        return {
            "ok": True,
            "summary": f"lsof 确认 80 端口归属：httpd / PID {DEMO_PID} / root",
            "raw": raw,
            "facts": {"port": 80, "pid": DEMO_PID, "process": "httpd", "user": "root", "lsof_confirmed": True},
            "command": "lsof -nP -iTCP:80 -sTCP:LISTEN",
            "duration_ms": 24,
        }

    if tool_name == "ps_process":
        raw = f"PID USER COMMAND\n{DEMO_PID} root httpd -DFOREGROUND"
        return {
            "ok": True,
            "summary": f"PID {DEMO_PID} 是 httpd 进程",
            "raw": raw,
            "facts": {"pid": DEMO_PID, "process": "httpd"},
            "command": f"ps -p {DEMO_PID} -o pid,user,comm,args",
            "duration_ms": 9,
        }

    if tool_name == "cpu_stat":
        facts = {
            "cpu_percent": 23.7,
            "cpu_cores": 4,
            "loadavg": [0.68, 0.56, 0.47],
            "collector": "/proc/stat",
            "cpu_collector": "/proc/stat",
            "is_demo": True,
        }
        return {
            "ok": True,
            "summary": "Demo CPU 使用率 23.7%",
            "raw": "cpu  235120 0 83120 920000 1200 0 2100 0 0 0",
            "facts": facts,
            "command": "cat /proc/stat",
            "duration_ms": 5,
        }

    if tool_name == "memory_info":
        facts = {
            "memory_total_mb": 7987,
            "memory_used_mb": 4887,
            "memory_available_mb": 3100,
            "memory_percent": 61.2,
            "collector": "/proc/meminfo",
            "memory_collector": "/proc/meminfo",
            "is_demo": True,
        }
        return {
            "ok": True,
            "summary": "Demo 内存使用率 61.2%",
            "raw": "MemTotal: 8178688 kB\nMemAvailable: 3174400 kB",
            "facts": facts,
            "command": "cat /proc/meminfo",
            "duration_ms": 4,
        }

    if tool_name == "disk_usage":
        mount = str(args.get("mount", "/"))
        facts = {
            "mount": mount,
            "filesystem": "/dev/sda2",
            "disk_total": "96G",
            "disk_used": "52G",
            "disk_available": "44G",
            "disk_percent": 54,
            "collector": "df -h",
            "disk_collector": "df -h",
            "is_demo": True,
        }
        return {
            "ok": True,
            "summary": f"Demo 磁盘 {mount} 使用率 54%",
            "raw": "Filesystem Size Used Avail Use% Mounted on\n/dev/sda2 96G 52G 44G 54% /",
            "facts": facts,
            "command": f"df -h {mount}",
            "duration_ms": 8,
        }

    return {"ok": False, "summary": "demo 模式未实现该工具", "raw": "", "facts": {}}


def _run_real(tool_name: str, args: dict) -> dict:
    if tool_name == "systemctl_status":
        service = str(args["service"]).replace(".service", "")
        result = run_command(["systemctl", "status", f"{service}.service", "--no-pager"])
        raw = result["stdout"] or result["stderr"]
        state = _extract_systemctl_state(raw)
        return _format_result(
            result,
            f"{service}.service 状态：{state}",
            {"service_state": state},
            ok_override=bool(raw) and state != "unknown",
        )

    if tool_name == "journalctl_unit":
        unit = str(args["unit"]).replace(".service", "")
        lines = str(int(args.get("lines", 80)))
        result = run_command(["journalctl", "-u", f"{unit}.service", "-n", lines, "--no-pager"])
        raw = result["stdout"] or result["stderr"]
        lowered = raw.lower()
        error = "address_in_use" if "address already in use" in lowered or "address in use" in lowered else "unknown"
        return _format_result(result, f"{unit}.service 日志检查：{error}", {"error": error}, ok_override=bool(raw))

    if tool_name == "ss_listen":
        port = int(args["port"])
        result = run_command(["ss", "-lntp"])
        matching = [line for line in result["stdout"].splitlines() if f":{port} " in line or f":{port}\t" in line]
        raw = "\n".join(matching) if matching else result["stdout"]
        pid = _extract_pid(raw)
        process = _extract_process_from_ss(raw)
        if not pid or not process:
            inferred = _infer_common_port_owner(port)
            pid = pid or inferred.get("pid")
            process = process or inferred.get("process")
        return {
            "ok": result["ok"],
            "returncode": result["returncode"],
            "summary": f"{port} 端口占用：{process or 'unknown'} / PID {pid or 'unknown'}",
            "raw": raw,
            "facts": {"port": port, "pid": pid, "process": process, "network_source": "ss", "ss_confirmed": bool(matching)},
            "command": result.get("command", "ss -lntp"),
            "duration_ms": result.get("duration_ms", 0),
        }

    if tool_name == "netstat_listen":
        port = int(args["port"])
        result = run_command(["netstat", "-lntp"])
        raw = _filter_port_lines(result["stdout"], port)
        pid = _extract_pid_from_netstat(raw)
        process = _extract_process_from_netstat(raw)
        return {
            "ok": result["ok"] and bool(raw),
            "returncode": result["returncode"],
            "summary": f"netstat 端口 {port}：{process or 'unknown'} / PID {pid or 'unknown'}",
            "raw": raw or result["stdout"] or result["stderr"],
            "facts": {"port": port, "pid": pid, "process": process, "netstat_confirmed": bool(raw)},
            "command": result.get("command", "netstat -lntp"),
            "duration_ms": result.get("duration_ms", 0),
        }

    if tool_name == "lsof_port":
        port = int(args["port"])
        result = run_command(["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN"])
        raw = result["stdout"] or result["stderr"]
        parsed = _extract_lsof_owner(raw)
        return {
            "ok": result["ok"] and bool(parsed.get("pid")),
            "returncode": result["returncode"],
            "summary": f"lsof 端口 {port}：{parsed.get('process') or 'unknown'} / PID {parsed.get('pid') or 'unknown'}",
            "raw": raw,
            "facts": {"port": port, **parsed, "lsof_confirmed": bool(parsed.get("pid"))},
            "command": result.get("command", f"lsof -nP -iTCP:{port} -sTCP:LISTEN"),
            "duration_ms": result.get("duration_ms", 0),
        }

    if tool_name == "ps_process":
        pid = str(int(args["pid"]))
        result = run_command(["ps", "-p", pid, "-o", "pid,user,comm,args"])
        process = _extract_process_name(result["stdout"])
        return _format_result(result, f"PID {pid} 进程：{process or '未知'}", {"pid": int(pid), "process": process})

    if tool_name == "cpu_stat":
        return _read_cpu_stat()

    if tool_name == "memory_info":
        return _read_memory_info()

    if tool_name == "disk_usage":
        return _read_disk_usage(str(args.get("mount", "/")))

    return {"ok": False, "summary": "real 模式未实现该工具", "raw": "", "facts": {}}


def _format_result(result: dict, summary: str, facts: dict, ok_override: bool | None = None) -> dict:
    return {
        "ok": result["ok"] if ok_override is None else ok_override,
        "returncode": result["returncode"],
        "summary": summary,
        "raw": result["stdout"] or result["stderr"],
        "facts": facts,
        "command": result.get("command", ""),
        "duration_ms": result.get("duration_ms", 0),
    }


def _extract_systemctl_state(text: str) -> str:
    lowered = text.lower()
    if "active: active" in lowered:
        return "active"
    if "active: failed" in lowered:
        return "failed"
    if "active: inactive" in lowered:
        return "inactive"
    if "active: activating" in lowered:
        return "activating"
    return "unknown"


def _extract_pid(text: str) -> int | None:
    match = re.search(r"pid=(\d+)", text)
    return int(match.group(1)) if match else None


def _extract_process_from_ss(text: str) -> str | None:
    match = re.search(r'users:\(\("([^"]+)"', text)
    return match.group(1) if match else None


def _extract_process_name(text: str) -> str | None:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) < 2:
        return None
    parts = lines[1].split(maxsplit=3)
    return parts[2] if len(parts) >= 3 else None


def _filter_port_lines(text: str, port: int) -> str:
    matches = []
    for line in text.splitlines():
        if f":{port} " in line or f":{port}\t" in line:
            matches.append(line)
    return "\n".join(matches)


def _extract_pid_from_netstat(text: str) -> int | None:
    match = re.search(r"\b(\d+)/([^\s]+)", text)
    return int(match.group(1)) if match else None


def _extract_process_from_netstat(text: str) -> str | None:
    match = re.search(r"\b\d+/([^\s]+)", text)
    return match.group(1) if match else None


def _extract_lsof_owner(text: str) -> dict:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) < 2:
        return {}
    parts = lines[1].split()
    if len(parts) < 3:
        return {}
    return {
        "process": parts[0],
        "pid": int(parts[1]) if parts[1].isdigit() else None,
        "user": parts[2],
    }


def _read_cpu_stat() -> dict:
    stat_path = Path("/proc/stat")
    load_path = Path("/proc/loadavg")
    if not stat_path.exists():
        return {"ok": False, "summary": "/proc/stat 不存在", "raw": "", "facts": {}, "command": "cat /proc/stat", "duration_ms": 0}

    raw = stat_path.read_text(encoding="utf-8", errors="ignore")
    cpu_line = next((line for line in raw.splitlines() if line.startswith("cpu ")), "")
    values = [int(value) for value in cpu_line.split()[1:] if value.isdigit()]
    total = sum(values)
    idle = (values[3] if len(values) > 3 else 0) + (values[4] if len(values) > 4 else 0)
    cpu_percent = round((1 - idle / total) * 100, 1) if total else 0.0
    loadavg = []
    if load_path.exists():
        load_values = load_path.read_text(encoding="utf-8", errors="ignore").split()[:3]
        loadavg = [float(value) for value in load_values]

    facts = {
        "cpu_percent": cpu_percent,
        "cpu_cores": os.cpu_count() or 0,
        "loadavg": loadavg,
        "collector": "/proc/stat",
        "cpu_collector": "/proc/stat",
        "is_demo": False,
    }
    return {
        "ok": bool(cpu_line),
        "summary": f"CPU 使用率 {cpu_percent}%",
        "raw": cpu_line,
        "facts": facts,
        "command": "cat /proc/stat",
        "duration_ms": 0,
    }


def _read_memory_info() -> dict:
    mem_path = Path("/proc/meminfo")
    if not mem_path.exists():
        return {"ok": False, "summary": "/proc/meminfo 不存在", "raw": "", "facts": {}, "command": "cat /proc/meminfo", "duration_ms": 0}

    raw = mem_path.read_text(encoding="utf-8", errors="ignore")
    data = {}
    for line in raw.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        number = value.strip().split()[0]
        if number.isdigit():
            data[key] = int(number)
    total_kb = data.get("MemTotal", 0)
    available_kb = data.get("MemAvailable", data.get("MemFree", 0))
    used_kb = max(0, total_kb - available_kb)
    percent = round(used_kb / total_kb * 100, 1) if total_kb else 0.0
    facts = {
        "memory_total_mb": round(total_kb / 1024),
        "memory_used_mb": round(used_kb / 1024),
        "memory_available_mb": round(available_kb / 1024),
        "memory_percent": percent,
        "collector": "/proc/meminfo",
        "memory_collector": "/proc/meminfo",
        "is_demo": False,
    }
    return {
        "ok": bool(total_kb),
        "summary": f"内存使用率 {percent}%",
        "raw": "\n".join(raw.splitlines()[:8]),
        "facts": facts,
        "command": "cat /proc/meminfo",
        "duration_ms": 0,
    }


def _read_disk_usage(mount: str) -> dict:
    result = run_command(["df", "-h", mount])
    raw = result["stdout"] or result["stderr"]
    parsed = _parse_df_output(raw)
    percent = parsed.get("disk_percent")
    summary = f"磁盘 {mount} 使用率 {percent}%" if percent is not None else f"磁盘 {mount} 使用率未知"
    return {
        "ok": result["ok"] and bool(parsed),
        "returncode": result["returncode"],
        "summary": summary,
        "raw": raw,
        "facts": {**parsed, "mount": mount, "collector": "df -h", "disk_collector": "df -h", "is_demo": False},
        "command": result.get("command", f"df -h {mount}"),
        "duration_ms": result.get("duration_ms", 0),
    }


def _parse_df_output(text: str) -> dict:
    lines = [line for line in text.splitlines() if line.strip()]
    if len(lines) < 2:
        return {}
    parts = lines[1].split()
    if len(parts) < 6:
        return {}
    percent_text = parts[4].rstrip("%")
    return {
        "filesystem": parts[0],
        "disk_total": parts[1],
        "disk_used": parts[2],
        "disk_available": parts[3],
        "disk_percent": int(percent_text) if percent_text.isdigit() else None,
        "mounted_on": parts[5],
    }


def _infer_common_port_owner(port: int) -> dict:
    if port not in {80, 443, 8080, 3306, 6379}:
        return {}

    process_table = run_command(["ps", "-eo", "pid=,comm=,args="])
    if not process_table["ok"]:
        return {}

    candidates = ["apache2", "httpd", "nginx", "caddy", "docker-proxy", "mysqld", "redis-server"]
    lines = [line.strip() for line in process_table["stdout"].splitlines() if line.strip()]
    for name in candidates:
        active = _service_is_active(name)
        if not active and name not in {"docker-proxy", "redis-server"}:
            continue
        for line in lines:
            if name in line:
                parts = line.split(maxsplit=2)
                if len(parts) >= 2 and parts[0].isdigit():
                    return {"pid": int(parts[0]), "process": parts[1]}
    return {}


def _service_is_active(service: str) -> bool:
    result = run_command(["systemctl", "is-active", service])
    return result["ok"] and result["stdout"].strip() == "active"
