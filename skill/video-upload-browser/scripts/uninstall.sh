#!/usr/bin/env bash
# =============================================================================
# video-upload-browser — 卸载脚本
# ⚠️ 警告: 此脚本会完全移除浏览器环境和登录状态
# =============================================================================

set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "=========================================="
echo " ⚠️  video-upload-browser 卸载工具"
echo "=========================================="
echo
echo "此操作将:"
echo "  1. 停止所有服务"
echo "  2. 移除 systemd 服务文件"
echo "  3. 移除 Chromium 用户数据（含各平台登录状态）"
echo "  4. 清理日志文件"
echo
read -p "确认卸载? [y/N] " -n 1 -r
echo

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "已取消"
    exit 0
fi

echo

# 停止服务
bash "${SKILL_DIR}/scripts/stop.sh"
sleep 1

# 移除 systemd 服务
echo "移除 systemd 服务..."
SYSTEMD_DIR="${HOME}/.config/systemd/user"
if [[ $EUID -eq 0 ]]; then
    SYSTEMD_DIR="/etc/systemd/system"
fi

for svc in video-upload-browser-xvfb video-upload-browser-chromium video-upload-browser-novnc; do
    if [[ -f "${SYSTEMD_DIR}/${svc}.service" ]]; then
        if [[ $EUID -eq 0 ]]; then
            systemctl stop "${svc}.service" 2>/dev/null || true
            systemctl disable "${svc}.service" 2>/dev/null || true
        else
            systemctl --user stop "${svc}.service" 2>/dev/null || true
            systemctl --user disable "${svc}.service" 2>/dev/null || true
        fi
        rm -f "${SYSTEMD_DIR}/${svc}.service"
        echo "  ✅ 已移除 ${svc}.service"
    fi
done

if [[ $EUID -eq 0 ]]; then
    systemctl daemon-reload 2>/dev/null || true
else
    systemctl --user daemon-reload 2>/dev/null || true
fi

# 移除用户数据
VUB_USER_DATA="${HOME}/.config/chromium-video-upload"
if [[ -d "${VUB_USER_DATA}" ]]; then
    echo "移除 Chromium 用户数据目录..."
    rm -rf "${VUB_USER_DATA}"
    echo "  ✅ 已移除 ${VUB_USER_DATA}"
fi

# 清理日志
if [[ -d "${SKILL_DIR}/logs" ]]; then
    rm -rf "${SKILL_DIR}/logs"
    echo "  ✅ 已清理日志目录"
fi

echo
echo "=========================================="
echo "✅ 卸载完成"
echo "=========================================="
echo
echo "说明: 系统级安装的 Chromium / Xvfb / x11vnc / noVNC 保留"
echo "如需彻底移除，请手动执行:"
echo "  Ubuntu/Debian: sudo apt-get remove chromium-browser xvfb x11vnc novnc"
echo "  CentOS/RHEL:   sudo yum remove chromium xorg-x11-server-Xvfb x11vnc"
