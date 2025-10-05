#!/bin/bash

# 修复兼容性问题脚本
echo "🔧 修复依赖兼容性问题..."

# 激活虚拟环境
source venv/bin/activate

# 修复 datasets 库版本兼容性
echo "📦 修复 datasets 库版本..."
pip install datasets==2.14.0

# 修复其他可能的兼容性问题
echo "📦 修复其他依赖..."
pip install transformers==4.35.0
pip install torch==2.1.0 torchvision==0.16.0 torchaudio==2.1.0 --index-url https://download.pytorch.org/whl/cpu

# 安装 lsof (如果需要)
echo "🔧 检查 lsof 命令..."
if ! command -v lsof &> /dev/null; then
    echo "⚠️  lsof 命令未找到，请手动安装:"
    echo "   CentOS/RHEL: yum install lsof"
    echo "   Ubuntu/Debian: apt-get install lsof"
fi

echo "✅ 修复完成！现在可以尝试启动服务:"
echo "   ./start.sh"