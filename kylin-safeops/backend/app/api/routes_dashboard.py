from fastapi import APIRouter

from backend.app.execution.environment import probe_environment
from backend.app.tools.runner import run_tool

router = APIRouter()


@router.get("/summary")
def dashboard_summary() -> dict:
    env = probe_environment()
    system_metrics = collect_system_metrics()
    health_score = _health_score(system_metrics, env)
    return {
        "health_score": health_score,
        "services": [
            {"name": "nginx", "state": "failed", "risk": "medium"},
            {"name": "sshd", "state": "running", "risk": "medium"},
        ],
        "ports": [
            {"port": 22, "process": "sshd", "risk": "medium"},
            {"port": 80, "process": "httpd", "risk": "high"},
        ],
        "mode": env["effective_mode"],
        "environment": env,
        "system_metrics": system_metrics,
        "metrics_source": "real" if env.get("effective_mode") == "real" and env.get("real_mode_ready") else "demo",
        "metrics_notice": "真实采集：/proc/stat、/proc/meminfo、df -h" if env.get("effective_mode") == "real" and env.get("real_mode_ready") else "当前不是 real mode，系统资源指标为 demo 样例数据",
    }


@router.get("/metrics")
def dashboard_metrics() -> dict:
    env = probe_environment()
    return {
        "mode": env["effective_mode"],
        "environment": env,
        "system_metrics": collect_system_metrics(),
    }


def collect_system_metrics() -> dict:
    cpu = run_tool("cpu_stat", {})
    memory = run_tool("memory_info", {})
    disk = run_tool("disk_usage", {"mount": "/"})
    return {
        "cpu": _metric_payload(cpu),
        "memory": _metric_payload(memory),
        "disk": _metric_payload(disk),
        "tools": [cpu, memory, disk],
        "all_ok": all(item.get("ok") for item in [cpu, memory, disk]),
        "is_demo": any(item.get("facts", {}).get("is_demo") for item in [cpu, memory, disk]),
    }


def _metric_payload(result: dict) -> dict:
    return {
        "ok": result.get("ok", False),
        "summary": result.get("summary", ""),
        "facts": result.get("facts", {}),
        "tool": result.get("tool", ""),
        "mode": result.get("mode", ""),
        "adapter": result.get("adapter", ""),
        "command": result.get("command", ""),
        "raw": result.get("raw", ""),
        "duration_ms": result.get("duration_ms", 0),
    }


def _health_score(metrics: dict, env: dict) -> int:
    score = 92 if env.get("effective_mode") == "real" and env.get("real_mode_ready") else 76
    cpu = float(metrics.get("cpu", {}).get("facts", {}).get("cpu_percent") or 0)
    memory = float(metrics.get("memory", {}).get("facts", {}).get("memory_percent") or 0)
    disk = float(metrics.get("disk", {}).get("facts", {}).get("disk_percent") or 0)
    for value, medium, high in [(cpu, 70, 90), (memory, 75, 90), (disk, 80, 92)]:
        if value >= high:
            score -= 15
        elif value >= medium:
            score -= 7
    if metrics.get("is_demo"):
        score -= 6
    return max(0, min(100, round(score)))
