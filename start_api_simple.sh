#!/bin/bash

# 简化版API启动脚本（不依赖modelscope）

echo "Starting Simple Speaker Verification API Server..."

# 检查Python环境
if ! command -v python &> /dev/null; then
    echo "Error: Python is not installed"
    exit 1
fi

# 检查Python版本
python_version=$(python -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "Python version: $python_version"

# 安装基础依赖
echo "Installing dependencies..."
pip install -r requirements_api_simple.txt

# 检查是否有预训练模型
MODEL_PATH=""

# 查找本地已下载的模型
if [ -f "pretrained/speech_campplus_sv_zh-cn_16k-common/campplus_cn_common.pt" ]; then
    MODEL_PATH="pretrained/speech_campplus_sv_zh-cn_16k-common/campplus_cn_common.pt"
    echo "Found pretrained model: $MODEL_PATH"
elif [ -f "pretrained/speech_campplus_sv_zh-cn_16k-common/model.pt" ]; then
    MODEL_PATH="pretrained/speech_campplus_sv_zh-cn_16k-common/model.pt"
    echo "Found pretrained model: $MODEL_PATH"
else
    echo "Warning: No pretrained model found!"
    echo "The server will start but won't work without a model."
    echo ""
    echo "To download a model, you have two options:"
    echo ""
    echo "Option 1: Use the download script (if modelscope is available):"
    echo "  pip install modelscope"
    echo "  python download_model.py"
    echo ""
    echo "Option 2: Download manually from ModelScope:"
    echo "  1. Visit: https://modelscope.cn/models/iic/speech_campplus_sv_zh-cn_16k-common"
    echo "  2. Download the model files"
    echo "  3. Place them in: pretrained/speech_campplus_sv_zh-cn_16k-common/"
    echo ""
    echo "Option 3: Use wget to download directly:"
    echo "  mkdir -p pretrained/speech_campplus_sv_zh-cn_16k-common"
    echo "  cd pretrained/speech_campplus_sv_zh-cn_16k-common"
    echo "  wget https://modelscope.cn/api/v1/models/iic/speech_campplus_sv_zh-cn_16k-common/repo?Revision=master&FilePath=campplus_cn_common.pt"
    echo ""

    read -p "Do you want to continue without a model? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 设置环境变量
export FLASK_APP=api_server_simple.py
export FLASK_ENV=production

# 启动服务器
PORT=${PORT:-5001}  # 默认使用5001端口，可通过环境变量修改
echo "Starting server on http://0.0.0.0:$PORT"
if [ -n "$MODEL_PATH" ]; then
    python api_server_simple.py --model_path "$MODEL_PATH" --port $PORT
else
    python api_server_simple.py --port $PORT
fi