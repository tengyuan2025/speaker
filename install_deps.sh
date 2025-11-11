#!/bin/bash
# 安装依赖到 venv 环境

set -e

echo "========================================"
echo "📦 安装 3D-Speaker 依赖"
echo "========================================"

# 检查 venv 是否存在
if [[ ! -d "venv" ]]; then
    echo "❌ venv 环境不存在，请先创建："
    echo "   python3 -m venv venv"
    exit 1
fi

# 激活环境
echo "🔄 激活 venv 环境..."
source venv/bin/activate

# 升级 pip
echo ""
echo "📦 升级 pip..."
pip install --upgrade pip

# 安装依赖
echo ""
echo "📦 安装依赖包..."

if [[ -f "requirements-inference.txt" ]]; then
    echo "使用 requirements-inference.txt (轻量级)"
    pip install -r requirements-inference.txt
elif [[ -f "requirements.txt" ]]; then
    echo "使用 requirements.txt"
    pip install -r requirements.txt
else
    echo "⚠️  未找到 requirements 文件，手动安装核心依赖..."

    # 安装核心依赖
    pip install torch>=2.0.0 torchaudio>=2.0.0
    pip install modelscope>=1.9.0
    pip install flask>=2.0.0
    pip install soundfile>=0.10.3
    pip install librosa>=0.10.0
    pip install pyyaml>=5.4.1
    pip install tqdm>=4.61.1
    pip install numpy
    pip install scipy
fi

# 验证安装
echo ""
echo "✅ 验证安装..."
python3 -c "
import sys
print(f'Python: {sys.version.split()[0]}')

deps = [
    ('torch', 'PyTorch'),
    ('modelscope', 'ModelScope'),
    ('flask', 'Flask'),
    ('soundfile', 'SoundFile'),
    ('numpy', 'NumPy')
]

missing = []
for module, name in deps:
    try:
        __import__(module)
        print(f'✅ {name}')
    except ImportError:
        print(f'❌ {name} - 未安装')
        missing.append(name)

if missing:
    print(f'\n缺失依赖: {missing}')
    sys.exit(1)
else:
    print('\n✅ 所有依赖安装成功！')
"

echo ""
echo "========================================"
echo "✅ 依赖安装完成！"
echo "========================================"
echo ""
echo "📋 后续步骤:"
echo "1. 启动服务:     bash start.sh"
echo "2. 生产模式:     bash start_production.sh"
echo "3. 测试API:      curl http://localhost:7001/health"
echo ""
echo "💡 手动激活环境: source venv/bin/activate"
