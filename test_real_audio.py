#!/usr/bin/env python3
"""
使用真实录音文件测试 /verify 接口的并发性能
"""

import requests
import time
import threading
from concurrent.futures import ThreadPoolExecutor
import statistics
import os
import glob
import random

def find_audio_files(audio_dir):
    """
    在指定目录中查找音频文件

    Args:
        audio_dir: 音频文件目录
    """
    print(f"🔍 搜索音频文件: {audio_dir}")

    # 支持的音频格式
    audio_extensions = ['*.wav', '*.mp3', '*.flac', '*.m4a', '*.aac']
    audio_files = []

    for ext in audio_extensions:
        pattern = os.path.join(audio_dir, '**', ext)
        found_files = glob.glob(pattern, recursive=True)
        audio_files.extend(found_files)

    # 也搜索没有扩展名的文件（可能是音频文件）
    all_files = glob.glob(os.path.join(audio_dir, '**', '*'), recursive=True)
    for file_path in all_files:
        if os.path.isfile(file_path) and not any(file_path.endswith(ext[1:]) for ext in audio_extensions):
            # 检查文件大小，音频文件通常比较大
            if os.path.getsize(file_path) > 1000:  # 大于1KB
                audio_files.append(file_path)

    print(f"📁 找到音频文件: {len(audio_files)}个")
    for i, file_path in enumerate(audio_files[:10]):  # 只显示前10个
        file_size = os.path.getsize(file_path) / 1024  # KB
        print(f"   {i+1}. {os.path.basename(file_path)} ({file_size:.1f}KB)")

    if len(audio_files) > 10:
        print(f"   ... 还有 {len(audio_files) - 10} 个文件")

    return audio_files

def test_verify_request(server_url, audio_files, timeout=60):
    """执行单次verify请求，使用真实音频文件"""
    try:
        if len(audio_files) < 2:
            return {
                'success': False,
                'error': '至少需要2个音频文件'
            }

        # 随机选择两个不同的音频文件
        audio1_path = random.choice(audio_files)
        audio2_path = random.choice(audio_files)

        # 确保选择的是两个不同的文件（如果有足够多的文件）
        attempts = 0
        while audio1_path == audio2_path and len(audio_files) > 1 and attempts < 10:
            audio2_path = random.choice(audio_files)
            attempts += 1

        start_time = time.time()

        with open(audio1_path, 'rb') as f1, open(audio2_path, 'rb') as f2:
            files = {
                'audio1': (os.path.basename(audio1_path), f1, 'audio/wav'),
                'audio2': (os.path.basename(audio2_path), f2, 'audio/wav')
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
            'error': None,
            'audio1_file': os.path.basename(audio1_path),
            'audio2_file': os.path.basename(audio2_path)
        }

    except Exception as e:
        return {
            'success': False,
            'status_code': 0,
            'response_time': 0,
            'response_data': None,
            'error': str(e),
            'audio1_file': '',
            'audio2_file': ''
        }

def test_verify_concurrency(server_url, audio_files, concurrent_users=3, total_requests=30):
    """
    测试 /verify 接口的并发性能（使用真实音频）

    Args:
        server_url: 服务器地址
        audio_files: 音频文件列表
        concurrent_users: 并发用户数
        total_requests: 总请求数
    """
    print(f"\n🧪 /verify 接口真实音频并发测试")
    print(f"🔗 目标: {server_url}/verify")
    print(f"👥 并发用户: {concurrent_users}")
    print(f"📊 总请求数: {total_requests}")
    print(f"🎵 音频文件池: {len(audio_files)}个")
    print("-" * 50)

    results = []
    errors = []
    completed_requests = 0

    def worker():
        nonlocal completed_requests
        while completed_requests < total_requests:
            if completed_requests >= total_requests:
                break

            completed_requests += 1
            request_id = completed_requests

            print(f"📤 发送请求 {request_id}/{total_requests}")
            result = test_verify_request(server_url, audio_files)
            results.append(result)

            if result['success']:
                data = result['response_data']
                similarity = data.get('similarity_score', 0)
                inference_time = data.get('inference_time', 0)
                print(f"✅ 请求 {request_id} 成功: 相似度={similarity:.3f}, 推理={inference_time:.3f}s, 总时间={result['response_time']:.2f}s")
            else:
                error_msg = result['error'] or f"HTTP {result['status_code']}"
                errors.append(error_msg)
                print(f"❌ 请求 {request_id} 失败: {error_msg}")

            # 稍微休息
            time.sleep(1)

    # 启动并发线程
    print("🚀 开始测试...")
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
        futures = [executor.submit(worker) for _ in range(concurrent_users)]
        for future in futures:
            future.result()

    # 计算统计数据
    total_time = time.time() - start_time
    successful_requests = sum(1 for r in results if r['success'])
    failed_requests = len(results) - successful_requests

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

    qps = len(results) / total_time if total_time > 0 else 0
    success_rate = (successful_requests / len(results) * 100) if results else 0

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
    print(f"\n📊 真实音频测试结果:")
    print(f"总请求数: {len(results)}")
    print(f"成功请求: {successful_requests}")
    print(f"失败请求: {failed_requests}")
    print(f"成功率: {success_rate:.1f}%")
    print(f"QPS: {qps:.2f}")
    print(f"总耗时: {total_time:.1f}秒")

    print(f"\n⏱️ 响应时间统计:")
    print(f"平均响应时间: {avg_response_time:.2f}s")
    print(f"95%响应时间: {p95_response_time:.2f}s")
    print(f"最快响应: {min_response_time:.2f}s")
    print(f"最慢响应: {max_response_time:.2f}s")

    if inference_times:
        avg_inference = statistics.mean(inference_times)
        min_inference = min(inference_times)
        max_inference = max(inference_times)
        print(f"\n🧠 模型推理时间:")
        print(f"平均推理时间: {avg_inference:.3f}s")
        print(f"最快推理: {min_inference:.3f}s")
        print(f"最慢推理: {max_inference:.3f}s")

    if similarity_scores:
        avg_similarity = statistics.mean(similarity_scores)
        min_similarity = min(similarity_scores)
        max_similarity = max(similarity_scores)
        print(f"\n🎯 相似度分析:")
        print(f"平均相似度: {avg_similarity:.3f}")
        print(f"相似度范围: {min_similarity:.3f} - {max_similarity:.3f}")

    if errors:
        print(f"\n❌ 错误统计 ({len(errors)}个):")
        error_counts = {}
        for error in errors[:5]:  # 只显示前5个错误
            error_counts[error] = error_counts.get(error, 0) + 1
        for error, count in error_counts.items():
            print(f"  {error}: {count}次")

    return {
        'qps': qps,
        'success_rate': success_rate,
        'avg_response_time': avg_response_time,
        'avg_inference_time': statistics.mean(inference_times) if inference_times else 0,
        'total_requests': len(results),
        'avg_similarity': statistics.mean(similarity_scores) if similarity_scores else 0
    }

def main():
    # 音频文件目录 - 改为当前目录下的test_audio文件夹
    audio_dir = "./test_audio"
    server_url = "http://localhost:7001"

    print("🎯 3D-Speaker 真实音频并发性能测试")
    print(f"🔗 测试目标: {server_url}")
    print(f"📁 音频目录: {audio_dir}")

    # 检查音频目录是否存在，如果不存在则创建并提示
    if not os.path.exists(audio_dir):
        print(f"📁 创建音频目录: {audio_dir}")
        os.makedirs(audio_dir, exist_ok=True)
        print(f"⚠️ 请将音频文件放到 {audio_dir} 目录下")
        print(f"   例如: cp /path/to/your/audio/* {audio_dir}/")
        print(f"   或者: 手动复制音频文件到该目录")
        return

    # 查找音频文件
    audio_files = find_audio_files(audio_dir)

    if len(audio_files) < 2:
        print("❌ 需要至少2个音频文件进行测试")
        return

    # 检查服务状态
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
                    print(f"✅ 单次请求成功:")
                    print(f"   文件1: {result['audio1_file']}")
                    print(f"   文件2: {result['audio2_file']}")
                    print(f"   响应时间: {result['response_time']:.2f}s")
                    print(f"   相似度: {result['response_data']['similarity_score']:.3f}")
                    print(f"   推理时间: {result['response_data']['inference_time']:.3f}s")

                    # 开始并发测试
                    print("\n" + "="*60)
                    print("开始并发测试...")

                    # 不同的测试配置
                    test_configs = [
                        (2, 10),   # 2并发，10个请求
                        (3, 15),   # 3并发，15个请求
                        (5, 20),   # 5并发，20个请求
                    ]

                    for concurrent_users, total_requests in test_configs:
                        print(f"\n📊 测试配置: {concurrent_users}并发 x {total_requests}请求")
                        result = test_verify_concurrency(server_url, audio_files, concurrent_users, total_requests)

                        # 如果成功率太低，停止测试
                        if result['success_rate'] < 70:
                            print("⚠️ 成功率过低，停止测试")
                            break

                        # 休息一下
                        if concurrent_users < 5:
                            print("⏳ 休息5秒...")
                            time.sleep(5)

                else:
                    print(f"❌ 单次请求失败: {result['error']}")
            else:
                print("❌ 模型未加载")
        else:
            print(f"❌ 服务器响应异常: {response.status_code}")
    except Exception as e:
        print(f"❌ 无法连接到服务器: {e}")

if __name__ == "__main__":
    main()