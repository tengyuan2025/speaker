#!/usr/bin/env python3
"""
Test script to diagnose model loading issues
"""

import os
import sys
import traceback
from modelscope.pipelines import pipeline
from modelscope.utils.constant import Tasks

def test_model_loading():
    """Test if the model can be loaded"""
    print("="*50)
    print("Model Loading Diagnostic Test")
    print("="*50)

    # Set environment
    os.environ['MODELSCOPE_CACHE'] = os.path.expanduser('~/.cache/modelscope')

    model_id = 'iic/speech_eres2net_sv_zh-cn_16k-common'
    device = 'cpu'

    print(f"\nModel ID: {model_id}")
    print(f"Device: {device}")
    print(f"Cache dir: {os.environ.get('MODELSCOPE_CACHE')}")

    try:
        print("\n1. Attempting to load model...")
        speaker_pipeline = pipeline(
            task=Tasks.speaker_verification,
            model=model_id,
            device=device,
            model_revision='master'
        )

        print("✅ Model loaded successfully!")

        print("\n2. Testing model info...")
        print(f"   Pipeline type: {type(speaker_pipeline)}")
        print(f"   Pipeline task: {speaker_pipeline.task}")

        print("\n✅ All tests passed! Model is ready for use.")
        return True

    except Exception as e:
        print(f"\n❌ Failed to load model: {e}")
        print("\nDetailed error:")
        print(traceback.format_exc())

        print("\n📝 Troubleshooting tips:")
        print("1. Check internet connection (model needs to download on first use)")
        print("2. Check disk space in ~/.cache/modelscope/")
        print("3. Try clearing cache: rm -rf ~/.cache/modelscope/hub/models/iic/speech_eres2net_sv_zh-cn_16k-common")
        print("4. Ensure all dependencies are installed: pip install modelscope")

        return False

if __name__ == "__main__":
    success = test_model_loading()
    sys.exit(0 if success else 1)