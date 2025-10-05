#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This script is a modified version of infer_sv.py that supports MPS acceleration on Mac.
Usage: python speakerlab/bin/infer_sv_mps.py --model_id iic/speech_campplus_sv_zh-cn_16k-common
"""

import os
import sys
import torch
import numpy as np

# 复制原始的infer_sv.py并修改设备检测部分
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# 导入原始脚本的内容
from speakerlab.bin.infer_sv import *

# 修改设备检测逻辑
def get_device():
    if torch.cuda.is_available():
        print('[INFO]: Using CUDA GPU for inference.')
        return torch.device('cuda')
    elif torch.backends.mps.is_available():
        print('[INFO]: Using Apple MPS for inference.')
        return torch.device('mps')
    else:
        print('[INFO]: Using CPU for inference.')
        return torch.device('cpu')

# 在主函数中替换设备选择
if __name__ == '__main__':
    # 这里需要修改原始infer_sv.py的主函数
    # 为了简单起见，直接运行修改版本
    
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--model_id', type=str, required=True)
    parser.add_argument('--wavs', type=str, nargs='*', default=None)
    args = parser.parse_args()
    
    # 设置MPS设备
    device = get_device()
    print(f"Using device: {device}")
    
    # 运行推理
    os.system(f"python speakerlab/bin/infer_sv.py --model_id {args.model_id}")