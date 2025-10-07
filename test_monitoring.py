#!/usr/bin/env python3
"""
测试声纹识别API监控系统

使用方法:
    python test_monitoring.py
"""

import requests
import time
import json
from pathlib import Path

API_URL = "http://tenyuan.tech:7001"

def test_health_check():
    """测试健康检查端点"""
    print("=" * 60)
    print("测试 /health 端点...")
    print("=" * 60)

    response = requests.get(f"{API_URL}/health", timeout=10)

    if response.status_code == 200:
        data = response.json()
        print(f"✅ 服务状态: {data['status']}")
        print(f"✅ 模型加载: {data['model_loaded']}")
        print(f"✅ 运行时间: {data['uptime']:.1f}秒")

        stats = data.get('statistics', {})
        if stats:
            print("\n📊 API统计:")
            print(f"   总请求数: {stats['total_requests']}")
            print(f"   成功次数: {stats['success_count']}")
            print(f"   失败次数: {stats['error_count']}")
            print(f"   成功率: {stats['success_rate']}")
            print(f"   平均响应: {stats['avg_response_time']}")

            recent = stats.get('recent_requests', [])
            if recent:
                print(f"\n📝 最近 {len(recent)} 条请求:")
                for req in recent[-5:]:  # 只显示最后5条
                    status = "✅" if req['success'] else "❌"
                    timestamp = time.strftime('%H:%M:%S', time.localtime(req['timestamp']))
                    error = f" - {req['error']}" if req['error'] else ""
                    print(f"   {status} {timestamp} - {req['endpoint']} - {req['duration']:.3f}s - IP: {req['client_ip']}{error}")
        return True
    else:
        print(f"❌ 健康检查失败: HTTP {response.status_code}")
        return False

def test_verify_with_dummy_files():
    """测试验证端点（使用虚拟文件模拟错误）"""
    print("\n" + "=" * 60)
    print("测试 /verify 端点 (预期失败 - 测试错误监控)...")
    print("=" * 60)

    # 创建虚拟文件来测试
    from io import BytesIO

    dummy_audio = BytesIO(b"not a real audio file")

    files = {
        'audio1': ('test1.wav', dummy_audio, 'audio/wav'),
        'audio2': ('test2.wav', BytesIO(b"also not real"), 'audio/wav')
    }

    try:
        response = requests.post(
            f"{API_URL}/verify",
            files=files,
            data={'threshold': 0.7},
            timeout=30
        )

        if response.status_code == 400:
            print(f"✅ 正确识别了无效音频文件")
            print(f"   错误信息: {response.json().get('error', 'N/A')}")
        else:
            print(f"⚠️  意外的响应: HTTP {response.status_code}")
            print(f"   响应内容: {response.text[:200]}")

    except Exception as e:
        print(f"❌ 请求失败: {e}")

def test_verify_with_real_files():
    """测试验证端点（如果有真实音频文件）"""
    print("\n" + "=" * 60)
    print("测试 /verify 端点 (使用真实音频文件)...")
    print("=" * 60)

    # 查找真实的音频文件
    test_dir = Path(__file__).parent
    audio_files = list(test_dir.glob("*.wav"))

    if len(audio_files) < 2:
        print("⚠️  未找到足够的音频文件进行测试")
        print(f"   当前目录: {test_dir}")
        print(f"   找到 {len(audio_files)} 个 .wav 文件")
        return

    file1 = audio_files[0]
    file2 = audio_files[1]

    print(f"📁 音频文件1: {file1.name}")
    print(f"📁 音频文件2: {file2.name}")

    try:
        with open(file1, 'rb') as f1, open(file2, 'rb') as f2:
            files = {
                'audio1': (file1.name, f1, 'audio/wav'),
                'audio2': (file2.name, f2, 'audio/wav')
            }

            start = time.time()
            response = requests.post(
                f"{API_URL}/verify",
                files=files,
                data={'threshold': 0.7},
                timeout=30
            )
            duration = time.time() - start

            if response.status_code == 200:
                data = response.json()
                print(f"✅ 验证成功")
                print(f"   相似度: {data['similarity_score']:.4f}")
                print(f"   是否匹配: {data['is_same_speaker']}")
                print(f"   推理时间: {data['inference_time']}s")
                print(f"   总请求时间: {duration:.3f}s")
            else:
                print(f"❌ 验证失败: HTTP {response.status_code}")
                print(f"   错误: {response.text[:200]}")

    except Exception as e:
        print(f"❌ 请求失败: {e}")

def main():
    """主函数"""
    print("\n🧪 声纹识别API监控系统测试")
    print("=" * 60)

    try:
        # 1. 测试健康检查
        if not test_health_check():
            print("\n❌ 健康检查失败，无法继续测试")
            return

        # 2. 测试错误处理（虚拟文件）
        test_verify_with_dummy_files()

        # 3. 测试真实音频（如果存在）
        test_verify_with_real_files()

        # 4. 再次检查健康状态（查看统计更新）
        time.sleep(1)
        print("\n" + "=" * 60)
        print("最终统计 (刷新)...")
        print("=" * 60)
        test_health_check()

        print("\n✅ 测试完成！")
        print("\n💡 提示:")
        print("   1. 查看日志文件: tail -f logs/speaker_api_$(date +%Y%m%d).log")
        print("   2. 查看统计: curl http://tenyuan.tech:7001/health | jq '.statistics'")
        print("   3. 检查失败请求: grep '❌' logs/speaker_api_$(date +%Y%m%d).log")

    except requests.exceptions.ConnectionError:
        print(f"\n❌ 无法连接到 {API_URL}")
        print("   请检查:")
        print("   1. API服务是否运行？")
        print("   2. 网络连接是否正常？")
        print("   3. 防火墙是否阻止连接？")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")

if __name__ == "__main__":
    main()
