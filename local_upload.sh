#!/bin/bash

# VideoContentOptimizer - 本地上传脚本
# 使用方法：
#   1. 将此脚本保存到本地电脑（如 ~/Desktop/upload.sh）
#   2. 修改 SERVER_IP 为你的服务器 IP
#   3. 运行: bash ~/Desktop/upload.sh

echo "🎬 VideoContentOptimizer - 本地上传到 GitHub"
echo "=============================================="
echo ""

# ========== 配置区域 ==========
# 服务器信息
SERVER_IP="<服务器IP>"  # ⚠️ 修改为你的服务器 IP
SERVER_USER="ubuntu"
REMOTE_FILE="/home/ubuntu/VideoContentOptimizer_FINAL.tar.gz"

# GitHub 信息（已填写）
GITHUB_USER="yunya1991"
REPO_NAME="VideoContentOptimizer"
REPO_DESC="🎬 一人公司(OPC)视频智能优化平台 - AI驱动的内容创作工具"
# ================================

echo "📋 配置信息:"
echo "   服务器: $SERVER_USER@$SERVER_IP"
echo "   本地目录: ~/Desktop/VideoContentOptimizer/"
echo "   GitHub 用户: $GITHUB_USER"
echo "   仓库名: $REPO_NAME"
echo ""

# 检查是否修改了服务器 IP
if [ "$SERVER_IP" = "<服务器IP>" ]; then
    echo "❌ 错误: 请先修改脚本中的 SERVER_IP 为你的服务器 IP"
    echo ""
    echo "修改方法："
    echo "  nano ~/Desktop/upload.sh"
    echo "  找到第 14 行: SERVER_IP=\"<服务器IP>\""
    echo "  修改为: SERVER_IP=\"你的实际IP\""
    exit 1
fi

# ========== 第 1 步：下载项目 ==========
echo "📥 第 1 步：从服务器下载项目..."
echo "=============================================="

if [ -f ~/Desktop/VideoContentOptimizer_FINAL.tar.gz ]; then
    echo "✅ 压缩包已存在，跳过下载"
else
    echo "正在下载: $SERVER_USER@$SERVER_IP:$REMOTE_FILE"
    scp $SERVER_USER@$SERVER_IP:$REMOTE_FILE ~/Desktop/
    if [ $? -ne 0 ]; then
        echo "❌ 下载失败！请检查："
        echo "  1. 服务器 IP 是否正确: $SERVER_IP"
        echo "  2. SSH 是否可连接: ssh $SERVER_USER@$SERVER_IP"
        echo "  3. 文件是否存在: $REMOTE_FILE"
        exit 1
    fi
    echo "✅ 下载完成！"
fi

# ========== 第 2 步：解压项目 ==========
echo ""
echo "📦 第 2 步：解压项目..."
echo "=============================================="

cd ~/Desktop/
if [ -d VideoContentOptimizer/ ]; then
    echo "✅ 目录已存在，跳过解压"
else
    echo "解压中..."
    tar -xzf VideoContentOptimizer_FINAL.tar.gz
    if [ $? -ne 0 ]; then
        echo "❌ 解压失败！"
        exit 1
    fi
    echo "✅ 解压完成！"
fi

cd ~/Desktop/VideoContentOptimizer/
echo "当前目录: $(pwd)"
echo "文件列表:"
ls -la | head -20

# ========== 第 3 步：检查 Git ==========
echo ""
echo "🔧 第 3 步：检查 Git..."
echo "=============================================="

if ! command -v git &> /dev/null; then
    echo "❌ 错误: 未安装 git"
    echo "请先安装: brew install git  (Mac) 或 apt install git (Linux)"
    exit 1
fi
echo "✅ Git 已安装: $(git --version)"

# 检查 gh CLI
if ! command -v gh &> /dev/null; then
    echo "⚠️  警告: 未安装 GitHub CLI (gh)"
    echo "建议安装: brew install gh (Mac) 或 https://cli.github.com/"
    echo "将使用普通 git 命令推送"
    USE_GH=false
else
    echo "✅ GitHub CLI 已安装: $(gh --version | head -1)"
    USE_GH=true
fi

# ========== 第 4 步：登录 GitHub ==========
if [ "$USE_GH" = true ]; then
    echo ""
    echo "🔐 第 4 步：检查 GitHub 登录状态..."
    echo "=============================================="
    
    gh auth status 2>&1 | grep -q "Logged in to github.com"
    if [ $? -ne 0 ]; then
        echo "⚠️  未登录 GitHub，启动登录..."
        echo "请按提示操作："
        echo "  1. 选择: GitHub.com"
        echo "  2. 选择: HTTPS"
        echo "  3. 选择: Login with a web browser"
        echo "  4. 复制显示的 code"
        echo "  5. 浏览器打开: https://github.com/login/device"
        echo "  6. 粘贴 code，点击 Continue"
        echo "  7. 点击 Authorize github"
        echo ""
        gh auth login --web
    else
        echo "✅ 已登录 GitHub"
        gh auth status
    fi
fi

# ========== 第 5 步：初始化 Git ==========
echo ""
echo "📦 第 5 步：初始化 Git 仓库..."
echo "=============================================="

if [ -d ".git" ]; then
    echo "✅ Git 仓库已初始化"
else
    echo "初始化 Git..."
    git init
    if [ $? -ne 0 ]; then
        echo "❌ Git 初始化失败"
        exit 1
    fi
    echo "✅ Git 初始化完成"
fi

# ========== 第 6 步：提交代码 ==========
echo ""
echo "💾 第 6 步：提交代码..."
echo "=============================================="

git add .
git commit -m "Initial commit: VideoContentOptimizer v2.0.0"
if [ $? -ne 0 ]; then
    echo "⚠️  提交失败，尝试允许空提交..."
    git commit -m "Initial commit: VideoContentOptimizer v2.0.0" --allow-empty
fi
echo "✅ 提交完成"

# ========== 第 7 步：设置主分支 ==========
echo ""
echo "🌿 第 7 步：设置主分支为 main..."
echo "=============================================="

git branch -M main
echo "✅ 主分支设置为 main"

# ========== 第 8 步：添加远程仓库 ==========
echo ""
echo "🔗 第 8 步：添加远程仓库..."
echo "=============================================="

git remote remove origin 2>/dev/null
if [ "$USE_GH" = true ]; then
    # 使用 gh 创建仓库并推送
    echo "使用 gh CLI 创建仓库并推送..."
    gh repo create $GITHUB_USER/$REPO_NAME --public --description "$REPO_DESC" --source=. --push 2>&1 | tee /tmp/gh_output.log
    if [ $? -eq 0 ]; then
        echo "✅ 仓库创建并推送成功！"
    else
        echo "⚠️  gh 创建失败，尝试手动推送..."
        git remote add origin https://github.com/$GITHUB_USER/$REPO_NAME.git
        git push -u origin main
    fi
else
    # 手动添加远程仓库
    echo "手动添加远程仓库..."
    git remote add origin https://github.com/$GITHUB_USER/$REPO_NAME.git
    
    echo ""
    echo "📤 推送代码..."
    echo "（如果需要认证，使用 GitHub Personal Access Token 作为密码）"
    git push -u origin main
fi

if [ $? -ne 0 ]; then
    echo "❌ 推送失败！常见原因："
    echo "  1. 仓库已存在但不为空 → 先运行: git pull origin main --rebase"
    echo "  2. 认证失败 → 需要使用 Personal Access Token"
    echo "     创建 Token: https://github.com/settings/tokens/new"
    echo "     权限: 勾选 repo (全部)"
    exit 1
fi

echo "✅ 推送完成！"

# ========== 第 9 步：验证 ==========
echo ""
echo "🎉 第 9 步：验证上传成功..."
echo "=============================================="

REPO_URL="https://github.com/$GITHUB_USER/$REPO_NAME"
echo "✅ 仓库地址: $REPO_URL"

if [ "$USE_GH" = true ]; then
    echo ""
    echo "在浏览器中打开仓库..."
    gh repo view --web 2>/dev/null || echo "请手动打开: $REPO_URL"
fi

echo ""
echo "📋 下一步操作："
echo "=============================================="
echo "1. 访问仓库: $REPO_URL"
echo "2. 确认 README.md 正确显示"
echo "3. 确认所有文件都已上传"
echo ""
echo "4. 发布到 SkillHub:"
echo "   访问: https://skillhub.cn/contest"
echo "   点击: '发布参赛 Skill'"
echo "   填写信息:"
echo "     - Skill 名称: video-ai-optimizer"
echo "     - 标题: 🎬 一人公司视频智能优化平台 - AI驱动的内容创作工具"
echo "     - 描述: 专为\"一人公司(OPC)\"设计的AI视频优化工具。一个人也能完成视频分析、智能优化、重生成和跨平台发布全流程。基于 FastAPI + Streamlit + LLM(DeepSeek) + Whisper + FFmpeg，节省 70% 制作时间，提升播放量 150%+。"
echo "     - GitHub URL: $REPO_URL"
echo "     - 标签: 内容创作, 个人提效, 产品研发"
echo "     - 分类: 内容创作 / 个人提效"
echo ""
echo "🎉 祝参赛顺利！冲 Top 10！🚀"
echo "=============================================="

