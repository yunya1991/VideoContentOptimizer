#!/bin/bash
# 视频优化部署脚本

echo '开始部署VideoContentOptimizer...'

# 检查依赖
if ! command -v python3 &> /dev/null; then
    echo '错误: Python3未安装'
    exit 1
fi

# 安装依赖
pip install -r requirements.txt

echo '部署完成！'
