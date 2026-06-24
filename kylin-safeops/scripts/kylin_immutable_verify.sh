#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

REPORT_DIR="${REPORT_DIR:-data}"
REPORT_PATH="${REPORT_PATH:-$REPORT_DIR/kylin_immutable_verify_report.md}"
mkdir -p "$REPORT_DIR"

now="$(date '+%Y-%m-%d %H:%M:%S %z')"

has_cmd() {
  command -v "$1" >/dev/null 2>&1
}

cmd_or_missing() {
  if has_cmd "$1"; then
    command -v "$1"
  else
    printf "missing"
  fi
}

os_text="missing"
if [ -f /etc/os-release ]; then
  os_text="$(cat /etc/os-release)"
fi

kernel_text="$(uname -a 2>/dev/null || printf 'missing')"
pid1="$(ps -p 1 -o comm= 2>/dev/null | tr -d ' ' || true)"
systemd_ready="false"
if [ "$pid1" = "systemd" ] || [ -d /run/systemd/system ]; then
  systemd_ready="true"
fi

immutable_mode="not_detected"
if [ -d /run/ostree-booted ] || has_cmd ostree || has_cmd ostree-pkgs-guard; then
  immutable_mode="likely_ostree_or_immutable"
fi

python_metrics="$(python3 - <<'PY'
from pathlib import Path
import json

def cpu():
    line = next((x for x in Path("/proc/stat").read_text(errors="ignore").splitlines() if x.startswith("cpu ")), "")
    nums = [int(x) for x in line.split()[1:] if x.isdigit()]
    total = sum(nums)
    idle = (nums[3] if len(nums) > 3 else 0) + (nums[4] if len(nums) > 4 else 0)
    load = Path("/proc/loadavg").read_text(errors="ignore").split()[:3] if Path("/proc/loadavg").exists() else []
    return {"cpu_percent_snapshot": round((1 - idle / total) * 100, 1) if total else 0, "loadavg": load, "raw": line[:180]}

def memory():
    data = {}
    for line in Path("/proc/meminfo").read_text(errors="ignore").splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        first = value.strip().split()[0]
        if first.isdigit():
            data[key] = int(first)
    total = data.get("MemTotal", 0)
    avail = data.get("MemAvailable", data.get("MemFree", 0))
    used = max(0, total - avail)
    return {"total_mb": round(total / 1024), "available_mb": round(avail / 1024), "used_mb": round(used / 1024), "used_percent": round(used / total * 100, 1) if total else 0}

print(json.dumps({"cpu": cpu(), "memory": memory()}, ensure_ascii=False, indent=2))
PY
)"

df_text="$(df -h / 2>&1 || true)"
ss_text="$(ss -lntp 2>&1 | sed -n '1,25p' || true)"
systemctl_text="$(systemctl status nginx --no-pager 2>&1 | sed -n '1,18p' || true)"
journal_text="$(journalctl -u nginx.service -n 40 --no-pager 2>&1 | sed -n '1,40p' || true)"

{
  echo "# KylinSafeOps openKylin Immutable 验证报告"
  echo
  echo "- 生成时间：$now"
  echo "- 项目目录：$ROOT_DIR"
  echo "- 策略：Windows/Codex 开发，openKylin 仅做无安装真实系统验证"
  echo "- Immutable/OSTree 迹象：$immutable_mode"
  echo "- systemd 就绪：$systemd_ready"
  echo
  echo "## 1. 系统信息"
  echo '```text'
  echo "$os_text"
  echo
  echo "$kernel_text"
  echo '```'
  echo
  echo "## 2. 工具可用性"
  echo
  echo "| 工具 | 路径 |"
  echo "| --- | --- |"
  for tool in systemctl journalctl lsof ss netstat curl wget python3 df; do
    echo "| $tool | $(cmd_or_missing "$tool") |"
  done
  echo
  echo "## 3. CPU/Memory 真实采集"
  echo '```json'
  echo "$python_metrics"
  echo '```'
  echo
  echo "## 4. Disk 真实采集"
  echo '```text'
  echo "$df_text"
  echo '```'
  echo
  echo "## 5. 服务与端口快照"
  echo '```text'
  echo "$systemctl_text"
  echo
  echo "$ss_text"
  echo '```'
  echo
  echo "## 6. nginx 日志快照"
  echo '```text'
  echo "$journal_text"
  echo '```'
  echo
  echo "## 7. 结论"
  echo "- 若本报告显示 openKylin、systemd、系统工具和 /proc/df 数据均可采集，可作为 real mode 底层能力截图材料。"
  echo "- 若后端依赖无法在 Immutable 系统安装，不影响本报告作为系统适配证明；完整 Web 联调继续在 Windows/Codex 或可写 Linux 环境完成。"
} > "$REPORT_PATH"

cat "$REPORT_PATH"
echo
echo "Immutable verification report written to: $REPORT_PATH"
