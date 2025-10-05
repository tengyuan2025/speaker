#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
调试模型加载问题
"""

import os
import sys
import torch
from pathlib import Path

# Add project path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_model_loading():
    """测试模型加载"""
    print("=" * 60)
    print("模型加载调试")
    print("=" * 60)

    model_dir = Path("pretrained/iic/speech_campplus_sv_zh-cn_16k-common")

    if not model_dir.exists():
        print("❌ 模型目录不存在")
        return False

    print(f"📁 模型目录: {model_dir}")
    print(f"📄 目录内容:")
    for file in model_dir.iterdir():
        if file.is_file():
            size_mb = file.stat().st_size / 1024 / 1024
            print(f"   {file.name}: {size_mb:.1f}MB")

    # 尝试不同的模型文件
    possible_files = [
        'campplus_cn_common.bin',
        'campplus_cn_common.pt',
        'model.pt',
        'pytorch_model.bin'
    ]

    model_file = None
    for fname in possible_files:
        full_path = model_dir / fname
        if full_path.exists():
            model_file = full_path
            print(f"✅ 找到模型文件: {model_file}")
            break

    if not model_file:
        print("❌ 未找到有效的模型文件")
        return False

    # 尝试加载模型
    print(f"\n🔄 尝试加载模型...")
    try:
        checkpoint = torch.load(model_file, map_location='cpu')
        print(f"✅ 模型文件读取成功")
        print(f"   类型: {type(checkpoint)}")

        if isinstance(checkpoint, dict):
            print(f"   字典键: {list(checkpoint.keys())}")

            # 检查各种可能的键
            possible_keys = ['model', 'state_dict', 'model_state_dict']
            state_dict = None

            for key in possible_keys:
                if key in checkpoint:
                    state_dict = checkpoint[key]
                    print(f"   找到状态字典: {key}")
                    break

            if state_dict is None:
                # 假设整个checkpoint就是state_dict
                state_dict = checkpoint
                print(f"   使用整个checkpoint作为state_dict")

            print(f"   状态字典键数量: {len(state_dict) if isinstance(state_dict, dict) else 'N/A'}")

            if isinstance(state_dict, dict):
                # 显示前几个键
                keys = list(state_dict.keys())[:5]
                print(f"   前5个键: {keys}")

        return True

    except Exception as e:
        print(f"❌ 模型加载失败: {e}")
        return False

def test_speakerlab_import():
    """测试speakerlab模块导入"""
    print("\n" + "=" * 60)
    print("模块导入测试")
    print("=" * 60)

    try:
        from speakerlab.process.processor import FBank
        print("✅ FBank 导入成功")
    except ImportError as e:
        print(f"❌ FBank 导入失败: {e}")
        return False

    try:
        from speakerlab.utils.builder import dynamic_import
        print("✅ dynamic_import 导入成功")
    except ImportError as e:
        print(f"❌ dynamic_import 导入失败: {e}")
        return False

    try:
        model_class = dynamic_import('speakerlab.models.campplus.DTDNN.CAMPPlus')
        print("✅ CAMPPlus 模型类导入成功")

        # 尝试创建模型实例
        model = model_class(feat_dim=80, embedding_size=192)
        print("✅ CAMPPlus 模型实例创建成功")
        print(f"   模型参数数量: {sum(p.numel() for p in model.parameters())}")

        return True

    except Exception as e:
        print(f"❌ CAMPPlus 模型创建失败: {e}")
        return False

def test_complete_loading():
    """测试完整的模型加载流程"""
    print("\n" + "=" * 60)
    print("完整模型加载测试")
    print("=" * 60)

    try:
        # 导入必要模块
        from speakerlab.process.processor import FBank
        from speakerlab.utils.builder import dynamic_import

        # 创建特征提取器
        feature_extractor = FBank(n_mels=80, sample_rate=16000)
        print("✅ 特征提取器创建成功")

        # 创建模型
        model_config = {
            'obj': 'speakerlab.models.campplus.DTDNN.CAMPPlus',
            'args': {
                'feat_dim': 80,
                'embedding_size': 192,
            },
        }

        model_class = dynamic_import(model_config['obj'])
        model = model_class(**model_config['args'])
        print("✅ 模型创建成功")

        # 加载预训练权重
        model_dir = Path("pretrained/iic/speech_campplus_sv_zh-cn_16k-common")
        model_file = model_dir / "campplus_cn_common.bin"

        if model_file.exists():
            checkpoint = torch.load(model_file, map_location='cpu')

            # 尝试不同的加载方式
            if isinstance(checkpoint, dict):
                if 'model' in checkpoint:
                    model.load_state_dict(checkpoint['model'])
                elif 'state_dict' in checkpoint:
                    model.load_state_dict(checkpoint['state_dict'])
                else:
                    model.load_state_dict(checkpoint)
            else:
                model.load_state_dict(checkpoint)

            print("✅ 模型权重加载成功")

            # 设置为评估模式
            model.eval()
            print("✅ 模型设置为评估模式")

            # 测试前向传播
            dummy_input = torch.randn(1, 80, 100)  # [batch, feat_dim, time]
            with torch.no_grad():
                output = model(dummy_input)
                print(f"✅ 模型前向传播成功")
                print(f"   输入形状: {dummy_input.shape}")
                print(f"   输出形状: {output.shape}")

            return True
        else:
            print(f"❌ 模型文件不存在: {model_file}")
            return False

    except Exception as e:
        print(f"❌ 完整加载测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🔍 开始调试模型加载问题...")

    # 测试1: 模型文件
    success1 = test_model_loading()

    # 测试2: 模块导入
    success2 = test_speakerlab_import()

    # 测试3: 完整加载
    success3 = test_complete_loading()

    print("\n" + "=" * 60)
    print("调试结果总结")
    print("=" * 60)
    print(f"模型文件读取: {'✅' if success1 else '❌'}")
    print(f"模块导入: {'✅' if success2 else '❌'}")
    print(f"完整加载: {'✅' if success3 else '❌'}")

    if success1 and success2 and success3:
        print("\n🎉 所有测试通过！可以启动API服务器了")
        print("\n启动命令:")
        print("python api_server_simple.py --model_path pretrained/iic/speech_campplus_sv_zh-cn_16k-common --port 5001")
    else:
        print("\n⚠️  存在问题，建议使用原版API:")
        print("pip install datasets")
        print("python api_server.py")