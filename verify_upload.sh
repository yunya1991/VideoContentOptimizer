#!/bin/bash

# VideoContentOptimizer - 上传验证脚本
# 使用方法：在本地电脑运行：bash verify_upload.sh

echo "🎬 VideoContentOptimizer - 上传验证"
echo "=============================================="
echo ""

# ========== 配置区域 ==========
GITHUB_USER="yunyi1991"
REPO_NAME="VideoContentOptimizer"
REPO_URL="https://github.com/$GITHUB_USER/$REPO_NAME"
# ================================

echo "📋 验证信息:"
echo "   仓库地址: $REPO_URL"
echo ""

# ========== 第 1 步：检查本地文件 ==========
echo "📂 第 1 步：检查本地文件..."
echo "=============================================="

if [ ! -d "$HOME/Desktop/VideoContentOptimizer" ]; then
    echo "❌ 错误: 本地目录不存在"
    echo "   请先下载并解压项目到: ~/Desktop/VideoContentOptimizer/"
    exit 1
fi

cd ~/Desktop/VideoContentOptimizer/

echo "✅ 目录存在: $(pwd)"
echo ""
echo "📋 关键文件检查:"

declare -A files=(
    ["README.md"]="项目说明"
    ["SKILL.md"]="Skill 定义文件"
    ["requirements.txt"]="依赖清单"
    ["app/main.py"]="FastAPI 主应用"
    ["webui/main.py"]="Streamlit Web UI"
    ["docker-compose.yml"]="Docker 配置"
)

for file in "${!files[@]}"; do
    if [ -f "$file" ]; then
        echo "   ✅ ${files[$file]}: $file"
    else
        echo "   ❌ 缺失: $file (${files[$file]})"
    fi
done

echo ""
echo "📊 文件统计:"
TOTAL_FILES=$(find . -type f | wc -l)
echo "   总文件数: $TOTAL_FILES"

if [ $TOTAL_FILES -lt 50 ]; then
    echo "   ⚠️  警告: 文件数较少，可能解压不完整"
else
    echo "   ✅ 文件数量正常"
fi

# ========== 第 2 步：检查 Git 状态 ==========
echo ""
echo "🔧 第 2 步：检查 Git 状态..."
echo "=============================================="

if [ ! -d ".git" ]; then
    echo "❌ 错误: 未初始化 Git"
    echo "   请先运行: git init"
    exit 1
fi

echo "✅ Git 仓库已初始化"

# 检查远程仓库
REMOTE_URL=$(git remote get-url origin 2>/dev/null)
if [ -z "$REMOTE_URL" ]; then
    echo "❌ 错误: 未设置远程仓库"
    echo "   请运行: git remote add origin $REPO_URL.git"
    exit 1
fi

echo "✅ 远程仓库: $REMOTE_URL"

# 检查主分支
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" != "main" ]; then
    echo "⚠️  警告: 当前分支是 $CURRENT_BRANCH，不是 main"
    echo "   请运行: git branch -M main"
else
    echo "✅ 主分支: main"
fi

# ========== 第 3 步：检查 GitHub 仓库 ==========
echo ""
echo "🌐 第 3 步：检查 GitHub 仓库..."
echo "=============================================="

if ! command -v gh &> /dev/null; then
    echo "⚠️  警告: 未安装 GitHub CLI (gh)"
    echo "   将使用 curl 检查..."
    
    # 使用 curl 检查
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$REPO_URL")
    if [ "$HTTP_CODE" = "200" ]; then
        echo "✅ 仓库可访问: $REPO_URL"
    else
        echo "❌ 仓库不可访问 (HTTP $HTTP_CODE): $REPO_URL"
        echo "   请检查仓库是否已创建"
        exit 1
    fi
else
    # 使用 gh 检查
    gh repo view $GITHUB_USER/$REPO_NAME &>/dev/null
    if [ $? -eq 0 ]; then
        echo "✅ 仓库存在: $REPO_URL"
    else
        echo "❌ 仓库不存在或无法访问"
        echo "   请先创建仓库: gh repo create $REPO_NAME --public --source=. --push"
        exit 1
    fi
fi

# ========== 第 4 步：验证关键文件在 GitHub ==========
echo ""
echo "📄 第 4 步：验证 GitHub 上的文件..."
echo "=============================================="

# 使用 GitHub API 检查
TOKEN=$(gh auth token 2>/dev/null)
if [ -z "$TOKEN" ]; then
    echo "⚠️  未登录 gh，跳过文件验证"
    echo "   请运行: gh auth login"
else
    # 检查 README.md
    CHECK_URL="https://api.github.com/repos/$GITHUB_USER/$REPO_NAME/contents/README.md"
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: token $TOKEN" "$CHECK_URL")
    
    if [ "$HTTP_CODE" = "200" ]; then
        echo "   ✅ README.md 已上传"
    else
        echo "   ❌ README.md 未找到 (HTTP $HTTP_CODE)"
    fi
    
    # 检查 SKILL.md
    CHECK_URL="https://api.github.com/repos/$GITHUB_USER/$REPO_NAME/contents/SKILL.md"
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: token $TOKEN" "$CHECK_URL")
    
    if [ "$HTTP_CODE" = "200" ]; then
        echo "   ✅ SKILL.md 已上传"
    else
        echo "   ❌ SKILL.md 未找到 (HTTP $HTTP_CODE)"
    fi
fi

# ========== 第 5 步：推送到 GitHub ==========
echo ""
echo "📤 第 5 步：推送到 GitHub（如果需要）..."
echo "=============================================="

# 检查是否有未推送的提交
UNPUSHED=$(git log origin/main..HEAD 2>/dev/null | wc -l)
if [ $UNPUSHED -gt 0 ]; then
    echo "⚠️  有 $UNPUSHED 个提交未推送"
    echo ""
    read -p "是否现在推送？(y/N): " CONFIRM
    if [ "$CONFIRM" = "y" ] || [ "$CONFIRM" = "Y" ]; then
        echo "推送中..."
        git push -u origin main
        if [ $? -eq 0 ]; then
            echo "✅ 推送成功！"
        else
            echo "❌ 推送失败！"
            echo "   尝试使用: git push -u origin main --force"
        fi
    else
        echo "跳过推送"
    fi
else
    echo "✅ 所有提交已推送"
fi

# ========== 第 6 步：生成总结报告 ==========
echo ""
echo "📊 验证总结报告"
echo "=============================================="

echo ""
echo "✅ 本地文件: $TOTAL_FILES 个文件"
echo "✅ Git 仓库: 已初始化，主分支: $CURRENT_BRANCH"
echo "✅ 远程仓库: $REMOTE_URL"
echo "✅ GitHub 仓库: $REPO_URL"

echo ""
echo "🎯 下一步操作："
echo "=============================================="
echo "1. 访问仓库确认文件:"
echo "   $REPO_URL"
echo ""
echo "2. 确认 README.md 正确显示"
echo "   - 标题、描述、截图都应该正常"
echo ""
echo "3. 访问 SkillHub 发布参赛:"
echo "   https://skillhub.cn/contest"
echo ""
echo "4. 点击 '发布参赛 Skill'"
echo ""
echo "5. 填写信息（照抄以下）:"
echo "   - Skill 名称: video-ai-optimizer"
echo "   - 标题: 🎬 一人公司视频智能优化平台 - AI驱动的内容创作工具"
echo "   - 描述: 专为\"一人公司(OPC)\"设计的AI视频优化工具。一个人也能完成视频分析、智能优化、重生成和跨平台发布全流程。基于 FastAPI + Streamlit + LLM(DeepSeek) + Whisper + FFmpeg，节省 70% 制作时间，提升播放量 150%+。"
echo "   - GitHub URL: $REPO_URL"
echo "   - 标签: 内容创作, 个人提效, 产品研发"
echo "   - 分类: 内容创作 / 个人提效"
echo ""
echo "6. 提交参赛 🎉"
echo ""
echo "7. 社区拉票:"
echo "   - 虾友会社区发帖"
echo "   - 邀请朋友点赞收藏"
echo "   - 分享到社交媒体"
echo ""
echo "=============================================="
echo "🎉 验证完成！准备冲 Top 10！🚀"
echo "=============================================="
