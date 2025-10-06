#!/usr/bin/env python3
"""
测试 /verify 接口的并发性能 - 使用真实音频文件
"""

import requests
import time
import threading
from concurrent.futures import ThreadPoolExecutor
import statistics
import os
import wave
import numpy as np
import soundfile as sf
from io import BytesIO

def create_test_audio(duration=3, sample_rate=16000, frequency=440):
    """
    创建测试用的音频文件

    Args:
        duration: 音频时长（秒）
        sample_rate: 采样率
        frequency: 音频频率
    """
    # 生成正弦波音频
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    audio_data = np.sin(frequency * 2 * np.pi * t)

    # 添加一些随机噪声使每个文件略有不同
    noise = np.random.normal(0, 0.1, audio_data.shape)
    audio_data = audio_data + noise

    # 确保在[-1, 1]范围内
    audio_data = np.clip(audio_data, -1, 1)

    return audio_data.astype(np.float32)

def save_audio_to_bytes(audio_data, sample_rate=16000):
    """将音频数据保存为WAV格式的字节流"""
    buffer = BytesIO()
    sf.write(buffer, audio_data, sample_rate, format='WAV')
    buffer.seek(0)
    return buffer.getvalue()

def create_test_audio_files():
    """创建多个测试音频文件"""
    print("🎵 创建测试音频文件...")

    os.makedirs('test_audio', exist_ok=True)

    # 创建多个不同的音频文件
    audio_files = []
    for i in range(5):
        # 不同的频率和时长
        freq = 440 + i * 110  # 440Hz, 550Hz, 660Hz, 770Hz, 880Hz
        duration = 2 + i * 0.5  # 2s, 2.5s, 3s, 3.5s, 4s

        audio_data = create_test_audio(duration=duration, frequency=freq)
        audio_bytes = save_audio_to_bytes(audio_data)

        filename = f'test_audio/test_{i+1}.wav'
        with open(filename, 'wb') as f:
            f.write(audio_bytes)

        audio_files.append(filename)
        print(f"   ✅ 创建 {filename} ({duration}s, {freq}Hz)")

    return audio_files

def test_verify_request(server_url, audio_files, timeout=30):
    """执行单次verify请求"""
    try:
        # 随机选择两个音频文件
        import random
        audio1_path = random.choice(audio_files)
        audio2_path = random.choice(audio_files)

        start_time = time.time()

        with open(audio1_path, 'rb') as f1, open(audio2_path, 'rb') as f2:
            files = {
                'audio1': ('audio1.wav', f1, 'audio/wav'),
                'audio2': ('audio2.wav', f2, 'audio/wav')
            }

            response = requests.post(
                f"{server_url}/verify",
                files=files,
                timeout=timeout
            )

        end_time = time.time()
        response_time = end_time - start_time

        return {
            'success': response.status_code == 200,
            'status_code': response.status_code,
            'response_time': response_time,
            'response_data': response.json() if response.status_code == 200 else None,
            'error': None
        }

    except Exception as e:
        return {
            'success': False,
            'status_code': 0,
            'response_time': 0,
            'response_data': None,
            'error': str(e)
        }

def test_verify_concurrency(server_url, audio_files, concurrent_users=5, duration=60):
    """
    测试 /verify 接口的并发性能

    Args:
        server_url: 服务器地址
        audio_files: 音频文件列表
        concurrent_users: 并发用户数
        duration: 测试持续时间（秒）
    """
    print(f"\n🧪 /verify 接口并发测试")
    print(f"🔗 目标: {server_url}/verify")
    print(f"👥 并发用户: {concurrent_users}")
    print(f"⏰ 测试时长: {duration}秒")
    print(f"🎵 音频文件: {len(audio_files)}个")
    print("-" * 50)

    results = []
    errors = []
    start_time = time.time()
    end_time = start_time + duration

    def worker():
        while time.time() < end_time:
            result = test_verify_request(server_url, audio_files)
            results.append(result)

            if not result['success']:
                errors.append(result['error'] or f"HTTP {result['status_code']}")

            # 稍微休息，避免过度请求
            time.sleep(0.5)

    # 启动并发线程
    print("🚀 开始测试...")

    with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
        futures = [executor.submit(worker) for _ in range(concurrent_users)]

        for future in futures:
            future.result()

    # 计算统计数据
    total_time = time.time() - start_time
    total_requests = len(results)
    successful_requests = sum(1 for r in results if r['success'])
    failed_requests = total_requests - successful_requests

    if results:
        response_times = [r['response_time'] for r in results if r['success']]
        if response_times:
            avg_response_time = statistics.mean(response_times)
            min_response_time = min(response_times)
            max_response_time = max(response_times)
            p95_response_time = sorted(response_times)[int(len(response_times) * 0.95)] if len(response_times) > 0 else 0
        else:
            avg_response_time = min_response_time = max_response_time = p95_response_time = 0
    else:
        avg_response_time = min_response_time = max_response_time = p95_response_time = 0

    qps = total_requests / total_time if total_time > 0 else 0
    success_rate = (successful_requests / total_requests * 100) if total_requests > 0 else 0

    # 分析响应数据
    similarity_scores = []
    inference_times = []

    for result in results:
        if result['success'] and result['response_data']:
            data = result['response_data']
            if 'similarity_score' in data:
                similarity_scores.append(data['similarity_score'])
            if 'inference_time' in data:
                inference_times.append(data['inference_time'])

    # 显示结果
    print(f"\n📊 /verify 接口测试结果:")
    print(f"总请求数: {total_requests}")
    print(f"成功请求: {successful_requests}")
    print(f"失败请求: {failed_requests}")
    print(f"成功率: {success_rate:.1f}%")
    print(f"QPS: {qps:.2f}")
    print(f"\n⏱️ 响应时间统计:")
    print(f"平均响应时间: {avg_response_time:.2f}s ({avg_response_time*1000:.0f}ms)")
    print(f"95%响应时间: {p95_response_time:.2f}s ({p95_response_time*1000:.0f}ms)")
    print(f"最快响应: {min_response_time:.2f}s")
    print(f"最慢响应: {max_response_time:.2f}s")

    if inference_times:
        avg_inference = statistics.mean(inference_times)
        print(f"\n🧠 模型推理时间:")
        print(f"平均推理时间: {avg_inference:.3f}s ({avg_inference*1000:.0f}ms)")
        print(f"最快推理: {min(inference_times):.3f}s")
        print(f"最慢推理: {max(inference_times):.3f}s")

    if similarity_scores:
        avg_similarity = statistics.mean(similarity_scores)
        print(f"\n🎯 相似度分析:")
        print(f"平均相似度: {avg_similarity:.3f}")
        print(f"相似度范围: {min(similarity_scores):.3f} - {max(similarity_scores):.3f}")

    if errors:
        print(f"\n❌ 错误统计 ({len(errors)}个):")
        error_counts = {}
        for error in errors[:10]:  # 只显示前10个错误
            error_counts[error] = error_counts.get(error, 0) + 1
        for error, count in error_counts.items():
            print(f"  {error}: {count}次")

    # 性能评估
    if success_rate >= 95 and avg_response_time < 5:
        performance = "优秀"
    elif success_rate >= 90 and avg_response_time < 10:
        performance = "良好"
    elif success_rate >= 80:
        performance = "一般"
    else:
        performance = "较差"

    print(f"\n💯 性能评级: {performance}")

    return {
        'qps': qps,
        'success_rate': success_rate,
        'avg_response_time': avg_response_time,
        'avg_inference_time': statistics.mean(inference_times) if inference_times else 0,
        'total_requests': total_requests
    }

def run_multiple_verify_tests(server_url, audio_files):
    """运行多个不同并发级别的verify测试"""
    test_configs = [
        (2, 30),   # 2用户，30秒
        (5, 30),   # 5用户，30秒
        (10, 30),  # 10用户，30秒
        (15, 30),  # 15用户，30秒
    ]

    print("🔥 /verify 接口多级并发测试")
    print("=" * 60)

    results = []

    for concurrent_users, duration in test_configs:
        print(f"\n🧪 测试场景: {concurrent_users}并发用户")
        result = test_verify_concurrency(server_url, audio_files, concurrent_users, duration)
        results.append(result)

        # 如果成功率太低，提前停止
        if result['success_rate'] < 80:
            print("⚠️ 成功率过低，停止测试")
            break

        # 休息一段时间让服务器恢复
        print("⏳ 休息10秒...")
        time.sleep(10)

    # 生成总结报告
    print("\n" + "="*60)
    print("📋 /verify 接口性能测试报告")
    print("="*60)
    print(f"{'并发数':<8} {'QPS':<8} {'成功率':<8} {'响应时间':<12} {'推理时间':<12}")
    print("-" * 60)

    for i, result in enumerate(results):
        config = test_configs[i]
        print(f"{config[0]:<8} "
              f"{result['qps']:<8.2f} "
              f"{result['success_rate']:<8.1f}% "
              f"{result['avg_response_time']:<12.2f}s "
              f"{result['avg_inference_time']:<12.3f}s")

    return results

def main():
    server_url = "http://localhost:7001"

    print("🎯 3D-Speaker /verify 接口并发性能测试")
    print(f"🔗 测试目标: {server_url}")

    # 创建测试音频文件
    audio_files = create_test_audio_files()

    # 先测试服务是否可用
    print("\n🔍 检查服务状态...")
    try:
        response = requests.get(f"{server_url}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('model_loaded'):
                print("✅ 服务器状态正常，模型已加载")

                # 先做一次单独测试
                print("\n🧪 单次请求测试...")
                result = test_verify_request(server_url, audio_files)
                if result['success']:
                    print(f"✅ 单次请求成功: {result['response_time']:.2f}s")
                    print(f"   相似度: {result['response_data']['similarity_score']:.3f}")
                    print(f"   推理时间: {result['response_data']['inference_time']:.3f}s")

                    # 开始并发测试
                    run_multiple_verify_tests(server_url, audio_files)
                else:
                    print(f"❌ 单次请求失败: {result['error']}")
            else:
                print("❌ 模型未加载")
        else:
            print(f"❌ 服务器响应异常: {response.status_code}")
    except Exception as e:
        print(f"❌ 无法连接到服务器: {e}")

    # 清理测试文件
    print("\n🧹 清理测试文件...")
    import shutil
    if os.path.exists('test_audio'):
        shutil.rmtree('test_audio')
        print("✅ 测试文件已清理")

if __name__ == "__main__":
    main()