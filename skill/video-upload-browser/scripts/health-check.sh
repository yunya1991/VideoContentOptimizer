#!/usr/bin/env bash
# =============================================================================
# video-upload-browser — 健康检查脚本
# 用途: 检查 Xvfb / Chromium / CDP / noVNC 状态
# =============================================================================

set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_FILE="${HOME}/.config/chromium-video-upload/config.env"

# 加载配置
if [[ -f "${CONFIG_FILE}" ]]; then
    # shellcheck disable=SC1090
    source "${CONFIG_FILE}"
fi

VUB_CDP_PORT="${VUB_CDP_PORT:-9222}"
VUB_NOVNC_PORT="${VUB_NOVNC_PORT:-6080}"
VUB_VNC_PORT="${VUB_VNC_PORT:-5900}"
VUB_DISPLAY="${VUB_DISPLAY:-:99}"

PASS=0
FAIL=0

check() {
    local name="$1"
    local cmd="$2"
    local detail="$3"

    if eval "${cmd}" &>/dev/null; then
        echo "✅ ${name}   - 正常"
        [[ -n "${detail}" ]] && echo "     ${detail}"
        PASS=$((PASS + 1))
    else
        echo "❌ ${name}   - 异常"
        [[ -n "${detail}" ]] && echo "     ${detail}"
        FAIL=$((FAIL + 1))
    fi
}

echo "=========================================="
echo " video-upload-browser 健康检查"
echo "=========================================="
echo

# 1. 进程检查
echo "【进程状态】"
check "Xvfb   " "pgrep -f 'Xvfb ${VUB_DISPLAY}' > /dev/null" "显示器: ${VUB_DISPLAY}"
check "Chromium" "pgrep -f 'chromium' > /dev/null" ""
if [[ -d "${HOME}/.local/share/novnc-video-upload" ]]; then
    check "x11vnc " "pgrep -f 'x11vnc' > /dev/null" ""
fi

echo

# 2. 端口检查
echo "【端口监听】"
check "CDP ${VUB_CDP_PORT}" "curl -s http://127.0.0.1:${VUB_CDP_PORT}/json/version | grep -q 'Browser'" "http://127.0.0.1:${VUB_CDP_PORT}"
check "VNC ${VUB_VNC_PORT}" "(echo > /dev/tcp/127.0.0.1/${VUB_VNC_PORT}) 2>/dev/null" ""
check "noVNC ${VUB_NOVNC_PORT}" "(echo > /dev/tcp/127.0.0.1/${VUB_NOVNC_PORT}) 2>/dev/null" "http://<服务器IP>:${VUB_NOVNC_PORT}/vnc.html"

echo

# 3. CDP 详细信息
echo "【CDP 信息】"
if curl -s "http://127.0.0.1:${VUB_CDP_PORT}/json/version" | grep -q "Browser" &>/dev/null; then
    echo "  浏览器版本:"
    curl -s "http://127.0.0.1:${VUB_CDP_PORT}/json/version" 2>/dev/null | python3 -m json.tool 2>/dev/null || curl -s "http://127.0.0.1:${VUB_CDP_PORT}/json/version"
    echo
    echo "  当前页面:"
    curl -s "http://127.0.0.1:${VUB_CDP_PORT}/json" 2>/dev/null | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    for i, page in enumerate(data[:5]):
        print(f'    {i+1}. {page.get(\"title\", \"(无标题)\")}')
        print(f'       URL: {page.get(\"url\", \"\")}')
except:
    pass
" 2>/dev/null
else
    echo "  ⚠️  CDP 不可达，Chromium 可能未启动"
fi

echo
echo "=========================================="
TOTAL=$((PASS + FAIL))
echo "检查结果: ${PASS}/${TOTAL} 通过"
if [[ ${FAIL} -eq 0 ]]; then
    echo "✅ 所有服务运行正常"
    echo
    echo "💡 提示:"
    echo "   - 访问 noVNC: http://<服务器IP>:${VUB_NOVNC_PORT}/vnc.html"
    echo "   - 在 noVNC 中完成各平台登录后，AI 即可自动上传视频"
    echo "   - VideoContentOptimizer API: /api/v2/browser-upload/*"
else
    echo "⚠️  有 ${FAIL} 项异常，请检查后运行:"
    echo "   bash ${SKILL_DIR}/scripts/restart.sh"
fi
echo "=========================================="
