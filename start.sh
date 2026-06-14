#!/bin/bash
#
# VideoContentOptimizer - 一键启动脚本
#
# 功能:
#   1. 检查环境变量（SECRET_KEY / JWT_SECRET / CDP_URL）
#   2. 检查 Python 依赖
#   3. 可选：启动 CDP 浏览器远程环境（skill/video-upload-browser/scripts/start.sh）
#   4. 启动 FastAPI 服务（默认 8080）
#
# 用法:
#   ./start.sh                    # 使用默认配置，只启动 API
#   ./start.sh --with-browser     # 同时启动远程浏览器（需 Linux + Xvfb + Chromium）
#   ./start.sh --port 8000        # 指定端口
#   ./start.sh --reinstall        # 重新安装依赖
#   ./start.sh --help             # 查看帮助
#
# 注意:
#   - 若未准备 .env，脚本会自动基于 .env.example 生成并提示替换弱密钥
#   - CDP 浏览器在 macOS 下不支持一键部署（仅 Linux 支持）

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_ROOT"

# ─── 参数解析 ─────────────────────────────────────────────────
WITH_BROWSER=0
PORT=8080
REINSTALL=0
HELP=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --with-browser) WITH_BROWSER=1; shift ;;
        --port) PORT="$2"; shift 2 ;;
        --reinstall) REINSTALL=1; shift ;;
        --help|-h) HELP=1; shift ;;
        *) echo "未知参数: $1"; exit 1 ;;
    esac
done

if [[ $HELP -eq 1 ]]; then
    grep '^#' "$0" | head -30
    exit 0
fi

# ─── 颜色工具 ─────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'

info()    { echo -e "${GREEN}[INFO]${NC} $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $*"; }
fatal()   { echo -e "${RED}[FATAL]${NC} $*"; exit 1; }

# ─── 1. 检查 Python 版本 ─────────────────────────────────────
info "检查 Python 环境..."
PY=python3
if ! command -v "$PY" >/dev/null 2>&1; then
    fatal "未找到 python3，请先安装 Python 3.10+"
fi
$PY -c "import sys; assert sys.version_info >= (3, 10), '需要 Python 3.10+'" || \
    fatal "Python 版本过低，需 3.10+"
info "Python 版本: $($PY --version)"

# ─── 2. 检查 / 安装依赖 ────────────────────────────────────
need_install=0
if [[ $REINSTALL -eq 1 ]]; then
    need_install=1
else
    $PY -c "import fastapi, starlette, pydantic, pydantic_settings" 2>/dev/null || need_install=1
fi

if [[ $need_install -eq 1 ]]; then
    warn "依赖未完整安装，开始执行: pip install -r requirements.txt"
    $PY -m pip install --upgrade pip
    $PY -m pip install -r requirements.txt || fatal "依赖安装失败"
    info "依赖安装完成"
else
    info "依赖已就绪"
fi

# ─── 3. 检查 .env 与敏感配置 ──────────────────────────────
info "检查环境变量..."
if [[ ! -f .env ]]; then
    warn "未找到 .env，基于 .env.example 生成"
    if [[ ! -f .env.example ]]; then
        fatal ".env.example 也不存在，项目目录可能不正确"
    fi
    cp .env.example .env
    warn "请修改 .env 中的 SECRET_KEY / JWT_SECRET 为随机值，按回车继续..."
    read -r
fi

# 校验弱密钥
if grep -Eq '^(SECRET_KEY|JWT_SECRET)\s*=\s*(your-secret-key|your-jwt-secret)' .env; then
    warn "检测到默认密钥，建议立即替换: .env 中的 SECRET_KEY / JWT_SECRET"
fi

# ─── 4. 可选：启动远程浏览器 Skill（仅 Linux） ─────────
if [[ $WITH_BROWSER -eq 1 ]]; then
    OS_NAME="$(uname -s)"
    if [[ "$OS_NAME" != "Linux" ]]; then
        warn "--with-browser 仅支持 Linux（当前: $OS_NAME），跳过浏览器启动"
    else
        info "启动远程浏览器 (CDP: http://127.0.0.1:9223, noVNC: :6080)"
        cd "$PROJECT_ROOT/skill/video-upload-browser"
        if [[ -x scripts/start.sh ]]; then
            bash scripts/start.sh || warn "浏览器启动失败，继续启动 API"
        else
            warn "未找到 scripts/start.sh，跳过浏览器启动"
        fi
        cd "$PROJECT_ROOT"
    fi
fi

# ─── 5. 启动 FastAPI ──────────────────────────────────────
info "启动 FastAPI 服务: http://127.0.0.1:${PORT}"
info "API 文档: http://127.0.0.1:${PORT}/docs"

exec "$PY" -m uvicorn app.main:app \
    --host 0.0.0.0 \
    --port "$PORT" \
    --log-level info
