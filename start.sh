#!/bin/bash

# VideoContentOptimizer 启动脚本

set -e  # 遇到错误立即退出

echo "🎬 Video AI Optimizer - 启动脚本"
echo "================================"

# 检查 Python 版本
echo "📌 检查 Python 版本..."
python3 --version || { echo "❌ Python3 未安装"; exit 1; }

# 检查是否安装了依赖
echo "📦 检查依赖..."
if [ ! -f "requirements.txt" ]; then
    echo "❌ requirements.txt 不存在"
    exit 1
fi

# 创建虚拟环境（如果不存在）
if [ ! -d "venv" ]; then
    echo "🏗️  创建虚拟环境..."
    python3 -m venv venv
fi

# 激活虚拟环境
echo "🔧 激活虚拟环境..."
source venv/bin/activate

# 安装/更新依赖
echo "📦 安装依赖..."
pip install -r requirements.txt -q

# 检查 .env 文件
if [ ! -f ".env" ]; then
    echo "⚠️  .env 文件不存在，从示例创建..."
    cp .env.example .env
    echo "📝 请编辑 .env 文件，配置你的 API Key"
    echo "   至少设置: LLM_API_KEY"
fi

# 检查 ffmpeg
echo "🎙️ 检查 ffmpeg..."
if ! command -v ffmpeg &> /dev/null; then
    echo "⚠️  ffmpeg 未安装"
    echo "    Ubuntu/Debian: sudo apt install ffmpeg"
    echo "    macOS: brew install ffmpeg"
fi

# 启动选择
echo ""
echo "🚀 选择启动模式："
echo "   1) 启动 API 服务 (端口 8080)"
echo "   2) 启动 Web UI (端口 8501)"
echo "   3) 同时启动 API + Web UI"
echo "   4) Docker 启动 (需要 docker-compose)"
echo ""
read -p "请选择 [1-4]: " choice

case $choice in
    1)
        echo "🚀 启动 API 服务..."
        uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
        ;;
    2)
        echo "🚀 启动 Web UI..."
        streamlit run webui/main.py --server.port 8501
        ;;
    3)
        echo "🚀 同时启动 API + Web UI..."
        # 后台启动 API
        uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload &
        API_PID=$!
        # 前台启动 Web UI
        streamlit run webui/main.py --server.port 8501
        # 清理
        kill $API_PID 2>/dev/null || true
        ;;
    4)
        echo "🐳 使用 Docker 启动..."
        if command -v docker-compose &> /dev/null; then
            docker-compose up -d
            echo "✅ 服务已启动"
            echo "   Web UI: http://localhost:8501"
            echo "   API: http://localhost:8080"
        else
            echo "❌ docker-compose 未安装"
            exit 1
        fi
        ;;
    *)
        echo "❌ 无效选择"
        exit 1
        ;;
esac
