#!/usr/bin/env python3
"""
Production Server for 3D-Speaker Lightweight Inference
Provides REST API for speaker verification and embedding extraction
"""

import os
import io
import time
import uuid
import logging
import traceback
from pathlib import Path
from typing import Dict, Any, Optional

from flask import Flask, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
import soundfile as sf
import numpy as np
from modelscope.pipelines import pipeline
from modelscope.utils.constant import Tasks

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Configuration
class Config:
    MODEL_ID = os.getenv('SPEAKER_MODEL_ID', 'iic/speech_eres2net_sv_zh-cn_16k-common')
    DEVICE = os.getenv('DEVICE', 'cpu')
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', './uploads')
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))  # 16MB
    SIMILARITY_THRESHOLD = float(os.getenv('SIMILARITY_THRESHOLD', 0.5))
    CACHE_DIR = os.getenv('CACHE_DIR', './models')

    # Audio constraints
    MAX_DURATION = int(os.getenv('MAX_AUDIO_DURATION', 30))  # seconds
    MIN_DURATION = float(os.getenv('MIN_AUDIO_DURATION', 0.5))  # seconds

app.config.from_object(Config)

# Create directories
os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
os.makedirs(Config.CACHE_DIR, exist_ok=True)

# Global model instance
speaker_pipeline = None

def init_model():
    """Initialize the speaker verification model"""
    global speaker_pipeline

    try:
        logger.info(f"Initializing speaker verification model: {Config.MODEL_ID}")
        speaker_pipeline = pipeline(
            task=Tasks.speaker_verification,
            model=Config.MODEL_ID,
            device=Config.DEVICE,
            model_revision='master'
        )
        logger.info("Model initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize model: {e}")
        logger.error(traceback.format_exc())
        return False

def validate_audio_file(file_path: str) -> Dict[str, Any]:
    """Validate uploaded audio file"""
    try:
        # Read audio file
        data, sample_rate = sf.read(file_path)

        # Convert to mono if stereo
        if len(data.shape) > 1:
            data = np.mean(data, axis=1)

        duration = len(data) / sample_rate

        # Check duration constraints
        if duration < Config.MIN_DURATION:
            return {"valid": False, "error": f"Audio too short: {duration:.2f}s (min: {Config.MIN_DURATION}s)"}

        if duration > Config.MAX_DURATION:
            return {"valid": False, "error": f"Audio too long: {duration:.2f}s (max: {Config.MAX_DURATION}s)"}

        return {
            "valid": True,
            "duration": duration,
            "sample_rate": sample_rate,
            "channels": "mono" if len(data.shape) == 1 else "stereo"
        }

    except Exception as e:
        return {"valid": False, "error": f"Invalid audio file: {str(e)}"}

@app.route('/', methods=['GET'])
def home():
    """Health check endpoint"""
    return jsonify({
        "service": "3D-Speaker Inference Server",
        "status": "running",
        "model": Config.MODEL_ID,
        "device": Config.DEVICE,
        "version": "1.0.0"
    })

@app.route('/health', methods=['GET'])
def health_check():
    """Detailed health check"""
    status = {
        "status": "healthy" if speaker_pipeline is not None else "unhealthy",
        "model_loaded": speaker_pipeline is not None,
        "timestamp": time.time(),
        "uptime": time.time() - start_time
    }

    return jsonify(status), 200 if speaker_pipeline else 503

@app.route('/verify', methods=['POST'])
def verify_speakers():
    """
    Speaker verification endpoint
    Accepts two audio files and returns similarity score
    """
    try:
        # Check if model is loaded
        if speaker_pipeline is None:
            return jsonify({"error": "Model not loaded"}), 503

        # Check if files are provided
        if 'audio1' not in request.files or 'audio2' not in request.files:
            return jsonify({"error": "Both 'audio1' and 'audio2' files are required"}), 400

        audio1_file = request.files['audio1']
        audio2_file = request.files['audio2']

        # Check if files are selected
        if audio1_file.filename == '' or audio2_file.filename == '':
            return jsonify({"error": "No file selected"}), 400

        # Generate unique session ID
        session_id = str(uuid.uuid4())

        # Save uploaded files
        filename1 = f"{session_id}_1_{secure_filename(audio1_file.filename)}"
        filename2 = f"{session_id}_2_{secure_filename(audio2_file.filename)}"

        filepath1 = os.path.join(Config.UPLOAD_FOLDER, filename1)
        filepath2 = os.path.join(Config.UPLOAD_FOLDER, filename2)

        audio1_file.save(filepath1)
        audio2_file.save(filepath2)

        try:
            # Validate audio files
            validation1 = validate_audio_file(filepath1)
            if not validation1["valid"]:
                return jsonify({"error": f"Audio1: {validation1['error']}"}), 400

            validation2 = validate_audio_file(filepath2)
            if not validation2["valid"]:
                return jsonify({"error": f"Audio2: {validation2['error']}"}), 400

            # Get threshold from request or use default
            threshold = request.form.get('threshold', Config.SIMILARITY_THRESHOLD, type=float)

            # Perform speaker verification
            start_time = time.time()
            result = speaker_pipeline([filepath1, filepath2])
            inference_time = time.time() - start_time

            # Prepare response
            similarity_score = float(result['score'])
            is_same_speaker = similarity_score >= threshold

            response = {
                "session_id": session_id,
                "similarity_score": similarity_score,
                "threshold": threshold,
                "is_same_speaker": is_same_speaker,
                "confidence": similarity_score if is_same_speaker else (1 - similarity_score),
                "inference_time": round(inference_time, 3),
                "audio1_info": {
                    "filename": audio1_file.filename,
                    "duration": round(validation1["duration"], 2),
                    "sample_rate": validation1["sample_rate"]
                },
                "audio2_info": {
                    "filename": audio2_file.filename,
                    "duration": round(validation2["duration"], 2),
                    "sample_rate": validation2["sample_rate"]
                }
            }

            logger.info(f"Verification completed - Session: {session_id}, Score: {similarity_score:.4f}, Time: {inference_time:.3f}s")

            return jsonify(response)

        finally:
            # Clean up uploaded files
            try:
                os.remove(filepath1)
                os.remove(filepath2)
            except Exception as e:
                logger.warning(f"Failed to cleanup files: {e}")

    except Exception as e:
        logger.error(f"Verification error: {e}")
        logger.error(traceback.format_exc())
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

@app.route('/extract', methods=['POST'])
def extract_embedding():
    """
    Extract speaker embedding from audio file
    """
    try:
        if speaker_pipeline is None:
            return jsonify({"error": "Model not loaded"}), 503

        if 'audio' not in request.files:
            return jsonify({"error": "Audio file is required"}), 400

        audio_file = request.files['audio']

        if audio_file.filename == '':
            return jsonify({"error": "No file selected"}), 400

        # Save uploaded file
        session_id = str(uuid.uuid4())
        filename = f"{session_id}_{secure_filename(audio_file.filename)}"
        filepath = os.path.join(Config.UPLOAD_FOLDER, filename)
        audio_file.save(filepath)

        try:
            # Validate audio file
            validation = validate_audio_file(filepath)
            if not validation["valid"]:
                return jsonify({"error": validation["error"]}), 400

            # Extract embedding (this is a simplified version)
            # Note: ModelScope pipeline doesn't directly expose embedding extraction
            # You would need to use the actual model for this

            response = {
                "session_id": session_id,
                "filename": audio_file.filename,
                "audio_info": {
                    "duration": round(validation["duration"], 2),
                    "sample_rate": validation["sample_rate"]
                },
                "message": "Embedding extraction not implemented in this version. Use the infer_sv_lite.py script for embedding extraction."
            }

            return jsonify(response)

        finally:
            # Clean up uploaded file
            try:
                os.remove(filepath)
            except Exception as e:
                logger.warning(f"Failed to cleanup file: {e}")

    except Exception as e:
        logger.error(f"Embedding extraction error: {e}")
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

@app.route('/models', methods=['GET'])
def list_models():
    """List available models"""
    models = [
        {
            "id": "iic/speech_eres2net_sv_zh-cn_16k-common",
            "name": "ERes2Net Chinese",
            "language": "Chinese",
            "description": "ERes2Net model for Chinese speakers"
        },
        {
            "id": "iic/speech_eres2net_sv_en_voxceleb_16k",
            "name": "ERes2Net English",
            "language": "English",
            "description": "ERes2Net model trained on VoxCeleb"
        },
        {
            "id": "iic/speech_campplus_sv_zh-cn_16k-common",
            "name": "CAM++ Chinese",
            "language": "Chinese",
            "description": "CAM++ model for Chinese speakers"
        }
    ]

    return jsonify({
        "current_model": Config.MODEL_ID,
        "available_models": models
    })

@app.errorhandler(413)
def file_too_large(error):
    return jsonify({"error": "File too large"}), 413

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500

def main():
    """Main function to start the server"""
    global start_time
    start_time = time.time()

    # Initialize model
    logger.info("Starting 3D-Speaker Inference Server...")

    if not init_model():
        logger.error("Failed to initialize model. Exiting.")
        return 1

    # Start server
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', 8000))
    debug = os.getenv('DEBUG', 'false').lower() == 'true'

    logger.info(f"Server starting on {host}:{port}")
    logger.info(f"Model: {Config.MODEL_ID}")
    logger.info(f"Device: {Config.DEVICE}")
    logger.info(f"Upload folder: {Config.UPLOAD_FOLDER}")

    app.run(host=host, port=port, debug=debug, threaded=True)

if __name__ == '__main__':
    main()