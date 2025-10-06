#!/bin/bash
# 3D-Speaker 轻量级推理环境一键安装脚本

set -e

echo "========================================"
echo "3D-Speaker 轻量级推理环境安装"
echo "========================================"

# 检查Python版本
echo "1. 检查Python环境..."
python_version=$(python3 --version 2>&1 | grep -Po '(?<=Python )\d+\.\d+' || echo "")
if [[ -z "$python_version" ]]; then
    echo "❌ Python3 未安装，请先安装Python3"
    exit 1
fi
echo "   ✓ Python版本: $python_version"

# 检查是否在conda环境中
if [[ -n "$CONDA_DEFAULT_ENV" ]]; then
    echo "   ✓ 当前conda环境: $CONDA_DEFAULT_ENV"
else
    echo "   ⚠️  未检测到conda环境，建议使用conda环境"
fi

# 检查pip
if ! command -v pip &> /dev/null; then
    echo "❌ pip 未安装，请先安装pip"
    exit 1
fi

echo ""
echo "2. 升级pip..."
pip install --upgrade pip

echo ""
echo "3. 安装核心依赖..."
pip install torch>=2.0.0 torchaudio>=2.0.0 --index-url https://download.pytorch.org/whl/cpu

echo ""
echo "4. 安装ModelScope和相关依赖..."
# 按顺序安装，避免依赖冲突
pip install addict>=2.4.0
pip install simplejson>=3.19.0
pip install oss2>=2.18.0
pip install sortedcontainers>=2.4.0
pip install yapf>=0.33.0
pip install datasets>=2.14.0
pip install Pillow>=9.0.0
pip install opencv-python>=4.5.0
pip install modelscope>=1.9.0

echo ""
echo "5. 安装音频处理库..."
pip install soundfile>=0.10.3
pip install librosa>=0.10.0
pip install pydub>=0.25.1
pip install scipy>=1.7.0

echo ""
echo "6. 安装服务器依赖..."
pip install flask>=2.0.0
pip install gunicorn>=20.0.0
pip install requests>=2.28.0

echo ""
echo "7. 安装工具依赖..."
pip install pyyaml>=5.4.1
pip install tqdm>=4.61.1
pip install filelock>=3.12.0
pip install huggingface-hub>=0.16.0

echo ""
echo "8. 安装可选依赖..."
pip install onnxruntime>=1.16.0

echo ""
echo "9. 创建必要目录..."
mkdir -p uploads
mkdir -p models
mkdir -p logs
mkdir -p examples/speaker_verification

echo ""
echo "10. 测试ModelScope导入..."
python -c "
try:
    from modelscope.pipelines import pipeline
    from modelscope.utils.constant import Tasks
    from flask import Flask
    print('✅ 所有依赖导入成功！')
except ImportError as e:
    print(f'❌ 导入失败: {e}')
    exit(1)
" || {
    echo ""
    echo "❌ 依赖测试失败，尝试修复..."

    # 尝试修复常见问题
    echo "   安装缺失的依赖..."
    pip install addict simplejson oss2 sortedcontainers yapf datasets Pillow opencv-python

    # 重新测试
    python -c "
    try:
        from modelscope.pipelines import pipeline
        print('✅ 修复成功！')
    except ImportError as e:
        print(f'❌ 修复失败: {e}')
        print('请手动检查依赖安装')
        exit(1)
    "
}

echo ""
echo "11. 设置配置文件..."
cat > .env << EOF
# 3D-Speaker 服务配置
HOST=0.0.0.0
PORT=7001
DEBUG=false

# 模型配置
SPEAKER_MODEL_ID=iic/speech_eres2net_sv_zh-cn_16k-common
DEVICE=cpu
CACHE_DIR=./models

# 音频处理配置
MAX_CONTENT_LENGTH=16777216
MAX_AUDIO_DURATION=30
MIN_AUDIO_DURATION=0.5
SIMILARITY_THRESHOLD=0.5

# 文件存储
UPLOAD_FOLDER=./uploads

# 生产环境配置
WORKERS=1
WORKER_CLASS=sync
TIMEOUT=120

# 日志配置
LOG_LEVEL=INFO
ACCESS_LOG=logs/access.log
ERROR_LOG=logs/error.log
EOF

echo "   ✓ 配置文件已创建: .env"

echo ""
echo "12. 创建系统服务文件（可选）..."
cat > speaker-server.service << EOF
[Unit]
Description=3D-Speaker Inference Server
After=network.target

[Service]
Type=simple
User=$(whoami)
WorkingDirectory=$(pwd)
Environment=PYTHONPATH=$(pwd)
ExecStart=$(which python) server.py
Restart=always
RestartSec=10

# 环境变量
EnvironmentFile=$(pwd)/.env

# 日志
StandardOutput=journal
StandardError=journal
SyslogIdentifier=speaker-server

# 安全设置
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

echo "   ✓ 系统服务文件已创建: speaker-server.service"
echo "   如需开机自启动，请运行:"
echo "     sudo cp speaker-server.service /etc/systemd/system/"
echo "     sudo systemctl enable speaker-server"

echo ""
echo "13. 验证安装..."
if [[ -f "server.py" ]]; then
    echo "   ✓ 服务器文件存在"
else
    echo "   ❌ 服务器文件不存在，请确保在正确目录运行"
fi

if [[ -f "demo_inference.py" ]]; then
    echo "   ✓ 演示文件存在"
else
    echo "   ❌ 演示文件不存在"
fi

echo ""
echo "========================================"
echo "✅ 安装完成！"
echo "========================================"
echo ""
echo "📋 后续步骤:"
echo "1. 启动服务:     bash start.sh"
echo "2. 生产模式:     bash start.sh production"
echo "3. 查看文档:     http://localhost:7001/"
echo "4. 健康检查:     http://localhost:7001/health"
echo "5. 测试API:      python test_api.py"
echo ""
echo "📁 示例音频文件放置位置: examples/speaker_verification/"
echo "🔧 配置文件位置: .env"
echo "📝 日志文件位置: logs/"
echo ""
echo "如遇问题，请查看: README_INFERENCE.md"