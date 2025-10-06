#!/usr/bin/env python3
"""
Export PyTorch speaker models to ONNX format for efficient inference
"""

import os
import argparse
import torch
import yaml
from typing import Dict, Any
from modelscope.hub.snapshot_download import snapshot_download


def load_model_from_modelscope(model_id: str, cache_dir: str = "./models") -> Tuple[torch.nn.Module, Dict]:
    """
    Load a model from ModelScope

    Args:
        model_id: ModelScope model ID
        cache_dir: Directory to cache models

    Returns:
        Tuple of (model, config)
    """
    print(f"Downloading model: {model_id}")
    model_dir = snapshot_download(model_id, cache_dir=cache_dir)

    # Load configuration
    config_path = os.path.join(model_dir, 'model.yaml')
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
    else:
        config = {'sample_rate': 16000, 'embedding_size': 192}

    # Load model
    model_path = os.path.join(model_dir, 'model.pt')
    if os.path.exists(model_path):
        model = torch.jit.load(model_path, map_location='cpu')
    else:
        ckpt_path = os.path.join(model_dir, 'model.ckpt')
        if os.path.exists(ckpt_path):
            checkpoint = torch.load(ckpt_path, map_location='cpu')
            # Build model from checkpoint
            from speakerlab.models import build_model
            model = build_model(config)
            model.load_state_dict(checkpoint['state_dict'])
        else:
            raise FileNotFoundError(f"No model file found in {model_dir}")

    model.eval()
    return model, config


def export_to_onnx(
    model: torch.nn.Module,
    output_path: str,
    config: Dict[str, Any],
    batch_size: int = 1,
    sequence_length: int = 16000 * 3  # 3 seconds at 16kHz
):
    """
    Export PyTorch model to ONNX format

    Args:
        model: PyTorch model
        output_path: Output ONNX file path
        config: Model configuration
        batch_size: Batch size for export
        sequence_length: Audio sequence length
    """
    print(f"Exporting model to ONNX: {output_path}")

    # Create dummy input
    dummy_input = torch.randn(batch_size, 1, sequence_length)

    # Export to ONNX
    torch.onnx.export(
        model,
        dummy_input,
        output_path,
        export_params=True,
        opset_version=14,
        do_constant_folding=True,
        input_names=['audio'],
        output_names=['embedding'],
        dynamic_axes={
            'audio': {0: 'batch_size', 2: 'sequence_length'},
            'embedding': {0: 'batch_size'}
        },
        verbose=False
    )

    print(f"Model exported successfully to {output_path}")

    # Verify the exported model
    try:
        import onnx
        import onnxruntime as ort

        # Check ONNX model
        onnx_model = onnx.load(output_path)
        onnx.checker.check_model(onnx_model)
        print("ONNX model validation passed")

        # Test inference
        ort_session = ort.InferenceSession(output_path)
        ort_inputs = {ort_session.get_inputs()[0].name: dummy_input.numpy()}
        ort_outputs = ort_session.run(None, ort_inputs)
        print(f"Test inference successful, output shape: {ort_outputs[0].shape}")

    except ImportError:
        print("ONNX or ONNXRuntime not installed, skipping validation")
    except Exception as e:
        print(f"Validation failed: {e}")


def optimize_onnx(input_path: str, output_path: str):
    """
    Optimize ONNX model for inference

    Args:
        input_path: Input ONNX file path
        output_path: Optimized ONNX file path
    """
    try:
        from onnxruntime.transformers import optimizer

        print(f"Optimizing ONNX model: {input_path}")

        # Optimize model
        optimized_model = optimizer.optimize_model(
            input_path,
            model_type='bert',  # Use bert optimizer for transformer-based models
            num_heads=8,
            hidden_size=256,
            optimization_options=optimizer.OptimizationOptions(
                enable_gelu_approximation=True,
                enable_embed_layer_norm_fusion=True
            )
        )

        # Save optimized model
        optimized_model.save_model_to_file(output_path)
        print(f"Optimized model saved to: {output_path}")

    except ImportError:
        print("ONNXRuntime transformers not installed, skipping optimization")
        print("Install with: pip install onnxruntime-tools")
    except Exception as e:
        print(f"Optimization failed: {e}")


def quantize_onnx(input_path: str, output_path: str):
    """
    Quantize ONNX model to INT8 for faster inference

    Args:
        input_path: Input ONNX file path
        output_path: Quantized ONNX file path
    """
    try:
        from onnxruntime.quantization import quantize_dynamic, QuantType

        print(f"Quantizing ONNX model: {input_path}")

        quantize_dynamic(
            model_input=input_path,
            model_output=output_path,
            weight_type=QuantType.QInt8,
            optimize_model=True,
            per_channel=True,
            reduce_range=True
        )

        print(f"Quantized model saved to: {output_path}")

        # Check size reduction
        original_size = os.path.getsize(input_path) / (1024 * 1024)  # MB
        quantized_size = os.path.getsize(output_path) / (1024 * 1024)  # MB
        reduction = (1 - quantized_size / original_size) * 100

        print(f"Model size reduced from {original_size:.2f}MB to {quantized_size:.2f}MB ({reduction:.1f}% reduction)")

    except ImportError:
        print("ONNXRuntime quantization not installed")
        print("Install with: pip install onnxruntime-tools")
    except Exception as e:
        print(f"Quantization failed: {e}")


def main():
    parser = argparse.ArgumentParser(description='Export speaker model to ONNX')
    parser.add_argument('--model_id', type=str,
                       default='iic/speech_eres2net_sv_zh-cn_16k-common',
                       help='ModelScope model ID or local model path')
    parser.add_argument('--output', type=str, default='model.onnx',
                       help='Output ONNX file path')
    parser.add_argument('--optimize', action='store_true',
                       help='Optimize ONNX model')
    parser.add_argument('--quantize', action='store_true',
                       help='Quantize model to INT8')
    parser.add_argument('--batch_size', type=int, default=1,
                       help='Batch size for export')
    parser.add_argument('--sequence_length', type=int, default=48000,
                       help='Audio sequence length (samples)')
    parser.add_argument('--cache_dir', type=str, default='./models',
                       help='Directory to cache models')

    args = parser.parse_args()

    # Create output directory
    output_dir = os.path.dirname(args.output) or '.'
    os.makedirs(output_dir, exist_ok=True)

    # Load model
    if os.path.exists(args.model_id):
        # Load local model
        print(f"Loading local model from: {args.model_id}")
        model = torch.jit.load(args.model_id, map_location='cpu')
        config = {'sample_rate': 16000}
    else:
        # Load from ModelScope
        model, config = load_model_from_modelscope(args.model_id, args.cache_dir)

    # Export to ONNX
    export_to_onnx(
        model,
        args.output,
        config,
        args.batch_size,
        args.sequence_length
    )

    # Optimize if requested
    if args.optimize:
        optimized_path = args.output.replace('.onnx', '_optimized.onnx')
        optimize_onnx(args.output, optimized_path)
        args.output = optimized_path

    # Quantize if requested
    if args.quantize:
        quantized_path = args.output.replace('.onnx', '_quantized.onnx')
        quantize_onnx(args.output, quantized_path)

    print("\nExport completed successfully!")


if __name__ == '__main__':
    from typing import Tuple
    main()