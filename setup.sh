#!/bin/bash

echo "🚀 开始安装依赖和下载模型..."

# 检查 Python 版本
echo "=== 检查 Python 版本 ==="
python --version

# 升级 pip
echo "=== 升级 pip ==="
python -m pip install --upgrade pip

# 安装依赖
echo "=== 安装依赖 ==="
# 使用阿里云镜像加速安装
pip install -i https://mirrors.aliyun.com/pypi/simple/ torch torchaudio numpy flask flask-cors requests werkzeug addict scipy librosa soundfile

# 安装兼容版本的依赖
echo "=== 安装AI相关依赖 ==="

# 先卸载可能存在的冲突版本
echo "清理可能冲突的包..."
pip uninstall -y tokenizers transformers huggingface-hub pyarrow

# 安装兼容的版本组合
echo "安装兼容版本的AI生态..."
pip install -i https://mirrors.aliyun.com/pypi/simple/ pyarrow==12.0.0  # 兼容datasets的版本
pip install -i https://mirrors.aliyun.com/pypi/simple/ tokenizers==0.12.1  # transformers兼容版本
pip install -i https://mirrors.aliyun.com/pypi/simple/ transformers==4.21.0  # 稳定版本
pip install -i https://mirrors.aliyun.com/pypi/simple/ huggingface-hub==0.10.0  # 兼容版本

# 安装其他依赖
pip install -i https://mirrors.aliyun.com/pypi/simple/ datasets==2.14.0  # 兼容版本，避免与modelscope冲突
pip install -i https://mirrors.aliyun.com/pypi/simple/ pyyaml tqdm packaging filelock typing-extensions

# 最后安装modelscope
echo "=== 安装modelscope ==="
pip install -i https://mirrors.aliyun.com/pypi/simple/ modelscope

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