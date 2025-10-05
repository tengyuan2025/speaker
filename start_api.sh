#!/bin/bash

# 启动说话人验证API服务

echo "Starting Speaker Verification API Server..."

# 检查Python环境
if ! command -v python &> /dev/null; then
    echo "Error: Python is not installed"
    exit 1
fi

# 检查Python版本
python_version=$(python -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "Python version: $python_version"

# 安装依赖
echo "Installing dependencies..."
pip install addict  # 先安装addict，避免modelscope导入错误
pip install -r requirements_api.txt

# 设置环境变量（可选）
export FLASK_APP=api_server.py
export FLASK_ENV=production

# 启动服务器
echo "Starting server on http://0.0.0.0:5000"
python api_server.py