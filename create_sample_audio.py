#!/usr/bin/env python3
"""
创建示例音频文件用于测试
如果真实音频文件不可用，可以使用这些示例文件
"""

import numpy as np
import soundfile as sf
import os

def create_sample_audio_files():
    """创建示例音频文件"""
    print("🎵 创建示例音频文件...")

    # 创建目录
    os.makedirs('./test_audio', exist_ok=True)

    # 音频参数
    sample_rate = 16000
    duration = 3  # 3秒

    # 创建两个不同的音频文件
    audio_configs = [
        {
            'filename': 'speaker1_sample.wav',
            'frequencies': [440, 550],  # 双音调
            'amplitude': 0.3
        },
        {
            'filename': 'speaker2_sample.wav',
            'frequencies': [660, 770],  # 不同的双音调
            'amplitude': 0.3
        }
    ]

    for config in audio_configs:
        # 生成时间轴
        t = np.linspace(0, duration, int(sample_rate * duration), False)

        # 生成多频率音频（模拟复杂语音）
        audio_data = np.zeros_like(t)
        for freq in config['frequencies']:
            audio_data += np.sin(2 * np.pi * freq * t) * config['amplitude']

        # 添加语音包络（模拟自然语音的音量变化）
        envelope = np.exp(-0.5 * t) * (1 + 0.5 * np.sin(10 * t))
        audio_data *= envelope

        # 添加轻微的随机噪声（模拟录音环境噪声）
        noise = np.random.normal(0, 0.02, audio_data.shape)
        audio_data += noise

        # 标准化到合理范围
        audio_data = np.clip(audio_data, -0.8, 0.8)

        # 保存文件
        filepath = f'./test_audio/{config["filename"]}'
        sf.write(filepath, audio_data, sample_rate)

        print(f"✅ 创建: {filepath}")
        print(f"   时长: {duration}s, 采样率: {sample_rate}Hz")
        print(f"   频率: {config['frequencies']}Hz")

    print(f"\n📁 音频文件已保存到: ./test_audio/")
    print(f"🧪 现在可以运行测试: python test_real_audio.py")

if __name__ == "__main__":
    create_sample_audio_files()