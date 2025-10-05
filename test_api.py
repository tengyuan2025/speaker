#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
API测试脚本
用于测试说话人验证API的各个接口
"""

import requests
import json
import sys
import time
from pathlib import Path

# API服务地址
BASE_URL = "http://localhost:5000"

def test_health():
    """测试健康检查接口"""
    print("测试健康检查接口...")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        result = response.json()
        print(f"✓ 服务状态: {result['status']}")
        print(f"  模型: {result['model']}")
        print(f"  设备: {result['device']}")
        print(f"  模型已加载: {result['model_loaded']}")
        return True
    except Exception as e:
        print(f"✗ 健康检查失败: {e}")
        return False

def test_verify_local():
    """测试本地文件验证"""
    print("\n测试本地文件验证...")

    # 查找示例音频文件
    example_dir = Path("pretrained/speech_campplus_sv_zh-cn_16k-common/examples")
    if not example_dir.exists():
        print("✗ 示例音频目录不存在")
        return False

    wav_files = list(example_dir.glob("*.wav"))
    if len(wav_files) < 2:
        print("✗ 示例音频文件不足")
        return False

    # 测试同一说话人（使用同一个文件）
    print("测试同一说话人...")
    data = {
        "audio1_path": str(wav_files[0]),
        "audio2_path": str(wav_files[0])
    }

    try:
        response = requests.post(f"{BASE_URL}/verify", json=data, timeout=30)
        result = response.json()

        if result['success']:
            print(f"✓ 验证成功")
            print(f"  相似度: {result['score']:.4f}")
            print(f"  是否同一人: {result['is_same_speaker']}")
            print(f"  置信度: {result['confidence']}")
        else:
            print(f"✗ 验证失败: {result['error']}")
            return False

    except Exception as e:
        print(f"✗ 请求失败: {e}")
        return False

    # 测试不同说话人（如果有多个文件）
    if len(wav_files) >= 2:
        print("\n测试不同说话人...")
        data = {
            "audio1_path": str(wav_files[0]),
            "audio2_path": str(wav_files[1])
        }

        try:
            response = requests.post(f"{BASE_URL}/verify", json=data, timeout=30)
            result = response.json()

            if result['success']:
                print(f"✓ 验证成功")
                print(f"  相似度: {result['score']:.4f}")
                print(f"  是否同一人: {result['is_same_speaker']}")
            else:
                print(f"✗ 验证失败: {result['error']}")

        except Exception as e:
            print(f"✗ 请求失败: {e}")

    return True

def test_extract_embedding():
    """测试特征提取接口"""
    print("\n测试特征提取接口...")

    example_dir = Path("pretrained/speech_campplus_sv_zh-cn_16k-common/examples")
    wav_files = list(example_dir.glob("*.wav"))

    if not wav_files:
        print("✗ 没有找到测试音频")
        return False

    data = {
        "audio_path": str(wav_files[0])
    }

    try:
        response = requests.post(f"{BASE_URL}/extract_embedding", json=data, timeout=30)
        result = response.json()

        if result['success']:
            print(f"✓ 特征提取成功")
            print(f"  特征维度: {result['dimension']}")
            print(f"  特征向量前5维: {result['embedding'][:5]}")
            return result['embedding']
        else:
            print(f"✗ 特征提取失败: {result['error']}")
            return None

    except Exception as e:
        print(f"✗ 请求失败: {e}")
        return None

def test_compare_embeddings(emb1, emb2=None):
    """测试特征向量比较接口"""
    print("\n测试特征向量比较...")

    if emb2 is None:
        emb2 = emb1  # 自己和自己比较

    data = {
        "embedding1": emb1,
        "embedding2": emb2
    }

    try:
        response = requests.post(f"{BASE_URL}/compare_embeddings", json=data, timeout=10)
        result = response.json()

        if result['success']:
            print(f"✓ 特征比较成功")
            print(f"  相似度: {result['similarity']:.4f}")
            print(f"  是否同一人: {result['is_same_speaker']}")
            return True
        else:
            print(f"✗ 特征比较失败: {result['error']}")
            return False

    except Exception as e:
        print(f"✗ 请求失败: {e}")
        return False

def test_config():
    """测试配置接口"""
    print("\n测试配置接口...")

    # 获取当前配置
    try:
        response = requests.get(f"{BASE_URL}/config", timeout=5)
        config = response.json()
        print(f"✓ 当前配置:")
        print(f"  模型: {config['model_id']}")
        print(f"  阈值: {config['threshold']}")
        print(f"  设备: {config['device']}")

        # 尝试更新阈值
        print("\n更新阈值为0.6...")
        new_config = {"threshold": 0.6}
        response = requests.post(f"{BASE_URL}/config", json=new_config, timeout=5)
        result = response.json()

        if result['success']:
            print(f"✓ 配置更新成功")
            print(f"  新阈值: {result['config']['threshold']}")

            # 恢复原阈值
            restore_config = {"threshold": config['threshold']}
            requests.post(f"{BASE_URL}/config", json=restore_config, timeout=5)

        return True

    except Exception as e:
        print(f"✗ 配置测试失败: {e}")
        return False

def main():
    """运行所有测试"""
    print("=" * 50)
    print("说话人验证API测试")
    print("=" * 50)

    # 检查服务是否运行
    if not test_health():
        print("\n❌ 服务未运行，请先启动API服务:")
        print("   python api_server.py")
        sys.exit(1)

    # 运行各项测试
    test_verify_local()

    embedding = test_extract_embedding()
    if embedding:
        test_compare_embeddings(embedding)

    test_config()

    print("\n" + "=" * 50)
    print("✅ 所有测试完成")
    print("=" * 50)

if __name__ == "__main__":
    main()