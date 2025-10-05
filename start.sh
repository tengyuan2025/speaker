#!/bin/bash

echo "🚀 启动说话人验证 API 服务..."

# 检查模型是否存在
MODEL_DIR="pretrained/iic/speech_campplus_sv_zh-cn_16k-common"
if [ ! -d "$MODEL_DIR" ]; then
    echo "❌ 模型未找到，请先运行: ./setup.sh"
    exit 1
fi

# 检查端口占用
PORT=5002
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null ; then
    echo "⚠️  端口 $PORT 已被占用，尝试使用端口 5001"
    PORT=5001
fi

if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null ; then
    echo "⚠️  端口 $PORT 也被占用，请手动指定端口"
    echo "使用方法: python api_server.py --port YOUR_PORT"
    exit 1
fi

echo "=== 启动服务 ==="
echo "端口: $PORT"
echo "本地访问: http://localhost:$PORT"
echo "远程访问: http://YOUR_SERVER_IP:$PORT"
echo "健康检查: http://localhost:$PORT/health"
echo ""
echo "按 Ctrl+C 停止服务"
echo "=========================="

# 启动服务器
python api_server.py --port $PORT