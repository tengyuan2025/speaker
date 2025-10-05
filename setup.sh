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

# 按照官方文档安装modelscope (处理PyArrow兼容性)
echo "=== 安装modelscope (官方方式) ==="
# 先固定PyArrow版本避免PyExtensionType错误
pip install -i https://mirrors.aliyun.com/pypi/simple/ pyarrow==20.0.0
# 然后安装modelscope
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