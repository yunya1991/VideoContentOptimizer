#!/usr/bin/env bash
# =============================================================================
# video-upload-browser — 重启脚本
# =============================================================================

set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=========================================="
echo " video-upload-browser — 重启服务"
echo "=========================================="
echo

bash "${SKILL_DIR}/stop.sh"
sleep 2
bash "${SKILL_DIR}/start.sh"

echo
echo "✅ 重启完成，正在检查状态..."
bash "${SKILL_DIR}/health-check.sh"
