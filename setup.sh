#!/bin/bash

echo "🚀 开始安装依赖和下载模型..."

# 检查 Python 版本和虚拟环境
echo "=== 检查 Python 版本 ==="
python --version
echo "虚拟环境: $VIRTUAL_ENV"

# 检查 Python 版本兼容性
PYTHON_VERSION=$(python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
if [[ "$PYTHON_VERSION" > "3.10" ]]; then
    echo "⚠️  警告：Python $PYTHON_VERSION 可能与某些依赖不兼容"
    echo "   ModelScope 官方推荐 Python 3.8"
    echo "   建议使用: conda create -n modelscope python=3.8"
fi

# 升级 pip
echo "=== 升级 pip ==="
python -m pip install --upgrade pip

# 安装依赖
echo "=== 安装依赖 ==="
# 使用阿里云镜像加速安装
pip install -i https://mirrors.aliyun.com/pypi/simple/ torch torchaudio numpy flask flask-cors requests werkzeug addict scipy librosa soundfile

# 按照官方文档安装modelscope (处理PyArrow兼容性)
echo "=== 安装modelscope (官方方式，处理Python 3.13兼容性) ==="

# 对于不同 Python 版本安装兼容依赖
if [[ "$PYTHON_VERSION" == "3.8" ]]; then
    echo "为 Python 3.8 安装兼容版本..."
    # Python 3.8 需要额外的兼容包
    pip install -i https://mirrors.aliyun.com/pypi/simple/ backports.zoneinfo  # zoneinfo 兼容包
    # 使用预编译的 pyarrow wheel
    pip install pyarrow==12.0.0 --only-binary :all: || {
        echo "尝试较低版本的 pyarrow..."
        pip install pyarrow==11.0.0 --only-binary :all:
    }
    # 安装兼容的 datasets 版本
    pip install -i https://mirrors.aliyun.com/pypi/simple/ datasets==2.12.0  # 兼容版本，有 LargeList
elif [[ "$PYTHON_VERSION" > "3.10" ]]; then
    echo "为 Python $PYTHON_VERSION 安装兼容版本..."
    # 先清理可能冲突的包
    pip uninstall -y pyarrow datasets transformers tokenizers huggingface-hub 2>/dev/null || true

    # 安装兼容的版本组合
    pip install -i https://mirrors.aliyun.com/pypi/simple/ pyarrow==12.0.0  # Python 3.13 兼容
    pip install -i https://mirrors.aliyun.com/pypi/simple/ datasets==2.14.0
    pip install -i https://mirrors.aliyun.com/pypi/simple/ transformers==4.30.0
    pip install -i https://mirrors.aliyun.com/pypi/simple/ tokenizers==0.13.3
else
    # Python 3.9-3.10 使用官方推荐版本
    pip install -i https://mirrors.aliyun.com/pypi/simple/ pyarrow==20.0.0
fi

# 先安装兼容的 ModelScope 依赖，避免自动安装不兼容版本
echo "=== 强制安装兼容版本的依赖 ==="
pip uninstall -y datasets transformers tokenizers huggingface-hub 2>/dev/null || true

# 确保使用预编译的 wheel 包
echo "=== 安装预编译依赖 (避免编译) ==="
# 升级 pip 确保能找到 wheel 包
pip install --upgrade pip

# 使用 --only-binary :all: 强制使用 wheel
pip install pyarrow==11.0.0 --only-binary :all:
pip install tokenizers==0.11.6 --only-binary :all:  # 0.11.6 通常有 Python 3.8 wheel
pip install datasets==2.14.0 --only-binary :all:
pip install transformers==4.21.0 --only-binary :all:

# 最后安装 modelscope，使用 --no-deps 避免覆盖我们的版本选择
pip install -i https://mirrors.aliyun.com/pypi/simple/ modelscope --no-deps

# 安装 modelscope 的其他必要依赖
pip install -i https://mirrors.aliyun.com/pypi/simple/ addict pyyaml requests tqdm packaging filelock typing-extensions

# 修复 Python 3.8 兼容性问题
echo "=== 修复 Python 3.8 兼容性 ==="

# 1. 修复类型注解问题
TORCH_UTILS_FILE=$(find $CONDA_PREFIX -name "torch_utils.py" -path "*/modelscope/*" 2>/dev/null | head -1)
if [ -n "$TORCH_UTILS_FILE" ]; then
    echo "修复文件: $TORCH_UTILS_FILE"
    # 备份原文件
    cp "$TORCH_UTILS_FILE" "$TORCH_UTILS_FILE.backup" 2>/dev/null || true

    # 修复所有类型注解
    sed -i 's/list\[int\]/List[int]/g' "$TORCH_UTILS_FILE"
    sed -i 's/list\[str\]/List[str]/g' "$TORCH_UTILS_FILE"
    sed -i 's/dict\[str, Any\]/Dict[str, Any]/g' "$TORCH_UTILS_FILE"
    sed -i 's/dict\[str, int\]/Dict[str, int]/g' "$TORCH_UTILS_FILE"
    sed -i 's/tuple\[set\[int\], torch\.Tensor\]/Tuple[Set[int], torch.Tensor]/g' "$TORCH_UTILS_FILE"
    sed -i 's/set\[int\]/Set[int]/g' "$TORCH_UTILS_FILE"
    sed -i 's/tuple\[/Tuple[/g' "$TORCH_UTILS_FILE"

    # 添加必要的导入
    if ! grep -q "from typing import.*Set" "$TORCH_UTILS_FILE"; then
        sed -i '1i from typing import List, Dict, Tuple, Any, Set' "$TORCH_UTILS_FILE"
    fi
fi

# 2. 修复 zoneinfo 导入问题
UTILS_FILE=$(find $CONDA_PREFIX -name "utils.py" -path "*/modelscope/hub/utils/*" 2>/dev/null | head -1)
if [ -n "$UTILS_FILE" ]; then
    echo "修复 zoneinfo 导入: $UTILS_FILE"
    cp "$UTILS_FILE" "$UTILS_FILE.backup" 2>/dev/null || true

    # 创建正确的替换内容
    cat > /tmp/zoneinfo_fix.py << 'EOF'
try:
    import zoneinfo
except ImportError:
    from backports import zoneinfo
EOF

    # 替换 import zoneinfo 行
    python3 -c "
import re
with open('$UTILS_FILE', 'r') as f:
    content = f.read()

# 替换 import zoneinfo
with open('/tmp/zoneinfo_fix.py', 'r') as f:
    replacement = f.read().strip()

content = re.sub(r'^import zoneinfo$', replacement, content, flags=re.MULTILINE)

with open('$UTILS_FILE', 'w') as f:
    f.write(content)
"
    rm -f /tmp/zoneinfo_fix.py
fi

# 3. 修复 LargeList 导入问题
HF_DATASETS_UTIL_FILE=$(find $CONDA_PREFIX -name "hf_datasets_util.py" -path "*/modelscope/msdatasets/utils/*" 2>/dev/null | head -1)
if [ -n "$HF_DATASETS_UTIL_FILE" ]; then
    echo "修复 LargeList 导入: $HF_DATASETS_UTIL_FILE"
    cp "$HF_DATASETS_UTIL_FILE" "$HF_DATASETS_UTIL_FILE.backup" 2>/dev/null || true

    # 移除有问题的 LargeList 导入
    python3 -c "
import re
with open('$HF_DATASETS_UTIL_FILE', 'r') as f:
    content = f.read()

# 移除 LargeList 从 datasets 导入中
content = re.sub(r', LargeList', '', content)
content = re.sub(r'LargeList,', '', content)
content = re.sub(r'LargeList', '', content)

with open('$HF_DATASETS_UTIL_FILE', 'w') as f:
    f.write(content)

print('已移除 LargeList 导入')
"
fi

echo "✅ Python 3.8 兼容性修复完成"

# 检查模型目录
MODEL_DIR="pretrained/iic/speech_campplus_sv_zh-cn_16k-common"
if [ ! -d "$MODEL_DIR" ]; then
    echo "=== 下载模型 ==="
    python -c "
from modelscope import snapshot_download
import os

model_dir = 'pretrained/iic/speech_campplus_sv_zh-cn_16k-common'
os.makedirs(os.path.dirname(model_dir), exist_ok=True)

print('开始下载模型...')
try:
    snapshot_download('iic/speech_campplus_sv_zh-cn_16k-common', cache_dir='pretrained')
    print('✅ 模型下载成功')
except Exception as e:
    print(f'❌ 模型下载失败: {e}')
    print('请手动运行: python download_model.py')
"
else
    echo "✅ 模型已存在"
fi

echo "🎉 安装完成！"
echo "现在可以运行: ./start.sh 启动服务"