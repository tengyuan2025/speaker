#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Download pretrained model from ModelScope
"""

import os
import sys
import argparse

def download_with_modelscope(model_id, save_dir):
    """Download using modelscope (if available)"""
    try:
        from modelscope.hub.snapshot_download import snapshot_download
        print(f"Downloading {model_id} using modelscope...")
        model_dir = snapshot_download(model_id, cache_dir=save_dir)
        print(f"Model downloaded to: {model_dir}")

        # Find the model checkpoint
        for root, dirs, files in os.walk(model_dir):
            for file in files:
                if file.endswith('.pt') or file.endswith('.pth'):
                    model_path = os.path.join(root, file)
                    print(f"Found model checkpoint: {model_path}")
                    return model_path
        return model_dir
    except ImportError:
        print("ModelScope not available. Please install it first:")
        print("pip install modelscope")
        return None

def download_with_git(model_id, save_dir):
    """Download using git clone (alternative method)"""
    print(f"Downloading {model_id} using git...")

    # Map model IDs to git URLs
    model_urls = {
        'iic/speech_campplus_sv_zh-cn_16k-common':
            'https://www.modelscope.cn/iic/speech_campplus_sv_zh-cn_16k-common.git',
        'iic/speech_eres2net_sv_zh-cn_16k-common':
            'https://www.modelscope.cn/iic/speech_eres2net_sv_zh-cn_16k-common.git',
    }

    if model_id not in model_urls:
        print(f"Unknown model ID: {model_id}")
        print("Available models:", list(model_urls.keys()))
        return None

    url = model_urls[model_id]
    model_name = model_id.split('/')[-1]
    target_dir = os.path.join(save_dir, model_name)

    if os.path.exists(target_dir):
        print(f"Model directory already exists: {target_dir}")
    else:
        os.makedirs(save_dir, exist_ok=True)
        cmd = f"cd {save_dir} && git clone {url} {model_name}"
        print(f"Running: {cmd}")
        result = os.system(cmd)

        if result != 0:
            print("Git clone failed. You may need to:")
            print("1. Install git-lfs: git lfs install")
            print("2. Or download manually from: https://modelscope.cn/models/" + model_id)
            return None

    # Find the model checkpoint
    for root, dirs, files in os.walk(target_dir):
        for file in files:
            if file.endswith('.pt') or file.endswith('.pth'):
                model_path = os.path.join(root, file)
                print(f"Found model checkpoint: {model_path}")
                return model_path

    return target_dir

def main():
    parser = argparse.ArgumentParser(description='Download pretrained speaker verification models')
    parser.add_argument('--model_id',
                        default='iic/speech_campplus_sv_zh-cn_16k-common',
                        help='Model ID from ModelScope')
    parser.add_argument('--save_dir',
                        default='pretrained',
                        help='Directory to save the model')
    parser.add_argument('--method',
                        default='auto',
                        choices=['auto', 'modelscope', 'git'],
                        help='Download method')

    args = parser.parse_args()

    model_path = None

    if args.method == 'modelscope':
        model_path = download_with_modelscope(args.model_id, args.save_dir)
    elif args.method == 'git':
        model_path = download_with_git(args.model_id, args.save_dir)
    else:  # auto
        # Try modelscope first, then git
        model_path = download_with_modelscope(args.model_id, args.save_dir)
        if model_path is None:
            print("\nTrying git method...")
            model_path = download_with_git(args.model_id, args.save_dir)

    if model_path:
        print("\n" + "="*50)
        print("Model download complete!")
        print(f"Model path: {model_path}")
        print("\nYou can now start the API server with:")
        print(f"python api_server_simple.py --model_path {model_path}")
        print("="*50)
    else:
        print("\nFailed to download model. Please try manual download from:")
        print(f"https://modelscope.cn/models/{args.model_id}")

if __name__ == '__main__':
    main()