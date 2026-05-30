#!/bin/bash
# 服务启动脚本

echo '启动VideoContentOptimizer服务...'

# 激活虚拟环境
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# 启动服务
python app/main.py
