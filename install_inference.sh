#!/bin/bash
# Installation script for 3D-Speaker lightweight inference

echo "========================================"
echo "3D-Speaker Lightweight Inference Setup"
echo "========================================"

# Check Python version
python_version=$(python3 --version 2>&1 | grep -Po '(?<=Python )\d+\.\d+')
echo "Python version: $python_version"

# Install dependencies step by step to catch errors
echo ""
echo "1. Installing core dependencies..."
pip install torch>=2.0.0 torchaudio>=2.0.0 --index-url https://download.pytorch.org/whl/cpu

echo ""
echo "2. Installing ModelScope and its dependencies..."
pip install addict>=2.4.0
pip install simplejson>=3.19.0
pip install oss2>=2.18.0
pip install sortedcontainers>=2.4.0
pip install yapf>=0.33.0
pip install modelscope>=1.9.0

echo ""
echo "3. Installing audio processing libraries..."
pip install soundfile>=0.10.3
pip install librosa>=0.10.0
pip install pydub>=0.25.1
pip install scipy>=1.7.0

echo ""
echo "4. Installing utilities..."
pip install pyyaml>=5.4.1
pip install tqdm>=4.61.1
pip install requests>=2.28.0
pip install filelock>=3.12.0
pip install huggingface-hub>=0.16.0

echo ""
echo "5. Installing ONNX runtime..."
pip install onnxruntime>=1.16.0

echo ""
echo "========================================"
echo "Installation completed!"
echo "========================================"

echo ""
echo "Testing ModelScope import..."
python -c "from modelscope.pipelines import pipeline; print('✓ ModelScope imported successfully')"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ All dependencies installed successfully!"
    echo ""
    echo "You can now run:"
    echo "  python demo_inference.py"
    echo ""
    echo "Or for simple speaker verification:"
    echo "  python speakerlab/bin/infer_sv_lite.py --audio1 audio1.wav --audio2 audio2.wav"
else
    echo ""
    echo "❌ Error importing ModelScope. Please check the installation."
fi