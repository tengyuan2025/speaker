#!/bin/bash

# 启动简化版 API 服务器（不依赖 ModelScope）
# 适用于 Python 3.13 或有依赖问题的环境

echo "=== 检查 Python 版本 ==="
python --version

echo "=== 安装基础依赖 ==="
pip install torch torchaudio numpy flask flask-cors requests werkzeug

echo "=== 检查模型文件 ==="
MODEL_DIR="pretrained/iic/speech_campplus_sv_zh-cn_16k-common"
if [ ! -d "$MODEL_DIR" ]; then
    echo "❌ 模型目录不存在: $MODEL_DIR"
    echo "请先下载模型："
    echo "python download_model.py"
    exit 1
fi

echo "✅ 模型目录存在"

echo "=== 启动简化版 API 服务器 ==="
python api_server_simple.py --model_path "$MODEL_DIR" --port 5001 --host 0.0.0.0

echo "=== 服务器地址 ==="
echo "本地访问: http://localhost:5001"
echo "远程访问: http://YOUR_SERVER_IP:5001"