#!/usr/bin/env python3
"""
Lightweight speaker verification inference using ModelScope and ONNX
This script provides efficient inference without the full 3D-Speaker framework
"""

import os
import argparse
import numpy as np
import torch
import torchaudio
import soundfile as sf
from typing import Tuple, Optional
from modelscope.hub.file_download import model_file_download
from modelscope.hub.snapshot_download import snapshot_download


class LiteSpeakerVerification:
    """Lightweight speaker verification using pre-trained models"""

    def __init__(self, model_id: str, cache_dir: str = "./models", device: str = "cpu"):
        """
        Initialize the speaker verification model

        Args:
            model_id: ModelScope model ID (e.g., 'iic/speech_eres2net_sv_zh-cn_16k-common')
            cache_dir: Directory to cache downloaded models
            device: Device to run inference on ('cpu' or 'cuda')
        """
        self.model_id = model_id
        self.cache_dir = cache_dir
        self.device = device

        # Create cache directory
        os.makedirs(cache_dir, exist_ok=True)

        # Download and load model
        self._download_and_load_model()

    def _download_and_load_model(self):
        """Download model from ModelScope and load it"""
        print(f"Downloading model: {self.model_id}")

        # Download model snapshot
        model_dir = snapshot_download(
            self.model_id,
            cache_dir=self.cache_dir,
            revision='master'
        )

        # Load model configuration
        import yaml
        config_path = os.path.join(model_dir, 'model.yaml')
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                self.config = yaml.safe_load(f)
        else:
            # Default configuration for common models
            self.config = {
                'sample_rate': 16000,
                'embedding_size': 192,
                'model_type': 'ERes2Net'
            }

        # Load PyTorch model
        model_path = os.path.join(model_dir, 'model.pt')
        if os.path.exists(model_path):
            self.model = torch.jit.load(model_path, map_location=self.device)
            self.model.eval()
        else:
            # Try loading from checkpoint
            ckpt_path = os.path.join(model_dir, 'model.ckpt')
            if os.path.exists(ckpt_path):
                checkpoint = torch.load(ckpt_path, map_location=self.device)
                # Create model based on config
                from speakerlab.models import build_model
                self.model = build_model(self.config)
                self.model.load_state_dict(checkpoint['state_dict'])
                self.model.to(self.device)
                self.model.eval()
            else:
                raise FileNotFoundError(f"No model file found in {model_dir}")

        print(f"Model loaded successfully on {self.device}")

    def load_audio(self, audio_path: str) -> torch.Tensor:
        """
        Load and preprocess audio file

        Args:
            audio_path: Path to audio file

        Returns:
            Preprocessed audio tensor
        """
        # Load audio
        waveform, sample_rate = torchaudio.load(audio_path)

        # Convert to mono if needed
        if waveform.shape[0] > 1:
            waveform = torch.mean(waveform, dim=0, keepdim=True)

        # Resample if needed
        target_sr = self.config.get('sample_rate', 16000)
        if sample_rate != target_sr:
            resampler = torchaudio.transforms.Resample(sample_rate, target_sr)
            waveform = resampler(waveform)

        return waveform

    def extract_embedding(self, audio_path: str) -> np.ndarray:
        """
        Extract speaker embedding from audio file

        Args:
            audio_path: Path to audio file

        Returns:
            Speaker embedding vector
        """
        # Load and preprocess audio
        waveform = self.load_audio(audio_path)
        waveform = waveform.to(self.device)

        # Extract embedding
        with torch.no_grad():
            if hasattr(self.model, 'extract_embedding'):
                embedding = self.model.extract_embedding(waveform)
            else:
                # Direct forward pass for JIT models
                embedding = self.model(waveform)

            # Convert to numpy
            if isinstance(embedding, torch.Tensor):
                embedding = embedding.cpu().numpy()

        # Normalize embedding
        embedding = embedding / np.linalg.norm(embedding)

        return embedding.squeeze()

    def compute_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Compute cosine similarity between two embeddings

        Args:
            embedding1: First speaker embedding
            embedding2: Second speaker embedding

        Returns:
            Cosine similarity score
        """
        # Ensure embeddings are normalized
        embedding1 = embedding1 / np.linalg.norm(embedding1)
        embedding2 = embedding2 / np.linalg.norm(embedding2)

        # Compute cosine similarity
        similarity = np.dot(embedding1, embedding2)

        return float(similarity)

    def verify(self, audio1: str, audio2: str, threshold: float = 0.5) -> Tuple[bool, float]:
        """
        Verify if two audio files are from the same speaker

        Args:
            audio1: Path to first audio file
            audio2: Path to second audio file
            threshold: Similarity threshold for verification

        Returns:
            Tuple of (is_same_speaker, similarity_score)
        """
        # Extract embeddings
        print(f"Extracting embedding from {audio1}")
        embedding1 = self.extract_embedding(audio1)

        print(f"Extracting embedding from {audio2}")
        embedding2 = self.extract_embedding(audio2)

        # Compute similarity
        similarity = self.compute_similarity(embedding1, embedding2)

        # Make decision
        is_same = similarity >= threshold

        return is_same, similarity


def main():
    parser = argparse.ArgumentParser(description='Lightweight Speaker Verification')
    parser.add_argument('--model_id', type=str,
                       default='iic/speech_eres2net_sv_zh-cn_16k-common',
                       help='ModelScope model ID')
    parser.add_argument('--audio1', type=str, required=True,
                       help='Path to first audio file')
    parser.add_argument('--audio2', type=str, required=True,
                       help='Path to second audio file')
    parser.add_argument('--threshold', type=float, default=0.5,
                       help='Similarity threshold for verification')
    parser.add_argument('--device', type=str, default='cpu',
                       choices=['cpu', 'cuda'],
                       help='Device to run inference on')
    parser.add_argument('--cache_dir', type=str, default='./models',
                       help='Directory to cache models')

    args = parser.parse_args()

    # Check if CUDA is available
    if args.device == 'cuda' and not torch.cuda.is_available():
        print("CUDA not available, falling back to CPU")
        args.device = 'cpu'

    # Initialize model
    sv_model = LiteSpeakerVerification(
        model_id=args.model_id,
        cache_dir=args.cache_dir,
        device=args.device
    )

    # Perform verification
    is_same, similarity = sv_model.verify(
        args.audio1,
        args.audio2,
        args.threshold
    )

    # Print results
    print(f"\n{'='*50}")
    print(f"Audio 1: {args.audio1}")
    print(f"Audio 2: {args.audio2}")
    print(f"Similarity Score: {similarity:.4f}")
    print(f"Threshold: {args.threshold}")
    print(f"Result: {'Same Speaker' if is_same else 'Different Speakers'}")
    print(f"{'='*50}\n")


if __name__ == '__main__':
    main()