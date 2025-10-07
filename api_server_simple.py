#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Simple API server for speaker verification without modelscope dependency
Uses the native 3D-Speaker implementation
"""

import os
import sys
import time
import tempfile
import hashlib
from pathlib import Path
from flask import Flask, request, jsonify
from flask_cors import CORS
import numpy as np
import torch
import torchaudio
import logging
from concurrent.futures import ThreadPoolExecutor
import requests
from werkzeug.utils import secure_filename

# Add project path to system path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from speakerlab.process.processor import FBank
    from speakerlab.utils.builder import dynamic_import
except ImportError:
    print("Error: Cannot import speakerlab modules. Make sure you're in the 3D-Speaker directory.")
    sys.exit(1)

# Configure logging with both file and console output
log_dir = Path(__file__).parent / 'logs'
log_dir.mkdir(exist_ok=True)
log_file = log_dir / f'api_server_{time.strftime("%Y%m%d")}.log'

# Create formatters
detailed_formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
)
simple_formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s'
)

# File handler (detailed logs)
file_handler = logging.FileHandler(log_file)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(detailed_formatter)

# Console handler (simple logs)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(simple_formatter)

# Configure root logger
logging.basicConfig(
    level=logging.DEBUG,
    handlers=[file_handler, console_handler]
)
logger = logging.getLogger(__name__)

# Print log file location
print(f"📝 日志文件: {log_file}")

# Request statistics
class RequestStats:
    def __init__(self):
        self.total_requests = 0
        self.success_requests = 0
        self.failed_requests = 0
        self.total_time = 0.0
        self.start_time = time.time()

    def record_request(self, success: bool, duration: float):
        self.total_requests += 1
        if success:
            self.success_requests += 1
        else:
            self.failed_requests += 1
        self.total_time += duration

    def get_stats(self):
        uptime = time.time() - self.start_time
        avg_time = self.total_time / self.total_requests if self.total_requests > 0 else 0
        success_rate = self.success_requests / self.total_requests * 100 if self.total_requests > 0 else 0

        return {
            'total_requests': self.total_requests,
            'success_requests': self.success_requests,
            'failed_requests': self.failed_requests,
            'success_rate': f'{success_rate:.2f}%',
            'avg_response_time': f'{avg_time:.3f}s',
            'uptime': f'{uptime:.0f}s'
        }

stats = RequestStats()

app = Flask(__name__)
CORS(app)  # Allow cross-origin requests

# Configuration
class Config:
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # Max file size 50MB
    ALLOWED_EXTENSIONS = {'wav', 'mp3', 'flac', 'm4a', 'ogg', 'wma', 'aac'}
    DEVICE = 'cuda' if torch.cuda.is_available() else 'cpu'
    THRESHOLD = 0.5  # Similarity threshold
    CACHE_DIR = Path(tempfile.gettempdir()) / 'speaker_verification_cache'

    # Default model configuration (CAM++ with 192-dim embeddings)
    MODEL_CONFIG = {
        'obj': 'speakerlab.models.campplus.DTDNN.CAMPPlus',
        'args': {
            'feat_dim': 80,
            'embedding_size': 192,
        },
    }
    MODEL_PATH = None  # Will be set when loading model

app.config.from_object(Config)
app.config['CACHE_DIR'].mkdir(exist_ok=True)

# Global variables
model = None
feature_extractor = None
executor = ThreadPoolExecutor(max_workers=4)

def init_model(model_path=None):
    """Initialize speaker verification model"""
    global model, feature_extractor

    if model is None:
        try:
            logger.info(f"Loading model on device: {app.config['DEVICE']}")

            # Initialize feature extractor
            feature_extractor = FBank(n_mels=80, sample_rate=16000)

            # Load model
            model_config = app.config['MODEL_CONFIG']
            model_class = dynamic_import(model_config['obj'])
            model = model_class(**model_config['args'])

            # Load checkpoint if provided
            if model_path:
                # If it's a directory, look for model files
                if os.path.isdir(model_path):
                    possible_files = [
                        'campplus_cn_common.bin',
                        'campplus_cn_common.pt',
                        'model.pt',
                        'model.bin',
                        'pytorch_model.bin'
                    ]
                    for fname in possible_files:
                        full_path = os.path.join(model_path, fname)
                        if os.path.exists(full_path):
                            model_path = full_path
                            break

                if os.path.exists(model_path):
                    logger.info(f"Loading checkpoint from {model_path}")
                    checkpoint = torch.load(model_path, map_location='cpu')

                    # Handle different checkpoint formats
                    if isinstance(checkpoint, dict):
                        if 'model' in checkpoint:
                            model.load_state_dict(checkpoint['model'])
                        elif 'state_dict' in checkpoint:
                            model.load_state_dict(checkpoint['state_dict'])
                        elif 'model_state_dict' in checkpoint:
                            model.load_state_dict(checkpoint['model_state_dict'])
                        else:
                            # Assume the checkpoint is the state_dict directly
                            model.load_state_dict(checkpoint)
                    else:
                        # If checkpoint is not a dict, assume it's the state_dict
                        model.load_state_dict(checkpoint)

                    app.config['MODEL_PATH'] = model_path
            else:
                logger.warning("No model checkpoint provided. Using random initialized model.")
                logger.warning("Please download a pretrained model or provide a checkpoint path.")

            model = model.to(app.config['DEVICE'])
            model.eval()

            logger.info("Model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise

def allowed_file(filename):
    """Check if file type is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def download_audio(url, save_path):
    """Download audio file from URL"""
    try:
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()

        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except Exception as e:
        logger.error(f"Failed to download audio from {url}: {e}")
        return False

def get_audio_path(audio_source):
    """Process audio source, return local file path"""
    temp_file = None

    # If file upload
    if hasattr(audio_source, 'read'):
        if not allowed_file(audio_source.filename):
            raise ValueError(f"File type not allowed: {audio_source.filename}")

        # Save uploaded file
        filename = secure_filename(audio_source.filename)
        temp_file = app.config['CACHE_DIR'] / f"{time.time()}_{filename}"
        audio_source.save(str(temp_file))
        return str(temp_file), True

    # If URL
    elif isinstance(audio_source, str) and audio_source.startswith(('http://', 'https://')):
        # Download from URL
        url_hash = hashlib.md5(audio_source.encode()).hexdigest()
        temp_file = app.config['CACHE_DIR'] / f"{url_hash}.audio"

        if not temp_file.exists():
            if not download_audio(audio_source, temp_file):
                raise ValueError(f"Failed to download audio from URL: {audio_source}")

        return str(temp_file), True

    # If local path
    elif isinstance(audio_source, str):
        if not Path(audio_source).exists():
            raise ValueError(f"File not found: {audio_source}")
        return audio_source, False

    else:
        raise ValueError("Invalid audio source type")

def extract_embedding(audio_path):
    """Extract speaker embedding from audio"""
    try:
        # Load and resample audio if necessary
        waveform, sample_rate = torchaudio.load(audio_path)

        # Convert to mono if stereo
        if waveform.shape[0] > 1:
            waveform = torch.mean(waveform, dim=0, keepdim=True)

        # Resample to 16kHz if needed
        if sample_rate != 16000:
            resampler = torchaudio.transforms.Resample(sample_rate, 16000)
            waveform = resampler(waveform)

        # Extract features
        with torch.no_grad():
            features = feature_extractor(waveform)
            features = features.unsqueeze(0).to(app.config['DEVICE'])

            # Forward through model
            embeddings = model(features)

            # Normalize embeddings
            embeddings = embeddings / torch.norm(embeddings, dim=1, keepdim=True)

        return embeddings[0].cpu().numpy()

    except Exception as e:
        logger.error(f"Failed to extract embedding: {e}")
        return None

def compute_similarity(emb1, emb2):
    """Compute cosine similarity between two embeddings"""
    return np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))

def verify_speakers(audio1_path, audio2_path):
    """Verify if two audio samples are from the same speaker"""
    try:
        emb1 = extract_embedding(audio1_path)
        emb2 = extract_embedding(audio2_path)

        if emb1 is None or emb2 is None:
            return {
                'success': False,
                'error': 'Failed to extract embeddings'
            }

        score = compute_similarity(emb1, emb2)
        is_same = score > app.config['THRESHOLD']

        return {
            'success': True,
            'score': float(score),
            'is_same_speaker': is_same,
            'threshold': app.config['THRESHOLD'],
            'confidence': 'high' if abs(score - app.config['THRESHOLD']) > 0.2 else 'medium'
        }
    except Exception as e:
        logger.error(f"Verification failed: {e}")
        return {
            'success': False,
            'error': str(e)
        }

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'model_loaded': model is not None,
        'device': app.config['DEVICE'],
        'model_path': str(app.config['MODEL_PATH']) if app.config['MODEL_PATH'] else 'No checkpoint loaded'
    })

@app.route('/verify', methods=['POST'])
def verify():
    """
    Speaker verification endpoint
    Supports three methods:
    1. File upload: multipart/form-data with audio1 and audio2 fields
    2. URL: JSON body with audio1_url and audio2_url
    3. Local path: JSON body with audio1_path and audio2_path
    """
    temp_files = []

    try:
        # Initialize model if needed
        if model is None:
            return jsonify({
                'success': False,
                'error': 'Model not loaded. Please provide a model checkpoint.'
            }), 500

        # Get audio sources
        audio1_source = None
        audio2_source = None

        # Check file uploads
        if 'audio1' in request.files and 'audio2' in request.files:
            audio1_source = request.files['audio1']
            audio2_source = request.files['audio2']

        # Check JSON request
        elif request.json:
            data = request.json
            if 'audio1_url' in data and 'audio2_url' in data:
                audio1_source = data['audio1_url']
                audio2_source = data['audio2_url']
            elif 'audio1_path' in data and 'audio2_path' in data:
                audio1_source = data['audio1_path']
                audio2_source = data['audio2_path']

        if not audio1_source or not audio2_source:
            return jsonify({
                'success': False,
                'error': 'Missing audio sources. Provide either files, URLs, or paths'
            }), 400

        # Process audio files
        audio1_path, is_temp1 = get_audio_path(audio1_source)
        audio2_path, is_temp2 = get_audio_path(audio2_source)

        if is_temp1:
            temp_files.append(audio1_path)
        if is_temp2:
            temp_files.append(audio2_path)

        # Perform verification
        result = verify_speakers(audio1_path, audio2_path)

        return jsonify(result)

    except Exception as e:
        logger.error(f"Request failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

    finally:
        # Clean up temporary files
        for temp_file in temp_files:
            try:
                Path(temp_file).unlink()
            except:
                pass

@app.route('/extract_embedding', methods=['POST'])
def extract():
    """
    Extract speaker embedding endpoint
    Returns a 192-dimensional feature vector
    """
    temp_file = None

    try:
        if model is None:
            return jsonify({
                'success': False,
                'error': 'Model not loaded. Please provide a model checkpoint.'
            }), 500

        # Get audio source
        audio_source = None

        if 'audio' in request.files:
            audio_source = request.files['audio']
        elif request.json:
            data = request.json
            audio_source = data.get('audio_url') or data.get('audio_path')

        if not audio_source:
            return jsonify({
                'success': False,
                'error': 'Missing audio source'
            }), 400

        # Process audio file
        audio_path, is_temp = get_audio_path(audio_source)
        if is_temp:
            temp_file = audio_path

        # Extract features
        embedding = extract_embedding(audio_path)

        if embedding is not None:
            return jsonify({
                'success': True,
                'embedding': embedding.tolist(),
                'dimension': len(embedding)
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to extract embedding'
            }), 500

    except Exception as e:
        logger.error(f"Embedding extraction failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

    finally:
        if temp_file:
            try:
                Path(temp_file).unlink()
            except:
                pass

@app.route('/compare_embeddings', methods=['POST'])
def compare_embeddings():
    """
    Compare similarity between two embeddings
    """
    try:
        data = request.json
        if not data or 'embedding1' not in data or 'embedding2' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing embeddings'
            }), 400

        emb1 = np.array(data['embedding1'])
        emb2 = np.array(data['embedding2'])

        # Compute cosine similarity
        similarity = compute_similarity(emb1, emb2)

        return jsonify({
            'success': True,
            'similarity': float(similarity),
            'is_same_speaker': similarity > app.config['THRESHOLD'],
            'threshold': app.config['THRESHOLD']
        })

    except Exception as e:
        logger.error(f"Embedding comparison failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/config', methods=['GET', 'POST'])
def config():
    """
    Get or update configuration
    """
    if request.method == 'GET':
        return jsonify({
            'device': app.config['DEVICE'],
            'threshold': app.config['THRESHOLD'],
            'max_file_size': app.config['MAX_CONTENT_LENGTH'],
            'allowed_extensions': list(app.config['ALLOWED_EXTENSIONS']),
            'model_path': str(app.config['MODEL_PATH']) if app.config['MODEL_PATH'] else None
        })

    else:  # POST
        data = request.json
        if 'threshold' in data:
            app.config['THRESHOLD'] = float(data['threshold'])

        if 'model_path' in data:
            # Reload model with new checkpoint
            global model
            model = None
            init_model(data['model_path'])

        return jsonify({'success': True, 'config': {
            'threshold': app.config['THRESHOLD'],
            'model_path': str(app.config['MODEL_PATH']) if app.config['MODEL_PATH'] else None
        }})

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Speaker Verification API Server')
    parser.add_argument('--model_path', type=str, help='Path to model checkpoint')
    parser.add_argument('--port', type=int, default=5000, help='Server port')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='Server host')

    args = parser.parse_args()

    # Load model if checkpoint provided
    if args.model_path:
        logger.info(f"Loading model from {args.model_path}")
        init_model(args.model_path)
    else:
        logger.warning("No model checkpoint provided. Starting without model.")
        logger.warning("You can download a pretrained model from:")
        logger.warning("https://www.modelscope.cn/models/iic/speech_campplus_sv_zh-cn_16k-common")
        logger.warning("Or provide a checkpoint using --model_path argument")

    # Start server
    logger.info(f"Starting Speaker Verification API Server on {args.host}:{args.port}")
    app.run(
        host=args.host,
        port=args.port,
        debug=False,
        threaded=True
    )