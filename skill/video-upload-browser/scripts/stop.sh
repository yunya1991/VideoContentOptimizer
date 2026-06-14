#!/usr/bin/env bash
# =============================================================================
# video-upload-browser — 停止脚本
# =============================================================================

set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="${SKILL_DIR}/logs"
mkdir -p "${LOG_DIR}"

log() { echo "[$(date +'%H:%M:%S')] $1"; }

echo "=========================================="
echo " video-upload-browser — 停止服务"
echo "=========================================="
echo

log "停止 Xvfb..."
if [[ -f "${LOG_DIR}/xvfb.pid" ]]; then
    kill "$(cat "${LOG_DIR}/xvfb.pid")" 2>/dev/null || true
    rm -f "${LOG_DIR}/xvfb.pid"
fi
killall Xvfb 2>/dev/null || true
sleep 0.5
echo "  ✅ Xvfb 已停止"

log "停止 Chromium..."
if [[ -f "${LOG_DIR}/chromium.pid" ]]; then
    kill "$(cat "${LOG_DIR}/chromium.pid")" 2>/dev/null || true
    rm -f "${LOG_DIR}/chromium.pid"
fi
killall chromium 2>/dev/null || true
killall chromium-browser 2>/dev/null || true
killall chrome 2>/dev/null || true
sleep 0.5
echo "  ✅ Chromium 已停止"

log "停止 x11vnc..."
if [[ -f "${LOG_DIR}/x11vnc.pid" ]]; then
    kill "$(cat "${LOG_DIR}/x11vnc.pid")" 2>/dev/null || true
    rm -f "${LOG_DIR}/x11vnc.pid"
fi
killall x11vnc 2>/dev/null || true
sleep 0.5
echo "  ✅ x11vnc 已停止"

log "停止 noVNC..."
if [[ -f "${LOG_DIR}/novnc.pid" ]]; then
    kill "$(cat "${LOG_DIR}/novnc.pid")" 2>/dev/null || true
    rm -f "${LOG_DIR}/novnc.pid"
fi
pkill -f "novnc" 2>/dev/null || true
pkill -f "launch.py" 2>/dev/null || true
pkill -f "http.server" 2>/dev/null || true
sleep 0.5
echo "  ✅ noVNC 已停止"

echo
echo "=========================================="
echo "✅ 所有服务已停止"
echo "=========================================="
echo
