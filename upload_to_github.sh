#!/bin/bash

# VideoContentOptimizer - GitHub 上传脚本
# 使用方法：
#   1. 编辑此脚本，将 <your_username> 替换为你的 GitHub 用户名
#   2. 运行: bash upload_to_github.sh

echo "🎬 VideoContentOptimizer - GitHub 上传脚本"
echo "=============================================="
echo ""

# ========== 配置区域 ==========
# ⚠️ 请修改为你的 GitHub 用户名
GITHUB_USERNAME="<your_username>"

# 仓库名（通常不需要修改）
REPO_NAME="VideoContentOptimizer"

# 仓库描述
REPO_DESC="🎬 一人公司(OPC)视频智能优化平台 - AI驱动的内容创作工具"
# ================================

# 检查是否修改了用户名
if [ "$GITHUB_USERNAME" = "<your_username>" ]; then
    echo "❌ 错误: 请先编辑此脚本，将 GITHUB_USERNAME 修改为你的 GitHub 用户名"
    echo ""
    echo "修改方法："
    echo "  1. 打开脚本: nano upload_to_github.sh"
    echo "  2. 找到第 12 行: GITHUB_USERNAME=\"<your_username>\""
    echo "  3. 修改为: GITHUB_USERNAME=\"你的用户名\""
    echo "  4. 保存并退出 (Ctrl+O, Enter, Ctrl+X)"
    echo ""
    echo "或者，如果你知道你的用户名，我可以帮你直接修改："
    echo "  运行: bash upload_to_github.sh <你的用户名>"
    exit 1
fi

echo "📋 配置信息:"
echo "   用户名: $GITHUB_USERNAME"
echo "   仓库名: $REPO_NAME"
echo "   描述: $REPO_DESC"
echo ""

# 检查 git 是否安装
if ! command -v git &> /dev/null; then
    echo "❌ 错误: 未安装 git"
    echo "   请先安装: sudo apt install git"
    exit 1
fi

# 检查是否在项目目录
if [ ! -f "README.md" ]; then
    echo "❌ 错误: 请在 VideoContentOptimizer 目录下运行此脚本"
    echo "   当前目录: $(pwd)"
    exit 1
fi

# 初始化 git（如果还没初始化）
if [ ! -d ".git" ]; then
    echo "📦 初始化 Git 仓库..."
    git init
    if [ $? -ne 0 ]; then
        echo "❌ Git 初始化失败"
        exit 1
    fi
    echo "✅ Git 仓库初始化完成"
else
    echo "✅ Git 仓库已存在"
fi

# 添加所有文件
echo ""
echo "📁 添加文件到 Git..."
git add .
if [ $? -ne 0 ]; then
    echo "❌ 添加文件失败"
    exit 1
fi
echo "✅ 文件添加完成"

# 提交
echo ""
echo "💾 提交更改..."
git commit -m "Initial commit: VideoContentOptimizer v2.0.0"
if [ $? -ne 0 ]; then
    echo "❌ 提交失败（可能没有任何更改）"
    echo "   尝试: git commit -m 'Initial commit' --allow-empty"
    git commit -m "Initial commit: VideoContentOptimizer v2.0.0" --allow-empty
fi
echo "✅ 提交完成"

# 添加远程仓库
echo ""
echo "🔗 添加远程仓库..."
git remote remove origin 2>/dev/null  # 先移除旧的（如果存在）
git remote add origin https://github.com/$GITHUB_USERNAME/$REPO_NAME.git
if [ $? -ne 0 ]; then
    echo "❌ 添加远程仓库失败"
    exit 1
fi
echo "✅ 远程仓库添加完成: https://github.com/$GITHUB_USERNAME/$REPO_NAME.git"

# 设置主分支
echo ""
echo "🌿 设置主分支为 main..."
git branch -M main
echo "✅ 完成"

# 推送代码
echo ""
echo "📤 推送代码到 GitHub..."
echo "   （如果是第一次推送，可能需要输入 GitHub 用户名和密码/Token）"
echo ""
git push -u origin main
if [ $? -ne 0 ]; then
    echo ""
    echo "❌ 推送失败！常见原因："
    echo "   1. 仓库不存在 → 请先在 GitHub 创建仓库"
    echo "   2. 认证失败 → 需要使用 Personal Access Token"
    echo "   3. 仓库不为空 → 先执行: git pull origin main --rebase"
    echo ""
    echo "💡 解决方法："
    echo "   - 创建仓库: https://github.com/new"
    echo "     仓库名: $REPO_NAME"
    echo "     描述: $REPO_DESC"
    echo "     ⚠️ 不要勾选 'Initialize with README'"
    echo ""
    echo "   - 创建 Token: https://github.com/settings/tokens/new"
    echo "     权限: repo (全部)"
    echo "     使用 Token 作为密码"
    exit 1
fi

echo ""
echo "🎉 上传成功！"
echo "=============================================="
echo "📍 你的仓库地址:"
echo "   https://github.com/$GITHUB_USERNAME/$REPO_NAME"
echo ""
echo "🎯 下一步："
echo "   1. 访问上面的地址，确认所有文件都已上传"
echo "   2. 确认 README.md 正确显示"
echo "   3. 访问 https://skillhub.cn/contest"
echo "   4. 点击 '发布参赛 Skill'"
echo "   5. 填写信息并上传"
echo ""
echo "🎉 祝参赛顺利！冲 Top 10！"
echo "=============================================="
