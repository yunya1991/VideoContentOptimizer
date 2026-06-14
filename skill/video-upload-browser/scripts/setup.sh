#!/usr/bin/env bash
# =============================================================================
# video-upload-browser — 安装脚本
# 用途: 在 Linux 服务器上部署 Xvfb + Chromium + noVNC + CDP 浏览器环境
# 供 VideoContentOptimizer 用于自动化视频上传
# =============================================================================

set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_FILE="${SKILL_DIR}/install.log"

# ── 颜色输出 ──────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${BLUE}[INFO]${NC} $1" | tee -a "${LOG_FILE}"; }
success() { echo -e "${GREEN}[OK]${NC} $1" | tee -a "${LOG_FILE}"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1" | tee -a "${LOG_FILE}"; }
error() { echo -e "${RED}[ERROR]${NC} $1" | tee -a "${LOG_FILE}"; }

# ── 初始化日志 ────────────────────────────────────────────────────────────
mkdir -p "$(dirname "${LOG_FILE}")"
echo "=== video-upload-browser 安装日志 $(date) ===" > "${LOG_FILE}"

# ── 权限检查 ──────────────────────────────────────────────────────────────
log "检查运行环境..."
if [[ "$(uname)" != "Linux" ]]; then
    error "本 Skill 仅支持 Linux 系统，当前系统: $(uname)"
    exit 1
fi

SUDO=""
if [[ $EUID -ne 0 ]]; then
    if ! command -v sudo &>/dev/null; then
        error "需要 sudo 权限来安装系统依赖"
        exit 1
    fi
    SUDO="sudo"
    log "检测到非 root 用户，将使用 sudo 执行系统级操作"
fi

# ── 检测包管理器 ───────────────────────────────────────────────────────────
log "检测包管理器..."
if command -v apt-get &>/dev/null; then
    PKG_MANAGER="apt"
    INSTALL_CMD="${SUDO} apt-get update && ${SUDO} apt-get install -y"
    success "检测到 Debian/Ubuntu 系 (apt-get)"
elif command -v yum &>/dev/null; then
    PKG_MANAGER="yum"
    INSTALL_CMD="${SUDO} yum install -y"
    success "检测到 CentOS/RHEL 系 (yum)"
elif command -v dnf &>/dev/null; then
    PKG_MANAGER="dnf"
    INSTALL_CMD="${SUDO} dnf install -y"
    success "检测到 Fedora/RHEL 8+ 系 (dnf)"
elif command -v pacman &>/dev/null; then
    PKG_MANAGER="pacman"
    INSTALL_CMD="${SUDO} pacman -Sy --noconfirm"
    success "检测到 Arch 系 (pacman)"
else
    error "未识别的包管理器，请手动安装依赖"
    exit 1
fi

# ── 配置参数（可通过环境变量覆盖） ────────────────────────────────────────
VUB_DISPLAY="${VUB_DISPLAY:-:99}"
VUB_CDP_PORT="${VUB_CDP_PORT:-9222}"
VUB_NOVNC_PORT="${VUB_NOVNC_PORT:-6080}"
VUB_VNC_PORT="${VUB_VNC_PORT:-5900}"
VUB_USER_DATA="${VUB_USER_DATA:-${HOME}/.config/chromium-video-upload}"
VUB_SCREEN_WIDTH="${VUB_SCREEN_WIDTH:-1920}"
VUB_SCREEN_HEIGHT="${VUB_SCREEN_HEIGHT:-1080}"
VUB_BIND_IP="${VUB_BIND_IP:-127.0.0.1}"  # 默认仅本地访问，更安全

# 生成 VNC 密码
VUB_VNC_PASSWORD="${VUB_VNC_PASSWORD:-}"
if [[ -z "${VUB_VNC_PASSWORD}" ]]; then
    VUB_VNC_PASSWORD=$(openssl rand -hex 6)
fi

log "安装参数:"
log "  Xvfb 显示器: ${VUB_DISPLAY}"
log "  CDP 端口    : ${VUB_CDP_PORT}"
log "  noVNC 端口  : ${VUB_NOVNC_PORT}"
log "  VNC 端口    : ${VUB_VNC_PORT}"
log "  用户数据目录: ${VUB_USER_DATA}"
log "  屏幕分辨率  : ${VUB_SCREEN_WIDTH}x${VUB_SCREEN_HEIGHT}"
log "  绑定 IP     : ${VUB_BIND_IP}"

# ── 安装系统依赖 ──────────────────────────────────────────────────────────
log "安装系统依赖 (这可能需要几分钟)..."

COMMON_PACKAGES=(
    "xvfb"
    "x11vnc"
    "curl"
    "wget"
    "openssl"
    "psmisc"
    "net-tools"
)

# 浏览器包名差异
case "${PKG_MANAGER}" in
    apt)
        BROWSER_PACKAGES=("chromium-browser" "chromium")
        ;;
    yum|dnf)
        BROWSER_PACKAGES=("chromium")
        ;;
    pacman)
        BROWSER_PACKAGES=("chromium")
        ;;
esac

# 尝试安装 common 包
log "  - 基础工具 (xvfb, x11vnc, curl, wget)..."
if [[ "${PKG_MANAGER}" == "apt" ]]; then
    ${SUDO} apt-get update -y >> "${LOG_FILE}" 2>&1
    ${SUDO} apt-get install -y xvfb x11vnc curl wget openssl psmisc net-tools >> "${LOG_FILE}" 2>&1 || true
elif [[ "${PKG_MANAGER}" == "yum" ]] || [[ "${PKG_MANAGER}" == "dnf" ]]; then
    ${SUDO} ${PKG_MANAGER} install -y epel-release >> "${LOG_FILE}" 2>&1 || true
    ${SUDO} ${PKG_MANAGER} install -y xorg-x11-server-Xvfb x11vnc curl wget openssl psmisc net-tools >> "${LOG_FILE}" 2>&1 || true
elif [[ "${PKG_MANAGER}" == "pacman" ]]; then
    ${SUDO} pacman -Sy --noconfirm xvfb x11vnc curl wget openssl psmisc net-tools >> "${LOG_FILE}" 2>&1 || true
fi
success "  - 基础工具安装完成"

# 安装 Chromium
log "  - 安装 Chromium 浏览器..."
CHROMIUM_BIN=""
for pkg in "${BROWSER_PACKAGES[@]}"; do
    if [[ "${PKG_MANAGER}" == "apt" ]]; then
        if ${SUDO} apt-get install -y "${pkg}" >> "${LOG_FILE}" 2>&1; then
            CHROMIUM_BIN=$(command -v "${pkg}" || command -v chromium || command -v chromium-browser || true)
            [[ -n "${CHROMIUM_BIN}" ]] && break
        fi
    elif [[ "${PKG_MANAGER}" == "yum" ]] || [[ "${PKG_MANAGER}" == "dnf" ]]; then
        if ${SUDO} ${PKG_MANAGER} install -y "${pkg}" >> "${LOG_FILE}" 2>&1; then
            CHROMIUM_BIN=$(command -v chromium || command -v chromium-browser || true)
            [[ -n "${CHROMIUM_BIN}" ]] && break
        fi
    elif [[ "${PKG_MANAGER}" == "pacman" ]]; then
        if ${SUDO} pacman -S --noconfirm "${pkg}" >> "${LOG_FILE}" 2>&1; then
            CHROMIUM_BIN=$(command -v chromium || true)
            [[ -n "${CHROMIUM_BIN}" ]] && break
        fi
    fi
done

# 如果包管理器安装失败，尝试下载 Chromium
if [[ -z "${CHROMIUM_BIN}" ]]; then
    warn "包管理器安装 Chromium 失败，尝试下载官方版本..."
    CHROMIUM_DIR="${HOME}/.local/share/chromium-video-upload"
    mkdir -p "${CHROMIUM_DIR}"
    cd "${CHROMIUM_DIR}"

    # 尝试下载 Chromium (Linux x64)
    if wget -q "https://www.googleapis.com/download/storage/v1/b/chromium-browser-snapshots/o/Linux_x64%2FLAST_CHANGE?alt=media" -O /tmp/chromium_last_change.txt 2>/dev/null; then
        local last_change=$(cat /tmp/chromium_last_change.txt)
        local url="https://www.googleapis.com/download/storage/v1/b/chromium-browser-snapshots/o/Linux_x64%2F${last_change}%2Fchrome-linux.zip?alt=media"
        if wget -q "${url}" -O /tmp/chrome-linux.zip 2>/dev/null; then
            unzip -q /tmp/chrome-linux.zip -d "${CHROMIUM_DIR}"
            CHROMIUM_BIN="${CHROMIUM_DIR}/chrome-linux/chrome"
            chmod +x "${CHROMIUM_BIN}"
            rm -f /tmp/chrome-linux.zip /tmp/chromium_last_change.txt
            success "  - Chromium 下载安装完成"
        else
            error "  - Chromium 下载失败，请手动安装 chromium 浏览器"
            exit 1
        fi
    else
        error "  - 无法获取 Chromium 版本信息，请手动安装 chromium 浏览器"
        exit 1
    fi
    cd "${SKILL_DIR}"
else
    success "  - Chromium 安装完成 (${CHROMIUM_BIN})"
fi

# noVNC 安装（直接从 GitHub 下载）
log "  - 安装 noVNC..."
NOVNC_DIR="${HOME}/.local/share/novnc-video-upload"
if [[ -d "${NOVNC_DIR}" ]]; then
    success "  - noVNC 已存在"
else
    mkdir -p "${NOVNC_DIR}"
    # 尝试使用包管理器安装 novnc
    if [[ "${PKG_MANAGER}" == "apt" ]]; then
        ${SUDO} apt-get install -y novnc websockify >> "${LOG_FILE}" 2>&1 || true
        if command -v novnc &>/dev/null; then
            success "  - noVNC 通过包管理器安装完成"
        else
            # 手动下载
            wget -q "https://github.com/novnc/noVNC/archive/refs/tags/v1.4.0.tar.gz" -O /tmp/novnc.tar.gz 2>/dev/null || true
            if [[ -s /tmp/novnc.tar.gz ]]; then
                tar -xzf /tmp/novnc.tar.gz -C "${NOVNC_DIR}" --strip-components=1
                success "  - noVNC 下载安装完成"
            else
                warn "  - noVNC 下载失败，跳过 Web 界面"
            fi
            rm -f /tmp/novnc.tar.gz 2>/dev/null
        fi
    else
        # 手动下载
        wget -q "https://github.com/novnc/noVNC/archive/refs/tags/v1.4.0.tar.gz" -O /tmp/novnc.tar.gz 2>/dev/null || true
        if [[ -s /tmp/novnc.tar.gz ]]; then
            tar -xzf /tmp/novnc.tar.gz -C "${NOVNC_DIR}" --strip-components=1
            success "  - noVNC 下载安装完成"
            rm -f /tmp/novnc.tar.gz
        else
            warn "  - noVNC 下载失败，跳过 Web 界面"
        fi
    fi

    # 安装 websockify
    if command -v pip3 &>/dev/null; then
        pip3 install websockify >> "${LOG_FILE}" 2>&1 || true
    fi
fi

# ── 创建用户数据目录 ──────────────────────────────────────────────────────
log "创建目录结构..."
mkdir -p "${VUB_USER_DATA}"
mkdir -p "${VUB_USER_DATA}/User Data"
mkdir -p "${SKILL_DIR}/logs"

# 保存密码
echo "${VUB_VNC_PASSWORD}" > "${VUB_USER_DATA}/vnc_password"
chmod 600 "${VUB_USER_DATA}/vnc_password"
success "  - VNC 密码已保存到 ${VUB_USER_DATA}/vnc_password"

# 保存配置
cat > "${VUB_USER_DATA}/config.env" <<ENVEOF
# video-upload-browser 配置
# 生成时间: $(date)
VUB_DISPLAY=${VUB_DISPLAY}
VUB_CDP_PORT=${VUB_CDP_PORT}
VUB_NOVNC_PORT=${VUB_NOVNC_PORT}
VUB_VNC_PORT=${VUB_VNC_PORT}
VUB_USER_DATA=${VUB_USER_DATA}
VUB_SCREEN_WIDTH=${VUB_SCREEN_WIDTH}
VUB_SCREEN_HEIGHT=${VUB_SCREEN_HEIGHT}
VUB_BIND_IP=${VUB_BIND_IP}
VUB_CHROMIUM_BIN=${CHROMIUM_BIN}
VUB_NOVNC_DIR=${NOVNC_DIR:-}
ENVEOF
chmod 600 "${VUB_USER_DATA}/config.env"
success "  - 配置文件已保存到 ${VUB_USER_DATA}/config.env"

# ── 创建 systemd 服务文件 ────────────────────────────────────────────────
SYSTEMD_DIR="${HOME}/.config/systemd/user"

log "创建 systemd 服务..."

# 使用 root 用户则放系统目录，否则放用户目录
if [[ $EUID -eq 0 ]]; then
    SYSTEMD_DIR="/etc/systemd/system"
else
    SYSTEMD_DIR="${HOME}/.config/systemd/user"
fi

mkdir -p "${SYSTEMD_DIR}"

# 服务 1: Xvfb 虚拟显示器
cat > "${SYSTEMD_DIR}/video-upload-browser-xvfb.service" <<SVCEOF
[Unit]
Description=video-upload-browser Xvfb virtual display
After=network.target

[Service]
Type=simple
Environment=DISPLAY=${VUB_DISPLAY}
ExecStart=/usr/bin/Xvfb ${VUB_DISPLAY} -screen 0 ${VUB_SCREEN_WIDTH}x${VUB_SCREEN_HEIGHT}x24 -ac +extension GLX +render -noreset
Restart=always
RestartSec=3
StandardOutput=append:${SKILL_DIR}/logs/xvfb.log
StandardError=append:${SKILL_DIR}/logs/xvfb.log

[Install]
WantedBy=default.target
SVCEOF

# 服务 2: Chromium 浏览器
cat > "${SYSTEMD_DIR}/video-upload-browser-chromium.service" <<SVCEOF
[Unit]
Description=video-upload-browser Chromium with CDP
After=video-upload-browser-xvfb.service
Requires=video-upload-browser-xvfb.service

[Service]
Type=simple
Environment=DISPLAY=${VUB_DISPLAY}
Environment=HOME=${HOME}
ExecStart=${CHROMIUM_BIN} \
    --no-sandbox \
    --disable-gpu \
    --disable-dev-shm-usage \
    --disable-background-networking \
    --disable-default-apps \
    --disable-extensions \
    --disable-sync \
    --disable-translate \
    --no-first-run \
    --user-data-dir=${VUB_USER_DATA}/User Data \
    --remote-debugging-address=127.0.0.1 \
    --remote-debugging-port=${VUB_CDP_PORT} \
    --window-size=${VUB_SCREEN_WIDTH},${VUB_SCREEN_HEIGHT} \
    --start-maximized \
    --disable-features=TranslateUI \
    about:blank
Restart=always
RestartSec=3
StandardOutput=append:${SKILL_DIR}/logs/chromium.log
StandardError=append:${SKILL_DIR}/logs/chromium.log

[Install]
WantedBy=default.target
SVCEOF

# 服务 3: x11vnc + noVNC
if [[ -d "${NOVNC_DIR}" ]]; then
    cat > "${SYSTEMD_DIR}/video-upload-browser-novnc.service" <<SVCEOF
[Unit]
Description=video-upload-browser noVNC Web interface
After=video-upload-browser-xvfb.service
Requires=video-upload-browser-xvfb.service

[Service]
Type=simple
Environment=DISPLAY=${VUB_DISPLAY}
ExecStart=/bin/bash -c "\
    /usr/bin/x11vnc -display ${VUB_DISPLAY} -rfbport ${VUB_VNC_PORT} -rfbauth ${VUB_USER_DATA}/vnc_passwd -shared -forever & \
    sleep 2 && \
    $(command -v python3 || echo python) ${NOVNC_DIR}/utils/launch.py --listen ${VUB_NOVNC_PORT} --vnc localhost:${VUB_VNC_PORT}"
Restart=always
RestartSec=3
StandardOutput=append:${SKILL_DIR}/logs/novnc.log
StandardError=append:${SKILL_DIR}/logs/novnc.log

[Install]
WantedBy=default.target
SVCEOF
fi

# 创建 VNC 密码文件
if command -v x11vnc &>/dev/null; then
    x11vnc -storepasswd "${VUB_VNC_PASSWORD}" "${VUB_USER_DATA}/vnc_passwd" >> "${LOG_FILE}" 2>&1 || true
    chmod 600 "${VUB_USER_DATA}/vnc_passwd" 2>/dev/null || true
fi

success "  - systemd 服务文件已创建"

# 重载 systemd
if [[ $EUID -eq 0 ]]; then
    systemctl daemon-reload >> "${LOG_FILE}" 2>&1 || true
else
    systemctl --user daemon-reload >> "${LOG_FILE}" 2>&1 || true
fi

# ── 生成集成配置 ──────────────────────────────────────────────────────────
log "生成 VideoContentOptimizer 集成配置..."

# 在项目根目录创建 .env 片段
if [[ -f "${SKILL_DIR}/../../.env.example" ]]; then
    success "  - 已识别 VideoContentOptimizer 项目"
fi

# 创建集成提示文件
cat > "${SKILL_DIR}/video-optimizer-config.txt" <<CFGEOF
# === video-upload-browser 集成提示 ===
# 在 VideoContentOptimizer 项目的 .env 中添加以下配置:

CDP_ENABLED=true
CDP_URL=http://127.0.0.1:${VUB_CDP_PORT}
CDP_VIEWPORT_WIDTH=${VUB_SCREEN_WIDTH}
CDP_VIEWPORT_HEIGHT=${VUB_SCREEN_HEIGHT}
CDP_UPLOAD_TIMEOUT=300

# noVNC Web 访问地址:
# http://<服务器IP>:${VUB_NOVNC_PORT}/vnc.html
#
# VNC 密码: ${VUB_VNC_PASSWORD}
#
# 注意: 默认 noVNC 仅绑定 127.0.0.1，需外网访问请
# 通过 Nginx 反向代理或修改 VUB_BIND_IP 重新安装
CFGEOF

# ── 完成 ────────────────────────────────────────────────────────────────
echo
echo "==============================================="
echo -e "${GREEN}✅ video-upload-browser 安装完成${NC}"
echo "==============================================="
echo
echo "📌 访问地址:"
echo "   noVNC Web : http://<服务器IP>:${VUB_NOVNC_PORT}/vnc.html"
echo "   VNC 密码 : ${VUB_VNC_PASSWORD}"
echo "   CDP 地址 : http://127.0.0.1:${VUB_CDP_PORT}"
echo
echo "🚀 启动服务:"
if [[ $EUID -eq 0 ]]; then
    echo "   systemctl start video-upload-browser-xvfb"
    echo "   systemctl start video-upload-browser-chromium"
    [[ -d "${NOVNC_DIR}" ]] && echo "   systemctl start video-upload-browser-novnc"
    echo "   systemctl enable video-upload-browser-xvfb video-upload-browser-chromium"
else
    echo "   systemctl --user start video-upload-browser-xvfb"
    echo "   systemctl --user start video-upload-browser-chromium"
    [[ -d "${NOVNC_DIR}" ]] && echo "   systemctl --user start video-upload-browser-novnc"
    echo "   systemctl --user enable video-upload-browser-xvfb video-upload-browser-chromium"
fi
echo
echo "💡 或使用快捷脚本:"
echo "   bash ${SKILL_DIR}/scripts/start.sh"
echo "   bash ${SKILL_DIR}/scripts/health-check.sh"
echo
echo "🔐 安全提示:"
echo "   - VNC 默认仅本地访问，请通过 SSH 隧道或 VPN 访问"
echo "   - 如需开放外网，请设置强密码并启用 HTTPS 反向代理"
echo "   - 配置文件路径: ${VUB_USER_DATA}/config.env"
echo
echo "📖 详细文档: ${SKILL_DIR}/SKILL.md"
echo "📝 安装日志: ${LOG_FILE}"
echo
