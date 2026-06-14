#!/usr/bin/env bash
# =============================================================================
# video-upload-browser — 启动脚本
# 用途: 启动 Xvfb + Chromium + noVNC 服务
# =============================================================================

set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_FILE="${HOME}/.config/chromium-video-upload/config.env"

# 加载配置
if [[ -f "${CONFIG_FILE}" ]]; then
    # shellcheck disable=SC1090
    source "${CONFIG_FILE}"
fi

VUB_DISPLAY="${VUB_DISPLAY:-:99}"
VUB_CDP_PORT="${VUB_CDP_PORT:-9222}"
VUB_NOVNC_PORT="${VUB_NOVNC_PORT:-6080}"
VUB_VNC_PORT="${VUB_VNC_PORT:-5900}"
VUB_USER_DATA="${VUB_USER_DATA:-${HOME}/.config/chromium-video-upload}"
VUB_SCREEN_WIDTH="${VUB_SCREEN_WIDTH:-1920}"
VUB_SCREEN_HEIGHT="${VUB_SCREEN_HEIGHT:-1080}"
VUB_BIND_IP="${VUB_BIND_IP:-127.0.0.1}"

LOG_DIR="${SKILL_DIR}/logs"
mkdir -p "${LOG_DIR}"

log() { echo "[$(date +'%H:%M:%S')] $1"; }
success() { echo "  ✅ $1"; }
error() { echo "  ❌ $1"; }

echo "=========================================="
echo " video-upload-browser — 启动服务"
echo "=========================================="
echo

# 检查是否已安装
if [[ ! -d "${VUB_USER_DATA}" ]]; then
    error "未检测到安装目录，请先运行 scripts/setup.sh"
    exit 1
fi

# 检测 Chromium 可执行文件
CHROMIUM_BIN="${VUB_CHROMIUM_BIN:-}"
if [[ -z "${CHROMIUM_BIN}" ]]; then
    CHROMIUM_BIN=$(command -v chromium || command -v chromium-browser || command -v google-chrome || echo "")
fi

if [[ -z "${CHROMIUM_BIN}" ]]; then
    error "未找到 Chromium 可执行文件"
    exit 1
fi

# 检测 noVNC 目录
NOVNC_DIR="${VUB_NOVNC_DIR:-${HOME}/.local/share/novnc-video-upload}"

# ── 停止已有进程（避免冲突） ─────────────────────────────────────────────
log "清理已有进程..."
killall Xvfb 2>/dev/null || true
killall x11vnc 2>/dev/null || true
killall chromium 2>/dev/null || true
killall chromium-browser 2>/dev/null || true
killall chrome 2>/dev/null || true
pkill -f "novnc" 2>/dev/null || true
pkill -f "launch.py" 2>/dev/null || true
sleep 1
success "进程清理完成"

# ── 启动 Xvfb ────────────────────────────────────────────────────────────
log "启动 Xvfb 虚拟显示器 (${VUB_DISPLAY}, ${VUB_SCREEN_WIDTH}x${VUB_SCREEN_HEIGHT})..."
Xvfb "${VUB_DISPLAY}" \
    -screen 0 "${VUB_SCREEN_WIDTH}x${VUB_SCREEN_HEIGHT}x24" \
    -ac +extension GLX +render -noreset \
    >> "${LOG_DIR}/xvfb.log" 2>&1 &
XVFB_PID=$!
sleep 1

if kill -0 "${XVFB_PID}" 2>/dev/null; then
    success "Xvfb 已启动 (PID=${XVFB_PID})"
    echo "${XVFB_PID}" > "${LOG_DIR}/xvfb.pid"
else
    error "Xvfb 启动失败"
    cat "${LOG_DIR}/xvfb.log" 2>/dev/null | tail -20
    exit 1
fi

# ── 启动 Chromium ────────────────────────────────────────────────────────
log "启动 Chromium (CDP 端口=${VUB_CDP_PORT})..."
export DISPLAY="${VUB_DISPLAY}"

"${CHROMIUM_BIN}" \
    --no-sandbox \
    --disable-gpu \
    --disable-dev-shm-usage \
    --disable-background-networking \
    --disable-default-apps \
    --disable-extensions \
    --disable-sync \
    --disable-translate \
    --no-first-run \
    --user-data-dir="${VUB_USER_DATA}/User Data" \
    --remote-debugging-address=127.0.0.1 \
    --remote-debugging-port="${VUB_CDP_PORT}" \
    --window-size="${VUB_SCREEN_WIDTH},${VUB_SCREEN_HEIGHT}" \
    --start-maximized \
    --disable-features=TranslateUI \
    --disable-infobars \
    --noerrdialogs \
    about:blank \
    >> "${LOG_DIR}/chromium.log" 2>&1 &
CHROMIUM_PID=$!
sleep 3

if kill -0 "${CHROMIUM_PID}" 2>/dev/null; then
    success "Chromium 已启动 (PID=${CHROMIUM_PID})"
    echo "${CHROMIUM_PID}" > "${LOG_DIR}/chromium.pid"
else
    error "Chromium 启动失败"
    cat "${LOG_DIR}/chromium.log" 2>/dev/null | tail -20
    exit 1
fi

# ── 启动 VNC + noVNC ─────────────────────────────────────────────────────
if [[ -d "${NOVNC_DIR}" ]] && command -v x11vnc &>/dev/null; then
    log "启动 x11vnc (VNC 端口=${VUB_VNC_PORT})..."

    # 创建密码文件（如果不存在）
    if [[ ! -f "${VUB_USER_DATA}/vnc_passwd" ]]; then
        VNC_PASS="$(cat ${VUB_USER_DATA}/vnc_password 2>/dev/null || openssl rand -hex 6)"
        x11vnc -storepasswd "${VNC_PASS}" "${VUB_USER_DATA}/vnc_passwd" >> "${LOG_DIR}/novnc.log" 2>&1 || true
        chmod 600 "${VUB_USER_DATA}/vnc_passwd" 2>/dev/null || true
    fi

    x11vnc \
        -display "${VUB_DISPLAY}" \
        -rfbport "${VUB_VNC_PORT}" \
        -rfbauth "${VUB_USER_DATA}/vnc_passwd" \
        -shared -forever -nopw -quiet \
        >> "${LOG_DIR}/novnc.log" 2>&1 &
    X11VNC_PID=$!
    sleep 1

    if kill -0 "${X11VNC_PID}" 2>/dev/null; then
        success "x11vnc 已启动 (PID=${X11VNC_PID})"
        echo "${X11VNC_PID}" > "${LOG_DIR}/x11vnc.pid"

        # 启动 noVNC Web 界面
        log "启动 noVNC (Web 端口=${VUB_NOVNC_PORT})..."

        # 寻找 launch.py
        LAUNCH_PY=""
        if [[ -f "${NOVNC_DIR}/utils/launch.py" ]]; then
            LAUNCH_PY="${NOVNC_DIR}/utils/launch.py"
        elif [[ -f "${NOVNC_DIR}/vnc.html" ]]; then
            LAUNCH_PY="python3 -m http.server"
        fi

        if [[ -n "${LAUNCH_PY}" && "${LAUNCH_PY}" != "python3 -m http.server" ]]; then
            python3 "${LAUNCH_PY}" \
                --listen "${VUB_NOVNC_PORT}" \
                --vnc "localhost:${VUB_VNC_PORT}" \
                >> "${LOG_DIR}/novnc.log" 2>&1 &
            NOVNC_PID=$!
            sleep 2

            if kill -0 "${NOVNC_PID}" 2>/dev/null; then
                success "noVNC 已启动 (PID=${NOVNC_PID})"
                echo "${NOVNC_PID}" > "${LOG_DIR}/novnc.pid"
            else
                error "noVNC 启动失败"
            fi
        elif [[ -f "${NOVNC_DIR}/vnc.html" ]]; then
            # 用简单的 HTTP server 提供 noVNC 静态文件
            cd "${NOVNC_DIR}"
            python3 -m http.server "${VUB_NOVNC_PORT}" --bind "${VUB_BIND_IP}" \
                >> "${LOG_DIR}/novnc.log" 2>&1 &
            NOVNC_PID=$!
            cd - > /dev/null
            sleep 2

            if kill -0 "${NOVNC_PID}" 2>/dev/null; then
                success "noVNC HTTP Server 已启动 (PID=${NOVNC_PID})"
                echo "${NOVNC_PID}" > "${LOG_DIR}/novnc.pid"
            else
                error "noVNC 启动失败"
            fi
        fi
    else
        error "x11vnc 启动失败"
    fi
else
    echo "  ⚠️  noVNC/x11vnc 未安装，跳过 Web 界面（CDP 依然可用）"
fi

# ── 等待 CDP 就绪 ───────────────────────────────────────────────────────
log "等待 CDP 接口就绪..."
for i in $(seq 1 30); do
    if curl -s "http://127.0.0.1:${VUB_CDP_PORT}/json/version" | grep -q "Browser" &>/dev/null; then
        break
    fi
    sleep 1
done

echo
echo "=========================================="
echo "🎉 所有服务启动完成"
echo "=========================================="
echo
echo "📌 服务信息:"
echo "   CDP 地址       : http://127.0.0.1:${VUB_CDP_PORT}"
if [[ -f "${LOG_DIR}/novnc.pid" ]]; then
    echo "   noVNC Web 地址 : http://<服务器IP>:${VUB_NOVNC_PORT}/vnc.html"
    VNC_PASSWORD=$(cat "${VUB_USER_DATA}/vnc_password" 2>/dev/null || echo "<查看 ${VUB_USER_DATA}/vnc_password>")
    echo "   VNC 密码       : ${VNC_PASSWORD}"
fi
echo "   Chromium 数据  : ${VUB_USER_DATA}/User Data"
echo "   日志目录        : ${LOG_DIR}"
echo
echo "🎯 下一步:"
echo "   1. 在浏览器访问 noVNC 完成各平台登录"
echo "   2. 在 VideoContentOptimizer 中调用 /api/v2/browser-upload/* API"
echo "   3. 运行 bash ${SKILL_DIR}/scripts/health-check.sh 检查服务状态"
echo
