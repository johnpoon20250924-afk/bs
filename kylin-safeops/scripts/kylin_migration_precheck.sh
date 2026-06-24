#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

REPORT_DIR="${REPORT_DIR:-data}"
REPORT_PATH="${REPORT_PATH:-$REPORT_DIR/kylin_migration_precheck_report.md}"
PREFLIGHT_REPORT="${PREFLIGHT_REPORT:-$REPORT_DIR/kylin_preflight_report.md}"
mkdir -p "$REPORT_DIR"

now="$(date '+%Y-%m-%d %H:%M:%S %z')"
demo_status="未执行"

run_preflight() {
  REPORT_PATH="$PREFLIGHT_REPORT" bash scripts/kylin_preflight.sh >/tmp/kylin-safeops-preflight.out
}

script_status() {
  local path="$1"
  if [ -f "$path" ]; then
    printf "存在"
  else
    printf "缺失"
  fi
}

run_preflight

if [ "${SAFEOPS_CONFIRM_DEMO:-false}" = "true" ]; then
  if bash scripts/kylin_prepare_nginx_conflict.sh; then
    demo_status="已准备 nginx 端口冲突演示数据"
  else
    demo_status="准备演示数据失败，请查看终端输出"
  fi
else
  demo_status="默认跳过。需要时运行：SAFEOPS_CONFIRM_DEMO=true bash scripts/kylin_prepare_nginx_conflict.sh"
fi

backend_cmd="SAFEOPS_MODE=real bash scripts/start_backend_kylin.sh  # 仅当 Python/FastAPI 依赖已随产物提供"
frontend_cmd="bash scripts/start_frontend_kylin.sh  # 仅当 Node/npm 或已构建前端产物可用"
verify_cmd="bash scripts/kylin_immutable_verify.sh"

{
  echo "# KylinSafeOps 迁移预检总报告"
  echo
  echo "- 生成时间：$now"
  echo "- 项目目录：$ROOT_DIR"
  echo "- 兼容性报告：$PREFLIGHT_REPORT"
  echo "- 端口冲突演示数据：$demo_status"
  echo
  echo "## 1. 脚本清单"
  echo
  echo "| 脚本 | 用途 | 状态 |"
  echo "| --- | --- | --- |"
  echo "| scripts/kylin_preflight.sh | 依赖检查与兼容性报告 | $(script_status scripts/kylin_preflight.sh) |"
  echo "| scripts/kylin_immutable_verify.sh | Immutable/openKylin 无安装真实系统验证 | $(script_status scripts/kylin_immutable_verify.sh) |"
  echo "| scripts/kylin_install_runtime.sh | 可写 apt 系统依赖安装（Immutable 系统不默认使用） | $(script_status scripts/kylin_install_runtime.sh) |"
  echo "| scripts/kylin_prepare_nginx_conflict.sh | nginx 端口冲突演示数据 | $(script_status scripts/kylin_prepare_nginx_conflict.sh) |"
  echo "| scripts/kylin_cleanup_demo_services.sh | 清理端口冲突演示数据 | $(script_status scripts/kylin_cleanup_demo_services.sh) |"
  echo "| scripts/start_backend_kylin.sh | real 模式启动后端 | $(script_status scripts/start_backend_kylin.sh) |"
  echo "| scripts/start_frontend_kylin.sh | 启动前端页面 | $(script_status scripts/start_frontend_kylin.sh) |"
  echo
  echo "## 2. 预检摘要"
  echo
  if [ -f "$PREFLIGHT_REPORT" ]; then
    sed -n '1,80p' "$PREFLIGHT_REPORT"
  else
    echo "未生成兼容性报告。"
  fi
  echo
  echo "## 3. 下一步命令"
  echo
  echo '```bash'
  echo "$verify_cmd"
  echo "bash scripts/kylin_migration_precheck.sh"
  echo "$backend_cmd"
  echo "$frontend_cmd"
  echo '```'
  echo
  echo "## 4. 演示数据"
  echo
  echo "- 端口冲突造数默认不会执行，避免误改真实环境。"
  echo "- openKylin Immutable 环境中如果 apt 被 ostree-pkgs-guard 拦截，请不要强行安装依赖，优先运行无安装验证脚本。"
  echo "- 只在比赛演示虚拟机中运行："
  echo
  echo '```bash'
  echo "SAFEOPS_CONFIRM_DEMO=true bash scripts/kylin_prepare_nginx_conflict.sh"
  echo "bash scripts/kylin_cleanup_demo_services.sh"
  echo '```'
} > "$REPORT_PATH"

cat "$REPORT_PATH"
echo
echo "Migration precheck report written to: $REPORT_PATH"
