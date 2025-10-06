#!/usr/bin/env python3
"""
快速并发测试脚本 - 专门测试阿里云部署的服务
"""

import requests
import time
import threading
from concurrent.futures import ThreadPoolExecutor
import statistics

def test_health_endpoint(server_url, concurrent_users=10, duration=30):
    """
    测试health端点的并发性能

    Args:
        server_url: 服务器地址
        concurrent_users: 并发用户数
        duration: 测试持续时间（秒）
    """
    print(f"🧪 测试目标: {server_url}")
    print(f"👥 并发用户: {concurrent_users}")
    print(f"⏰ 测试时长: {duration}秒")
    print("-" * 40)

    results = []
    errors = []
    start_time = time.time()
    end_time = start_time + duration

    def worker():
        while time.time() < end_time:
            try:
                request_start = time.time()
                response = requests.get(f"{server_url}/health", timeout=10)
                request_end = time.time()

                response_time = request_end - request_start
                results.append({
                    'status_code': response.status_code,
                    'response_time': response_time,
                    'success': response.status_code == 200
                })

                # 稍微休息一下，避免过度占用CPU
                time.sleep(0.1)

            except Exception as e:
                errors.append(str(e))

    # 启动并发线程
    print("🚀 开始测试...")

    with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
        futures = [executor.submit(worker) for _ in range(concurrent_users)]

        # 等待所有线程完成
        for future in futures:
            future.result()

    # 计算结果
    total_time = time.time() - start_time
    total_requests = len(results)
    successful_requests = sum(1 for r in results if r['success'])
    failed_requests = total_requests - successful_requests

    if results:
        response_times = [r['response_time'] for r in results]
        avg_response_time = statistics.mean(response_times)
        min_response_time = min(response_times)
        max_response_time = max(response_times)
        p95_response_time = sorted(response_times)[int(len(response_times) * 0.95)]
    else:
        avg_response_time = min_response_time = max_response_time = p95_response_time = 0

    qps = total_requests / total_time
    success_rate = (successful_requests / total_requests * 100) if total_requests > 0 else 0

    # 显示结果
    print(f"\n📊 测试结果:")
    print(f"总请求数: {total_requests}")
    print(f"成功请求: {successful_requests}")
    print(f"失败请求: {failed_requests}")
    print(f"成功率: {success_rate:.1f}%")
    print(f"QPS: {qps:.1f}")
    print(f"平均响应时间: {avg_response_time*1000:.0f}ms")
    print(f"95%响应时间: {p95_response_time*1000:.0f}ms")
    print(f"最快响应: {min_response_time*1000:.0f}ms")
    print(f"最慢响应: {max_response_time*1000:.0f}ms")

    if errors:
        print(f"\n❌ 错误统计 ({len(errors)}个):")
        error_counts = {}
        for error in errors:
            error_counts[error] = error_counts.get(error, 0) + 1
        for error, count in error_counts.items():
            print(f"  {error}: {count}次")

    return {
        'qps': qps,
        'success_rate': success_rate,
        'avg_response_time': avg_response_time,
        'total_requests': total_requests
    }

def run_multiple_tests(server_url):
    """运行多个不同并发级别的测试"""
    test_configs = [
        (5, 20),   # 5用户，20秒
        (10, 20),  # 10用户，20秒
        (20, 20),  # 20用户，20秒
        (30, 20),  # 30用户，20秒
    ]

    print("🔥 多级并发测试开始")
    print("=" * 50)

    for concurrent_users, duration in test_configs:
        print(f"\n🧪 测试场景: {concurrent_users}并发用户")
        result = test_health_endpoint(server_url, concurrent_users, duration)

        # 评估性能
        if result['success_rate'] >= 99:
            performance = "优秀"
        elif result['success_rate'] >= 95:
            performance = "良好"
        elif result['success_rate'] >= 90:
            performance = "一般"
        else:
            performance = "较差"

        print(f"💯 性能评级: {performance}")

        # 短暂休息
        print("⏳ 休息5秒...")
        time.sleep(5)

if __name__ == "__main__":
    # 测试本地服务器
    server_url = "http://localhost:7001"

    print("🎯 3D-Speaker 并发性能测试")
    print(f"🔗 测试目标: {server_url}")

    # 先检查服务是否可用
    try:
        response = requests.get(f"{server_url}/health", timeout=5)
        if response.status_code == 200:
            print("✅ 服务器状态正常，开始测试")
            run_multiple_tests(server_url)
        else:
            print(f"❌ 服务器响应异常: {response.status_code}")
    except Exception as e:
        print(f"❌ 无法连接到服务器: {e}")
        print("请确认:")
        print("1. 服务器是否正在运行")
        print("2. 端口7001是否开放")
        print("3. 网络连接是否正常")