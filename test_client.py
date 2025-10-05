#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
说话人验证API测试客户端
包含各种使用示例和测试用例
"""

import requests
import json
import time
import os
from pathlib import Path
import argparse
import numpy as np


class SpeakerVerificationClient:
    """说话人验证API客户端"""

    def __init__(self, base_url="http://localhost:5001"):
        """
        初始化客户端

        Args:
            base_url: API服务地址
        """
        self.base_url = base_url
        self.session = requests.Session()

    def check_health(self):
        """检查服务健康状态"""
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=5)
            if response.ok:
                data = response.json()
                print("✅ 服务状态: 正常")
                print(f"   模型加载: {data.get('model_loaded', False)}")
                print(f"   设备类型: {data.get('device', 'unknown')}")
                print(f"   模型路径: {data.get('model_path', '未加载')}")
                return True
            else:
                print("❌ 服务状态: 异常")
                return False
        except Exception as e:
            print(f"❌ 无法连接到服务: {e}")
            return False

    def verify_files(self, audio1_path, audio2_path):
        """
        通过文件上传方式验证两个音频

        Args:
            audio1_path: 第一个音频文件路径
            audio2_path: 第二个音频文件路径

        Returns:
            dict: 验证结果
        """
        print(f"\n📁 文件验证模式")
        print(f"   音频1: {audio1_path}")
        print(f"   音频2: {audio2_path}")

        with open(audio1_path, 'rb') as f1, open(audio2_path, 'rb') as f2:
            files = {
                'audio1': (os.path.basename(audio1_path), f1, 'audio/wav'),
                'audio2': (os.path.basename(audio2_path), f2, 'audio/wav')
            }

            response = self.session.post(
                f"{self.base_url}/verify",
                files=files,
                timeout=30
            )

        return self._handle_response(response)

    def verify_urls(self, audio1_url, audio2_url):
        """
        通过URL方式验证两个音频

        Args:
            audio1_url: 第一个音频URL
            audio2_url: 第二个音频URL

        Returns:
            dict: 验证结果
        """
        print(f"\n🌐 URL验证模式")
        print(f"   URL1: {audio1_url}")
        print(f"   URL2: {audio2_url}")

        data = {
            "audio1_url": audio1_url,
            "audio2_url": audio2_url
        }

        response = self.session.post(
            f"{self.base_url}/verify",
            json=data,
            timeout=30
        )

        return self._handle_response(response)

    def verify_paths(self, audio1_path, audio2_path):
        """
        通过本地路径方式验证两个音频

        Args:
            audio1_path: 第一个音频路径
            audio2_path: 第二个音频路径

        Returns:
            dict: 验证结果
        """
        print(f"\n📂 路径验证模式")
        print(f"   路径1: {audio1_path}")
        print(f"   路径2: {audio2_path}")

        data = {
            "audio1_path": audio1_path,
            "audio2_path": audio2_path
        }

        response = self.session.post(
            f"{self.base_url}/verify",
            json=data,
            timeout=30
        )

        return self._handle_response(response)

    def verify_batch(self, reference, candidates):
        """
        批量验证多个音频

        Args:
            reference: 参考音频(URL或路径)
            candidates: 候选音频列表

        Returns:
            dict: 批量验证结果
        """
        print(f"\n📦 批量验证模式")
        print(f"   参考音频: {reference}")
        print(f"   候选数量: {len(candidates)}")

        data = {
            "reference": reference,
            "candidates": candidates
        }

        response = self.session.post(
            f"{self.base_url}/verify_batch",
            json=data,
            timeout=60
        )

        return self._handle_response(response)

    def extract_embedding(self, audio_path):
        """
        提取音频特征向量

        Args:
            audio_path: 音频文件路径

        Returns:
            numpy.array: 特征向量
        """
        print(f"\n🔊 提取特征向量")
        print(f"   音频: {audio_path}")

        if os.path.isfile(audio_path):
            # 文件上传方式
            with open(audio_path, 'rb') as f:
                files = {'audio': (os.path.basename(audio_path), f, 'audio/wav')}
                response = self.session.post(
                    f"{self.base_url}/extract_embedding",
                    files=files,
                    timeout=30
                )
        else:
            # URL或路径方式
            data = {"audio_url": audio_path} if audio_path.startswith('http') else {"audio_path": audio_path}
            response = self.session.post(
                f"{self.base_url}/extract_embedding",
                json=data,
                timeout=30
            )

        result = self._handle_response(response)
        if result and result.get('success'):
            return np.array(result['embedding'])
        return None

    def compare_embeddings(self, embedding1, embedding2):
        """
        比较两个特征向量

        Args:
            embedding1: 第一个特征向量
            embedding2: 第二个特征向量

        Returns:
            dict: 比较结果
        """
        print(f"\n📊 比较特征向量")

        data = {
            "embedding1": embedding1.tolist() if isinstance(embedding1, np.ndarray) else embedding1,
            "embedding2": embedding2.tolist() if isinstance(embedding2, np.ndarray) else embedding2
        }

        response = self.session.post(
            f"{self.base_url}/compare_embeddings",
            json=data,
            timeout=10
        )

        return self._handle_response(response)

    def get_config(self):
        """获取当前配置"""
        response = self.session.get(f"{self.base_url}/config", timeout=5)
        return self._handle_response(response)

    def update_config(self, **kwargs):
        """
        更新配置

        Args:
            **kwargs: 配置参数(如threshold=0.6)
        """
        response = self.session.post(
            f"{self.base_url}/config",
            json=kwargs,
            timeout=5
        )
        return self._handle_response(response)

    def _handle_response(self, response):
        """处理响应"""
        try:
            result = response.json()
            if result.get('success'):
                return result
            else:
                print(f"❌ 错误: {result.get('error', '未知错误')}")
                return None
        except Exception as e:
            print(f"❌ 请求失败: {e}")
            return None

    def print_result(self, result):
        """打印验证结果"""
        if not result:
            return

        if result.get('success'):
            score = result.get('score', 0)
            is_same = result.get('is_same_speaker', False)
            threshold = result.get('threshold', 0.5)
            confidence = result.get('confidence', 'unknown')

            print("\n" + "="*50)
            print("📊 验证结果")
            print("="*50)
            print(f"判定结果: {'✅ 同一说话人' if is_same else '❌ 不同说话人'}")
            print(f"相似度分数: {score:.4f}")
            print(f"判定阈值: {threshold}")
            print(f"置信度: {confidence}")
            print("="*50)

            # 显示分数条
            bar_length = 40
            filled_length = int(bar_length * score)
            bar = '█' * filled_length + '░' * (bar_length - filled_length)
            print(f"分数: [{bar}] {score*100:.1f}%")


def run_examples():
    """运行示例测试"""
    client = SpeakerVerificationClient()

    print("\n" + "="*60)
    print(" 说话人验证API测试客户端")
    print("="*60)

    # 1. 检查服务状态
    if not client.check_health():
        print("\n⚠️  服务未启动，请先启动API服务")
        print("   运行: python api_server_simple.py --port 5001")
        return

    # 2. 获取配置
    print("\n📋 当前配置:")
    config = client.get_config()
    if config:
        print(f"   阈值: {config.get('threshold')}")
        print(f"   设备: {config.get('device')}")

    # 3. 文件验证示例
    print("\n" + "-"*60)
    print("示例1: 文件上传验证")
    print("-"*60)

    # 创建测试音频文件（这里使用示例路径，实际使用时替换为真实文件）
    test_audio1 = "test_audio1.wav"
    test_audio2 = "test_audio2.wav"

    if os.path.exists(test_audio1) and os.path.exists(test_audio2):
        result = client.verify_files(test_audio1, test_audio2)
        client.print_result(result)
    else:
        print("⚠️  测试音频文件不存在，跳过文件验证示例")

    # 4. 路径验证示例
    print("\n" + "-"*60)
    print("示例2: 本地路径验证")
    print("-"*60)

    # 查找项目中的示例音频
    example_dir = Path("pretrained/speech_campplus_sv_zh-cn_16k-common/examples")
    if example_dir.exists():
        wav_files = list(example_dir.glob("*.wav"))
        if len(wav_files) >= 2:
            result = client.verify_paths(str(wav_files[0]), str(wav_files[1]))
            client.print_result(result)

            # 同一个文件验证（应该是同一人）
            print("\n验证同一个文件:")
            result = client.verify_paths(str(wav_files[0]), str(wav_files[0]))
            client.print_result(result)
        else:
            print("⚠️  示例音频不足，跳过路径验证")
    else:
        print("⚠️  示例目录不存在，跳过路径验证")

    # 5. 特征提取示例
    print("\n" + "-"*60)
    print("示例3: 特征提取与比较")
    print("-"*60)

    if example_dir.exists():
        wav_files = list(example_dir.glob("*.wav"))
        if wav_files:
            # 提取第一个音频的特征
            emb1 = client.extract_embedding(str(wav_files[0]))
            if emb1 is not None:
                print(f"✅ 特征提取成功")
                print(f"   维度: {len(emb1)}")
                print(f"   前5维: {emb1[:5]}")

                # 提取第二个特征（可以是同一个文件）
                emb2 = client.extract_embedding(str(wav_files[0]))

                if emb2 is not None:
                    # 比较特征向量
                    result = client.compare_embeddings(emb1, emb2)
                    if result:
                        print(f"\n特征向量相似度: {result.get('similarity', 0):.4f}")
                        print(f"是否同一人: {'是' if result.get('is_same_speaker') else '否'}")

    # 6. 批量验证示例
    print("\n" + "-"*60)
    print("示例4: 批量验证")
    print("-"*60)

    if example_dir.exists():
        wav_files = list(example_dir.glob("*.wav"))
        if len(wav_files) >= 2:
            reference = str(wav_files[0])
            candidates = [str(f) for f in wav_files[:3]]  # 最多取3个

            result = client.verify_batch(reference, candidates)
            if result and result.get('success'):
                print(f"✅ 批量验证完成")
                for i, item in enumerate(result['results']):
                    r = item['result']
                    if r.get('success'):
                        is_same = r.get('is_same_speaker')
                        score = r.get('score', 0)
                        print(f"   候选{i+1}: {'同一人' if is_same else '不同人'} (分数: {score:.4f})")

    # 7. 更新配置示例
    print("\n" + "-"*60)
    print("示例5: 配置管理")
    print("-"*60)

    # 更新阈值
    print("更新阈值为0.6...")
    result = client.update_config(threshold=0.6)
    if result and result.get('success'):
        print("✅ 配置更新成功")

    # 恢复默认阈值
    print("恢复默认阈值0.5...")
    client.update_config(threshold=0.5)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='说话人验证API测试客户端')
    parser.add_argument('--url', default='http://localhost:5001',
                        help='API服务地址')
    parser.add_argument('--mode', choices=['examples', 'verify', 'extract', 'batch'],
                        default='examples',
                        help='运行模式')
    parser.add_argument('--audio1', help='第一个音频文件')
    parser.add_argument('--audio2', help='第二个音频文件')
    parser.add_argument('--reference', help='参考音频(批量模式)')
    parser.add_argument('--candidates', nargs='+', help='候选音频列表(批量模式)')

    args = parser.parse_args()

    client = SpeakerVerificationClient(args.url)

    if args.mode == 'examples':
        # 运行示例
        run_examples()

    elif args.mode == 'verify':
        # 验证两个音频
        if not args.audio1 or not args.audio2:
            print("错误: 验证模式需要提供 --audio1 和 --audio2")
            return

        if not client.check_health():
            print("服务未启动")
            return

        # 根据输入类型选择验证方式
        if os.path.isfile(args.audio1) and os.path.isfile(args.audio2):
            result = client.verify_files(args.audio1, args.audio2)
        elif args.audio1.startswith('http') and args.audio2.startswith('http'):
            result = client.verify_urls(args.audio1, args.audio2)
        else:
            result = client.verify_paths(args.audio1, args.audio2)

        client.print_result(result)

    elif args.mode == 'extract':
        # 提取特征
        if not args.audio1:
            print("错误: 提取模式需要提供 --audio1")
            return

        if not client.check_health():
            print("服务未启动")
            return

        embedding = client.extract_embedding(args.audio1)
        if embedding is not None:
            print(f"\n✅ 特征提取成功")
            print(f"维度: {len(embedding)}")
            print(f"前10维: {embedding[:10]}")

            # 保存到文件
            output_file = f"{Path(args.audio1).stem}_embedding.npy"
            np.save(output_file, embedding)
            print(f"特征已保存到: {output_file}")

    elif args.mode == 'batch':
        # 批量验证
        if not args.reference or not args.candidates:
            print("错误: 批量模式需要提供 --reference 和 --candidates")
            return

        if not client.check_health():
            print("服务未启动")
            return

        result = client.verify_batch(args.reference, args.candidates)
        if result and result.get('success'):
            print("\n批量验证结果:")
            for i, item in enumerate(result['results']):
                r = item['result']
                if r.get('success'):
                    is_same = r.get('is_same_speaker')
                    score = r.get('score', 0)
                    print(f"候选{i+1} [{item['candidate']}]:")
                    print(f"  结果: {'同一人' if is_same else '不同人'}")
                    print(f"  分数: {score:.4f}")
                else:
                    print(f"候选{i+1}: 验证失败 - {r.get('error')}")


if __name__ == '__main__':
    main()