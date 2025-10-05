#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
快速下载预训练模型（不依赖modelscope）
"""

import os
import sys
import urllib.request
import ssl
from pathlib import Path

# 忽略SSL证书验证（某些环境需要）
ssl._create_default_https_context = ssl._create_unverified_context


def download_file(url, dest_path):
    """下载文件并显示进度"""
    def download_progress(block_num, block_size, total_size):
        downloaded = block_num * block_size
        percent = min(downloaded * 100.0 / total_size, 100)
        bar_len = 40
        filled_len = int(bar_len * percent // 100)
        bar = '█' * filled_len + '░' * (bar_len - filled_len)
        sys.stdout.write(f'\r下载进度: [{bar}] {percent:.1f}% ({downloaded/1024/1024:.1f}MB/{total_size/1024/1024:.1f}MB)')
        sys.stdout.flush()

    try:
        print(f"开始下载: {url}")
        urllib.request.urlretrieve(url, dest_path, download_progress)
        print("\n✅ 下载完成!")
        return True
    except Exception as e:
        print(f"\n❌ 下载失败: {e}")
        return False


def main():
    """主函数"""
    print("="*60)
    print("   3D-Speaker 快速模型下载工具")
    print("="*60)

    # 模型信息
    models = {
        "1": {
            "name": "CAM++ 中文通用模型",
            "file": "campplus_cn_common.pt",
            "urls": [
                # 备选URL列表
                "https://modelscope.oss-cn-beijing.aliyuncs.com/model/iic/speech_campplus_sv_zh-cn_16k-common/campplus_cn_common.pt",
                "https://www.modelscope.cn/api/v1/models/iic/speech_campplus_sv_zh-cn_16k-common/repo/files/campplus_cn_common.pt/download",
            ],
            "size": "约 400MB",
            "desc": "推荐使用，192维特征，中文效果最佳"
        },
        "2": {
            "name": "ERes2Net 中文通用模型",
            "file": "eres2net_cn_common.pt",
            "urls": [
                "https://modelscope.oss-cn-beijing.aliyuncs.com/model/iic/speech_eres2net_sv_zh-cn_16k-common/eres2net_cn_common.pt",
            ],
            "size": "约 300MB",
            "desc": "轻量级模型，速度更快"
        }
    }

    # 显示模型选项
    print("\n可用的预训练模型:")
    for key, model in models.items():
        print(f"\n{key}. {model['name']}")
        print(f"   大小: {model['size']}")
        print(f"   说明: {model['desc']}")

    # 选择模型
    choice = input("\n请选择要下载的模型 (1-2): ").strip()

    if choice not in models:
        print("❌ 无效的选择")
        return

    model_info = models[choice]

    # 创建目录
    model_dir = Path("pretrained") / f"speech_campplus_sv_zh-cn_16k-common"
    model_dir.mkdir(parents=True, exist_ok=True)

    model_path = model_dir / model_info["file"]

    # 检查是否已存在
    if model_path.exists():
        size_mb = model_path.stat().st_size / 1024 / 1024
        print(f"\n⚠️  模型文件已存在: {model_path} ({size_mb:.1f}MB)")

        if size_mb < 10:  # 文件小于10MB，可能是下载失败的
            print("文件可能损坏，将重新下载")
        else:
            overwrite = input("是否覆盖? (y/n): ").strip().lower()
            if overwrite != 'y':
                print("\n模型路径:", model_path)
                print("\n✅ 可以启动API服务:")
                print(f"   python api_server_simple.py --model_path {model_path}")
                return

    # 尝试下载
    print(f"\n📥 正在下载 {model_info['name']}...")
    print(f"   保存到: {model_path}")

    success = False
    for url in model_info["urls"]:
        print(f"\n尝试URL: {url[:50]}...")
        if download_file(url, str(model_path)):
            success = True
            break

    if success:
        size_mb = model_path.stat().st_size / 1024 / 1024
        print(f"\n✅ 模型下载成功!")
        print(f"   文件: {model_path}")
        print(f"   大小: {size_mb:.1f}MB")

        if size_mb < 10:
            print("\n⚠️  警告: 文件可能未完整下载")
            print("请尝试手动下载:")
            print(f"1. 访问: https://modelscope.cn/models/iic/speech_campplus_sv_zh-cn_16k-common")
            print(f"2. 下载: {model_info['file']}")
            print(f"3. 保存到: {model_path}")
        else:
            print("\n🚀 现在可以启动API服务:")
            print(f"   python api_server_simple.py --model_path {model_path}")
            print("\n   或使用自动启动脚本:")
            print("   ./start_api_simple.sh")

            # 更新启动脚本中的模型路径
            update_script = input("\n是否更新启动脚本以使用此模型? (y/n): ").strip().lower()
            if update_script == 'y':
                with open("start_api_simple.sh", "r") as f:
                    content = f.read()

                # 更新MODEL_PATH
                import re
                content = re.sub(
                    r'MODEL_PATH="[^"]*"',
                    f'MODEL_PATH="{model_path}"',
                    content,
                    count=1
                )

                with open("start_api_simple.sh", "w") as f:
                    f.write(content)

                print("✅ 启动脚本已更新")
    else:
        print("\n❌ 所有下载尝试都失败了")
        print("\n请尝试以下方案:")
        print("\n方案1: 使用modelscope下载")
        print("pip install modelscope")
        print("python download_model.py")
        print("\n方案2: 手动下载")
        print("1. 访问: https://modelscope.cn/models/iic/speech_campplus_sv_zh-cn_16k-common/files")
        print(f"2. 下载: {model_info['file']}")
        print(f"3. 保存到: {model_path}")
        print("\n方案3: 使用wget或curl")
        print(f"wget {model_info['urls'][0]} -O {model_path}")


if __name__ == "__main__":
    main()