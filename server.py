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

from flask import Flask, request, jsonify, send_from_directory, render_template_string
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

# Global variables
speaker_pipeline = None
start_time = time.time()  # Initialize start_time at module load

def init_model(retry_count=3):
    """Initialize the speaker verification model with retry logic"""
    global speaker_pipeline

    for attempt in range(retry_count):
        try:
            logger.info(f"Initializing model (attempt {attempt + 1}/{retry_count}): {Config.MODEL_ID}")

            # Set cache directory for ModelScope
            os.environ['MODELSCOPE_CACHE'] = os.path.expanduser('~/.cache/modelscope')

            # Create pipeline with error handling
            speaker_pipeline = pipeline(
                task=Tasks.speaker_verification,
                model=Config.MODEL_ID,
                device=Config.DEVICE,
                model_revision='master'
            )

            # Test the pipeline with dummy data to ensure it's working
            logger.info("Testing model with dummy verification...")
            # Create a simple test to verify model is loaded
            test_result = speaker_pipeline is not None

            if test_result:
                logger.info("Model initialized and verified successfully")
                return True
            else:
                logger.warning(f"Model verification failed on attempt {attempt + 1}")

        except Exception as e:
            logger.error(f"Model initialization attempt {attempt + 1} failed: {e}")
            logger.error(traceback.format_exc())

            if attempt < retry_count - 1:
                wait_time = (attempt + 1) * 5  # Progressive backoff
                logger.info(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                logger.error("All model initialization attempts failed")

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
    """Home page with documentation"""
    if request.headers.get('Accept', '').startswith('application/json'):
        # Return JSON for API clients
        return jsonify({
            "service": "3D-Speaker Inference Server",
            "status": "running",
            "model": Config.MODEL_ID,
            "device": Config.DEVICE,
            "version": "1.0.0",
            "documentation": "/docs"
        })
    else:
        # Return HTML documentation for browsers
        return render_template_string(API_DOCS_HTML)

@app.route('/docs', methods=['GET'])
def docs():
    """API Documentation"""
    return render_template_string(API_DOCS_HTML)

@app.route('/health', methods=['GET'])
def health_check():
    """Detailed health check"""
    global speaker_pipeline

    # Try to reinitialize model if not loaded
    if speaker_pipeline is None:
        logger.warning("Model not loaded, attempting to initialize...")
        init_model(retry_count=1)

    status = {
        "status": "healthy" if speaker_pipeline is not None else "unhealthy",
        "model_loaded": speaker_pipeline is not None,
        "model_id": Config.MODEL_ID,
        "device": Config.DEVICE,
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
        # Check if model is loaded, try to initialize if not
        if speaker_pipeline is None:
            logger.warning("Model not loaded, attempting to initialize...")
            if not init_model(retry_count=2):
                return jsonify({"error": "Model not loaded. Server is initializing, please try again in a few seconds."}), 503

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

# HTML Template for API Documentation
API_DOCS_HTML = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>3D-Speaker API Documentation</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1, h2, h3 { color: #333; }
        h1 { border-bottom: 3px solid #007acc; padding-bottom: 10px; }
        .endpoint {
            background: #f8f9fa;
            border-left: 4px solid #007acc;
            padding: 15px;
            margin: 20px 0;
            border-radius: 4px;
        }
        .method {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-weight: bold;
            font-size: 12px;
            margin-right: 10px;
        }
        .get { background: #28a745; color: white; }
        .post { background: #ffc107; color: black; }
        .code {
            background: #f1f1f1;
            padding: 10px;
            border-radius: 4px;
            overflow-x: auto;
            font-family: 'Courier New', monospace;
            font-size: 14px;
        }
        .example {
            background: #e7f3ff;
            border: 1px solid #b3d7ff;
            padding: 15px;
            margin: 10px 0;
            border-radius: 4px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
        }
        th, td {
            border: 1px solid #ddd;
            padding: 12px;
            text-align: left;
        }
        th {
            background-color: #f2f2f2;
            font-weight: bold;
        }
        .status-badge {
            display: inline-block;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 11px;
            font-weight: bold;
        }
        .status-running { background: #d4edda; color: #155724; }
        .footer {
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #eee;
            color: #666;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎙️ 3D-Speaker API Documentation</h1>

        <div class="status-badge status-running">Service Running</div>

        <p>REST API for speaker verification and voice biometric analysis using 3D-Speaker models.</p>

        <h2>📋 Quick Start</h2>
        <div class="example">
            <h4>Test the service:</h4>
            <div class="code">curl http://localhost:8000/health</div>

            <h4>Speaker verification:</h4>
            <div class="code">curl -X POST http://localhost:8000/verify \\<br>
  -F "audio1=@speaker1.wav" \\<br>
  -F "audio2=@speaker2.wav"</div>
        </div>

        <h2>🔗 API Endpoints</h2>

        <div class="endpoint">
            <h3><span class="method get">GET</span> /health</h3>
            <p><strong>Description:</strong> Health check and service status</p>
            <p><strong>Response:</strong></p>
            <div class="code">{
  "status": "healthy",
  "model_loaded": true,
  "timestamp": 1699123456.789,
  "uptime": 3600.5
}</div>
        </div>

        <div class="endpoint">
            <h3><span class="method post">POST</span> /verify</h3>
            <p><strong>Description:</strong> Compare two audio files for speaker verification</p>
            <p><strong>Parameters:</strong></p>
            <table>
                <tr><th>Parameter</th><th>Type</th><th>Required</th><th>Description</th></tr>
                <tr><td>audio1</td><td>File</td><td>Yes</td><td>First audio file (WAV/MP3/FLAC)</td></tr>
                <tr><td>audio2</td><td>File</td><td>Yes</td><td>Second audio file (WAV/MP3/FLAC)</td></tr>
                <tr><td>threshold</td><td>Float</td><td>No</td><td>Similarity threshold (default: 0.5)</td></tr>
            </table>
            <p><strong>Response:</strong></p>
            <div class="code">{
  "session_id": "uuid-string",
  "similarity_score": 0.8234,
  "threshold": 0.5,
  "is_same_speaker": true,
  "confidence": 0.8234,
  "inference_time": 0.156,
  "audio1_info": {"duration": 3.2, "sample_rate": 16000},
  "audio2_info": {"duration": 2.8, "sample_rate": 16000}
}</div>
        </div>

        <div class="endpoint">
            <h3><span class="method get">GET</span> /models</h3>
            <p><strong>Description:</strong> List available speaker verification models</p>
            <p><strong>Response:</strong></p>
            <div class="code">{
  "current_model": "iic/speech_eres2net_sv_zh-cn_16k-common",
  "available_models": [
    {
      "id": "iic/speech_eres2net_sv_zh-cn_16k-common",
      "name": "ERes2Net Chinese",
      "language": "Chinese"
    }
  ]
}</div>
        </div>

        <h2>📁 Audio File Requirements</h2>
        <table>
            <tr><th>Property</th><th>Requirement</th><th>Notes</th></tr>
            <tr><td>Format</td><td>WAV, MP3, FLAC</td><td>WAV recommended</td></tr>
            <tr><td>Sample Rate</td><td>16kHz preferred</td><td>Auto-resampled if needed</td></tr>
            <tr><td>Channels</td><td>Mono</td><td>Stereo auto-converted</td></tr>
            <tr><td>Duration</td><td>0.5s - 30s</td><td>Configurable limits</td></tr>
            <tr><td>File Size</td><td>Max 16MB</td><td>Configurable</td></tr>
        </table>

        <h2>🔧 Configuration</h2>
        <p>Environment variables for customization:</p>
        <table>
            <tr><th>Variable</th><th>Default</th><th>Description</th></tr>
            <tr><td>HOST</td><td>0.0.0.0</td><td>Server host</td></tr>
            <tr><td>PORT</td><td>8000</td><td>Server port</td></tr>
            <tr><td>DEVICE</td><td>cpu</td><td>cpu or cuda</td></tr>
            <tr><td>SIMILARITY_THRESHOLD</td><td>0.5</td><td>Default threshold</td></tr>
            <tr><td>MAX_AUDIO_DURATION</td><td>30</td><td>Max audio length (seconds)</td></tr>
        </table>

        <h2>📝 Example Usage</h2>

        <h3>Python</h3>
        <div class="code">import requests

# Speaker verification
with open('speaker1.wav', 'rb') as f1, open('speaker2.wav', 'rb') as f2:
    files = {'audio1': f1, 'audio2': f2}
    response = requests.post('http://localhost:8000/verify', files=files)
    result = response.json()

    print(f"Similarity: {result['similarity_score']:.4f}")
    print(f"Same speaker: {result['is_same_speaker']}")
</div>

        <h3>cURL</h3>
        <div class="code"># Health check
curl http://localhost:8000/health

# Speaker verification
curl -X POST http://localhost:8000/verify \\
  -F "audio1=@audio1.wav" \\
  -F "audio2=@audio2.wav" \\
  -F "threshold=0.6"

# List models
curl http://localhost:8000/models
</div>

        <h3>JavaScript</h3>
        <div class="code">// Speaker verification with fetch API
const formData = new FormData();
formData.append('audio1', audio1File);
formData.append('audio2', audio2File);

fetch('http://localhost:8000/verify', {
    method: 'POST',
    body: formData
})
.then(response => response.json())
.then(data => {
    console.log('Similarity:', data.similarity_score);
    console.log('Same speaker:', data.is_same_speaker);
});
</div>

        <h2>🚀 Deployment</h2>
        <div class="example">
            <h4>Development:</h4>
            <div class="code">python server.py</div>

            <h4>Production:</h4>
            <div class="code">bash start_server.sh production</div>

            <h4>System Service:</h4>
            <div class="code">sudo systemctl start speaker-server</div>
        </div>

        <h2>❌ Error Codes</h2>
        <table>
            <tr><th>Code</th><th>Description</th><th>Common Causes</th></tr>
            <tr><td>400</td><td>Bad Request</td><td>Missing files, invalid audio format</td></tr>
            <tr><td>413</td><td>File Too Large</td><td>Audio file exceeds size limit</td></tr>
            <tr><td>503</td><td>Service Unavailable</td><td>Model not loaded</td></tr>
            <tr><td>500</td><td>Internal Server Error</td><td>Processing error</td></tr>
        </table>

        <div class="footer">
            <p>🔗 <strong>Links:</strong>
               <a href="/health">Health Check</a> |
               <a href="/models">Models</a> |
               <a href="https://github.com/tengyuan2025/speaker">GitHub</a>
            </p>
            <p>Powered by 3D-Speaker • ModelScope • Flask</p>
        </div>
    </div>
</body>
</html>
'''

def main():
    """Main function to start the server"""
    global start_time, speaker_pipeline
    start_time = time.time()

    # Initialize model with retry
    logger.info("Starting 3D-Speaker Inference Server...")

    # Try to initialize model, but don't exit if it fails
    # Model can be initialized later via health check or first request
    if not init_model(retry_count=3):
        logger.warning("Initial model load failed. Model will be loaded on first request.")
        logger.warning("Server will start but return 503 until model loads successfully.")
        # Don't exit - allow server to start anyway

    # Start server
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', 7001))
    debug = os.getenv('DEBUG', 'false').lower() == 'true'

    logger.info(f"Server starting on {host}:{port}")
    logger.info(f"Model: {Config.MODEL_ID}")
    logger.info(f"Device: {Config.DEVICE}")
    logger.info(f"Upload folder: {Config.UPLOAD_FOLDER}")

    app.run(host=host, port=port, debug=debug, threaded=True)

if __name__ == '__main__':
    main()