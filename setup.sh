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

# 对于 Python 3.13，需要更谨慎的依赖管理
if [[ "$PYTHON_VERSION" > "3.10" ]]; then
    echo "为 Python $PYTHON_VERSION 安装兼容版本..."
    # 先清理可能冲突的包
    pip uninstall -y pyarrow datasets transformers tokenizers huggingface-hub 2>/dev/null || true

    # 安装兼容的版本组合
    pip install -i https://mirrors.aliyun.com/pypi/simple/ pyarrow==12.0.0  # Python 3.13 兼容
    pip install -i https://mirrors.aliyun.com/pypi/simple/ datasets==2.14.0
    pip install -i https://mirrors.aliyun.com/pypi/simple/ transformers==4.30.0
    pip install -i https://mirrors.aliyun.com/pypi/simple/ tokenizers==0.13.3
else
    # Python <= 3.10 使用官方推荐版本
    pip install -i https://mirrors.aliyun.com/pypi/simple/ pyarrow==20.0.0
fi

# 然后安装modelscope
pip install -i https://mirrors.aliyun.com/pypi/simple/ modelscope

# 修复 Python 3.8 类型注解兼容性问题
echo "=== 修复 Python 3.8 兼容性 ==="
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

    # 添加必要的导入（如果还没有）
    if ! grep -q "from typing import.*Set" "$TORCH_UTILS_FILE"; then
        sed -i '1i from typing import List, Dict, Tuple, Any, Set' "$TORCH_UTILS_FILE"
    fi

    echo "✅ Python 3.8 兼容性修复完成"
else
    echo "未找到需要修复的文件"
fi

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