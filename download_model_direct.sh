#!/bin/bash

# 直接下载预训练模型脚本

echo "=========================================="
echo "   3D-Speaker 预训练模型下载工具"
echo "=========================================="

# 创建目录
MODEL_DIR="pretrained/speech_campplus_sv_zh-cn_16k-common"
mkdir -p $MODEL_DIR

echo "📁 创建目录: $MODEL_DIR"

# 模型选择
echo ""
echo "请选择要下载的模型："
echo "1. CAM++ 中文通用模型 (推荐，192维)"
echo "2. ERes2Net 中文通用模型 (192维)"
echo "3. 手动输入模型URL"

read -p "请输入选项 (1-3): " choice

case $choice in
    1)
        MODEL_NAME="campplus_cn_common.pt"
        # ModelScope CDN URL (这个URL可能需要更新)
        MODEL_URL="https://modelscope.cn/api/v1/models/iic/speech_campplus_sv_zh-cn_16k-common/repo?Revision=master&FilePath=campplus_cn_common.pt"
        ;;
    2)
        MODEL_NAME="eres2net_cn_common.pt"
        MODEL_URL="https://modelscope.cn/api/v1/models/iic/speech_eres2net_sv_zh-cn_16k-common/repo?Revision=master&FilePath=eres2net_cn_common.pt"
        ;;
    3)
        read -p "请输入模型URL: " MODEL_URL
        read -p "请输入保存的文件名 (如 model.pt): " MODEL_NAME
        ;;
    *)
        echo "无效的选项"
        exit 1
        ;;
esac

MODEL_PATH="$MODEL_DIR/$MODEL_NAME"

echo ""
echo "📥 开始下载模型..."
echo "   URL: $MODEL_URL"
echo "   保存到: $MODEL_PATH"

# 检查是否已存在
if [ -f "$MODEL_PATH" ]; then
    echo "⚠️  模型文件已存在: $MODEL_PATH"
    read -p "是否覆盖? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "跳过下载"
        exit 0
    fi
fi

# 尝试不同的下载工具
if command -v wget &> /dev/null; then
    echo "使用 wget 下载..."
    wget -O "$MODEL_PATH" "$MODEL_URL" --no-check-certificate --header="User-Agent: Mozilla/5.0"
elif command -v curl &> /dev/null; then
    echo "使用 curl 下载..."
    curl -L -o "$MODEL_PATH" "$MODEL_URL" -H "User-Agent: Mozilla/5.0"
else
    echo "❌ 错误: 需要安装 wget 或 curl"
    exit 1
fi

# 检查下载是否成功
if [ -f "$MODEL_PATH" ]; then
    FILE_SIZE=$(ls -lh "$MODEL_PATH" | awk '{print $5}')
    echo ""
    echo "✅ 模型下载成功!"
    echo "   文件: $MODEL_PATH"
    echo "   大小: $FILE_SIZE"

    # 如果文件太小，可能是下载失败
    MIN_SIZE=10000000  # 10MB
    ACTUAL_SIZE=$(stat -f%z "$MODEL_PATH" 2>/dev/null || stat -c%s "$MODEL_PATH" 2>/dev/null)

    if [ "$ACTUAL_SIZE" -lt "$MIN_SIZE" ]; then
        echo ""
        echo "⚠️  警告: 文件可能未正确下载（文件太小）"
        echo "   如果模型无法使用，请尝试："
        echo ""
        echo "   方案1: 使用Python下载脚本"
        echo "   pip install modelscope"
        echo "   python download_model.py"
        echo ""
        echo "   方案2: 手动下载"
        echo "   1. 访问: https://modelscope.cn/models/iic/speech_campplus_sv_zh-cn_16k-common/files"
        echo "   2. 下载 campplus_cn_common.pt"
        echo "   3. 保存到: $MODEL_PATH"
    else
        echo ""
        echo "🚀 现在可以启动API服务:"
        echo "   python api_server_simple.py --model_path $MODEL_PATH"
        echo ""
        echo "   或使用启动脚本:"
        echo "   ./start_api_simple.sh"
    fi
else
    echo ""
    echo "❌ 下载失败!"
    echo ""
    echo "请尝试以下替代方案:"
    echo ""
    echo "方案1: 使用Python脚本下载"
    echo "---------------------------------------"
    echo "pip install modelscope"
    echo "python download_model.py"
    echo ""
    echo "方案2: 通过Git克隆"
    echo "---------------------------------------"
    echo "# 安装 git-lfs"
    echo "git lfs install"
    echo ""
    echo "# 克隆模型仓库"
    echo "cd pretrained"
    echo "git clone https://www.modelscope.cn/iic/speech_campplus_sv_zh-cn_16k-common.git"
    echo ""
    echo "方案3: 手动下载"
    echo "---------------------------------------"
    echo "1. 访问ModelScope网站:"
    echo "   https://modelscope.cn/models/iic/speech_campplus_sv_zh-cn_16k-common/files"
    echo ""
    echo "2. 点击下载 campplus_cn_common.pt (约400MB)"
    echo ""
    echo "3. 将文件保存到:"
    echo "   $MODEL_PATH"
    echo ""
    echo "方案4: 使用阿里云OSS下载（如果在中国）"
    echo "---------------------------------------"
    echo "wget https://modelscope.oss-cn-beijing.aliyuncs.com/model/iic/speech_campplus_sv_zh-cn_16k-common/campplus_cn_common.pt -O $MODEL_PATH"
fi