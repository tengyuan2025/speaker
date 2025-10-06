#!/bin/bash
# 复制音频文件到测试目录

echo "🎵 复制音频文件脚本"
echo "===================="

# 源目录（原始音频文件位置）
SOURCE_DIR="/home/pi/workspace/xiaoyu-server/audio_records/2025/10/06/22/1759761683287886"

# 目标目录（测试脚本使用的目录）
TARGET_DIR="./test_audio"

# 创建目标目录
mkdir -p "$TARGET_DIR"

echo "📂 源目录: $SOURCE_DIR"
echo "📂 目标目录: $TARGET_DIR"

# 检查源目录是否存在
if [ ! -d "$SOURCE_DIR" ]; then
    echo "❌ 源目录不存在: $SOURCE_DIR"
    echo ""
    echo "🔧 解决方案："
    echo "1. 确认路径是否正确"
    echo "2. 或者手动将音频文件复制到 $TARGET_DIR/"
    echo "3. 支持的格式: wav, mp3, flac, m4a, aac"
    echo ""
    echo "手动复制示例："
    echo "cp /your/audio/path/*.wav $TARGET_DIR/"
    exit 1
fi

# 复制音频文件
echo "📋 搜索音频文件..."

# 查找各种格式的音频文件
AUDIO_EXTENSIONS=("*.wav" "*.mp3" "*.flac" "*.m4a" "*.aac")
FOUND_FILES=0

for ext in "${AUDIO_EXTENSIONS[@]}"; do
    for file in "$SOURCE_DIR"/$ext "$SOURCE_DIR"/**/$ext; do
        if [ -f "$file" ]; then
            echo "📄 复制: $(basename "$file")"
            cp "$file" "$TARGET_DIR/"
            ((FOUND_FILES++))
        fi
    done
done

# 也复制没有扩展名的文件（可能是音频文件）
echo "🔍 检查无扩展名文件..."
for file in "$SOURCE_DIR"/*; do
    if [ -f "$file" ] && [[ ! "$file" =~ \. ]]; then
        file_size=$(stat -c%s "$file" 2>/dev/null || stat -f%z "$file" 2>/dev/null || echo "0")
        if [ "$file_size" -gt 1000 ]; then  # 大于1KB，可能是音频文件
            echo "📄 复制: $(basename "$file") (${file_size} bytes)"
            cp "$file" "$TARGET_DIR/"
            ((FOUND_FILES++))
        fi
    fi
done

echo ""
echo "✅ 复制完成！"
echo "📊 总共复制了 $FOUND_FILES 个文件"

# 显示复制的文件
echo ""
echo "📁 目标目录文件列表:"
ls -la "$TARGET_DIR/"

echo ""
echo "🚀 现在可以运行测试:"
echo "python test_real_audio.py"