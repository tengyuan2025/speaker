#!/usr/bin/env python3
"""
并发性能测试脚本
测试3D-Speaker服务的并发处理能力
"""

import asyncio
import aiohttp
import time
import statistics
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
import json

class PerformanceTester:
    def __init__(self, base_url="http://localhost:7001"):
        self.base_url = base_url
        self.health_url = f"{base_url}/health"

    def test_health_endpoint(self, concurrent_users=10, total_requests=100):
        """测试health端点的并发性能"""
        print(f"\n=== Health端点并发测试 ===")
        print(f"并发用户: {concurrent_users}")
        print(f"总请求数: {total_requests}")

        start_time = time.time()
        response_times = []
        success_count = 0
        error_count = 0

        def make_request():
            try:
                start = time.time()
                response = requests.get(self.health_url, timeout=30)
                end = time.time()

                response_time = end - start
                response_times.append(response_time)

                if response.status_code == 200:
                    return True, response_time, response.status_code
                else:
                    return False, response_time, response.status_code
            except Exception as e:
                return False, 0, str(e)

        with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            futures = [executor.submit(make_request) for _ in range(total_requests)]

            for future in as_completed(futures):
                success, response_time, status = future.result()
                if success:
                    success_count += 1
                else:
                    error_count += 1

        total_time = time.time() - start_time

        # 计算统计数据
        if response_times:
            avg_response_time = statistics.mean(response_times)
            median_response_time = statistics.median(response_times)
            p95_response_time = sorted(response_times)[int(len(response_times) * 0.95)]
            p99_response_time = sorted(response_times)[int(len(response_times) * 0.99)]
            min_response_time = min(response_times)
            max_response_time = max(response_times)
        else:
            avg_response_time = median_response_time = p95_response_time = p99_response_time = 0
            min_response_time = max_response_time = 0

        rps = total_requests / total_time
        success_rate = (success_count / total_requests) * 100

        print(f"\n📊 测试结果:")
        print(f"总耗时: {total_time:.2f}秒")
        print(f"成功请求: {success_count}/{total_requests}")
        print(f"失败请求: {error_count}")
        print(f"成功率: {success_rate:.1f}%")
        print(f"QPS (每秒请求数): {rps:.1f}")
        print(f"\n⏱️ 响应时间统计:")
        print(f"平均响应时间: {avg_response_time*1000:.1f}ms")
        print(f"中位数响应时间: {median_response_time*1000:.1f}ms")
        print(f"95%响应时间: {p95_response_time*1000:.1f}ms")
        print(f"99%响应时间: {p99_response_time*1000:.1f}ms")
        print(f"最小响应时间: {min_response_time*1000:.1f}ms")
        print(f"最大响应时间: {max_response_time*1000:.1f}ms")

        return {
            'success_rate': success_rate,
            'qps': rps,
            'avg_response_time': avg_response_time,
            'p95_response_time': p95_response_time,
            'total_time': total_time
        }

    def test_concurrent_loads(self):
        """测试不同并发负载下的性能"""
        print("\n🔥 多级并发负载测试")
        print("=" * 50)

        test_scenarios = [
            (5, 50),     # 5并发用户，50个请求
            (10, 100),   # 10并发用户，100个请求
            (20, 200),   # 20并发用户，200个请求
            (50, 500),   # 50并发用户，500个请求
            (100, 1000), # 100并发用户，1000个请求
        ]

        results = []

        for concurrent_users, total_requests in test_scenarios:
            print(f"\n🧪 测试场景: {concurrent_users}并发用户 x {total_requests}请求")
            result = self.test_health_endpoint(concurrent_users, total_requests)
            result['concurrent_users'] = concurrent_users
            result['total_requests'] = total_requests
            results.append(result)

            # 等待服务器恢复
            print("⏳ 等待3秒...")
            time.sleep(3)

            # 如果成功率太低，停止测试
            if result['success_rate'] < 90:
                print(f"⚠️ 成功率低于90%，停止测试")
                break

        # 生成总结报告
        self.generate_summary_report(results)

        return results

    def generate_summary_report(self, results):
        """生成性能测试总结报告"""
        print("\n" + "="*60)
        print("📋 性能测试总结报告")
        print("="*60)

        print(f"{'并发数':<8} {'QPS':<8} {'成功率':<8} {'平均响应':<12} {'P95响应':<12}")
        print("-" * 60)

        for result in results:
            print(f"{result['concurrent_users']:<8} "
                  f"{result['qps']:<8.1f} "
                  f"{result['success_rate']:<8.1f}% "
                  f"{result['avg_response_time']*1000:<12.1f}ms "
                  f"{result['p95_response_time']*1000:<12.1f}ms")

        # 找到最佳性能点
        if results:
            max_qps_result = max(results, key=lambda x: x['qps'])
            print(f"\n🏆 最高QPS: {max_qps_result['qps']:.1f} (并发数: {max_qps_result['concurrent_users']})")

            # 推荐配置
            good_results = [r for r in results if r['success_rate'] >= 95 and r['p95_response_time'] < 2.0]
            if good_results:
                recommended = max(good_results, key=lambda x: x['qps'])
                print(f"💡 推荐配置: {recommended['concurrent_users']}并发 (QPS: {recommended['qps']:.1f}, 成功率: {recommended['success_rate']:.1f}%)")

    def test_server_status(self):
        """检查服务器状态"""
        print("🔍 检查服务器状态...")
        try:
            response = requests.get(self.health_url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ 服务器运行正常")
                print(f"   模型: {data.get('model_id', 'N/A')}")
                print(f"   设备: {data.get('device', 'N/A')}")
                print(f"   模型已加载: {data.get('model_loaded', False)}")
                print(f"   运行时间: {data.get('uptime', 0):.1f}秒")
                return True
            else:
                print(f"❌ 服务器响应异常: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ 无法连接到服务器: {e}")
            return False

def main():
    # 解析命令行参数
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    else:
        base_url = "http://localhost:7001"

    print(f"🚀 3D-Speaker 并发性能测试")
    print(f"🔗 目标服务: {base_url}")

    tester = PerformanceTester(base_url)

    # 检查服务器状态
    if not tester.test_server_status():
        print("❌ 服务器检查失败，无法继续测试")
        return

    # 执行并发测试
    print("\n🏁 开始并发性能测试...")
    results = tester.test_concurrent_loads()

    print(f"\n🎯 测试完成!")
    print(f"📊 建议根据结果调整Gunicorn worker数量")
    print(f"💡 当前配置: 2个workers")

if __name__ == "__main__":
    main()