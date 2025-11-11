# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

3D-Speaker is an open-source toolkit for single- and multi-modal speaker verification, speaker recognition, and speaker diarization. The project supports multiple deep learning architectures (CAM++, ERes2Net, ERes2NetV2, ECAPA-TDNN, ResNet) and datasets (VoxCeleb, CNCeleb, 3D-Speaker). This repository includes both the full training framework and a production-ready API server for speaker verification inference.

## Common Commands

### Environment Setup
```bash
# Full framework setup
conda create -n 3D-Speaker python=3.8
conda activate 3D-Speaker
pip install -r requirements.txt

# Lightweight inference-only setup
bash setup.sh
pip install -r requirements-inference.txt
```

### API Server Deployment

#### Development Mode
```bash
# Start API server (default port 7001)
bash start.sh

# Or start simple API server (port 5001)
bash start_api_simple.sh

# Custom configuration
python server.py --port 7001 --device cpu
python api_server_simple.py --port 5001
```

#### Production Mode
```bash
# Production deployment with Gunicorn
bash start.sh production
bash start_production.sh

# Stop server
bash stop_server.sh
# Or manually: lsof -ti:7001 | xargs kill -9
```

#### API Testing
```bash
# Health check
curl http://localhost:7001/health

# Test verification
python test_client.py
python test_api.py
python test_verify_api.py

# Concurrency testing
python test_concurrency.py

# Real audio testing
python test_real_audio.py
```

### Model Management
```bash
# Download pretrained models
bash download_model_direct.sh
python download_model.py
python quick_download.py

# Test model loading
python test_model_loading.py
python quick_test.py
```

### Training and Experiments

#### Running Experiments
```bash
# Navigate to experiment directory
cd egs/<dataset>/<model-name>/

# Set Python path and environment
. ./path.sh

# Run full pipeline (stages 1-6)
bash run.sh

# Run specific stages with GPU configuration
bash run.sh --stage 3 --stop_stage 5 --gpus "0 1 2 3"
```

#### Training Models
```bash
# Single GPU training
python speakerlab/bin/train.py --config conf/<model>.yaml --gpu 0 \
       --data data/<dataset>/train/train.csv --exp_dir exp/<model>

# Multi-GPU training with torchrun
torchrun --nproc_per_node=4 speakerlab/bin/train.py --config conf/<model>.yaml --gpu "0 1 2 3" \
         --data data/<dataset>/train/train.csv --noise data/musan/wav.scp --reverb data/rirs/wav.scp --exp_dir exp/<model>

# Self-supervised training
python speakerlab/bin/train_rdino.py --config conf/rdino.yaml
python speakerlab/bin/train_sdpn.py --config conf/sdpn.yaml
```

### Inference with Pretrained Models
```bash
# Speaker verification (ModelScope)
python speakerlab/bin/infer_sv.py --model_id iic/speech_eres2net_sv_zh-cn_16k-common
python speakerlab/bin/infer_sv_batch.py --model_id iic/speech_campplus_sv_zh-cn_16k-common --wavs wav_list.txt

# Lightweight inference
python speakerlab/bin/infer_sv_lite.py --model_id <model_id> --audio1 audio1.wav --audio2 audio2.wav

# MPS (Apple Silicon) optimized
python speakerlab/bin/infer_sv_mps.py --model_id <model_id>

# Self-supervised models
python speakerlab/bin/infer_sv_ssl.py --model_id iic/speech_sdpn_ecapa_tdnn_sv_en_voxceleb_16k

# Speaker diarization
python speakerlab/bin/infer_diarization.py --wav wav_path --out_dir output/
python speakerlab/bin/infer_diarization.py --wav wav_path --out_dir output/ --include_overlap --hf_access_token $HF_TOKEN
```

### Feature Extraction
```bash
# Extract speaker embeddings
python speakerlab/bin/extract.py --config conf/<model>.yaml \
       --checkpoint exp/<model>/models/CKPT-EPOCH-XX-00 \
       --wavs data/test/wav.scp --save_dir embeddings/

# Extract SSL embeddings
python speakerlab/bin/extract_ssl.py --config conf/<model>.yaml \
       --checkpoint exp/<model>/models/CKPT-EPOCH-XX-00 \
       --wavs data/test/wav.scp --save_dir embeddings/
```

### ONNX Export and Runtime
```bash
# Export to ONNX
python speakerlab/bin/export_speaker_embedding_onnx.py \
       --model_id iic/speech_eres2net_sv_en_voxceleb_16k \
       --target_onnx_file model.onnx

python speakerlab/bin/export_to_onnx.py \
       --model_id <model_id> --output models/model.onnx --optimize --quantize

# Build ONNX runtime (C++)
cd runtime/onnxruntime/
mkdir build && cd build
cmake .. && make
```

## Architecture

### Directory Structure
- **egs/** - Experiment recipes for different datasets and models
  - **3dspeaker/** - Recipes for 3D-Speaker dataset (speaker verification, diarization, language identification)
  - **voxceleb/** - Recipes for VoxCeleb dataset (various models including SDPN, RDINO, X-vector)
  - **cnceleb/** - Recipes for CNCeleb dataset
  - **ava-asd/** - Active speaker detection (TalkNet)
  - **semantic_speaker/** - Semantic speaker analysis (BERT-based)
- **speakerlab/** - Core library implementation
  - **bin/** - Training and inference scripts (train.py, extract.py, infer_*.py, export_*.py)
  - **models/** - Model architectures (campplus/, ecapa_tdnn/, eres2net/, rdino/, resnet/, etc.)
  - **dataset/** - Dataset loaders and data augmentation (dataset.py, dataset_rdino.py, dataset_sdpn.py)
  - **loss/** - Loss functions (margin_loss.py, dino_loss.py, sdpn_loss.py, keleo_loss.py)
  - **process/** - Audio processing (augmentation, feature extraction)
  - **utils/** - Utility functions (metrics, schedulers, configuration)
- **runtime/** - Deployment solutions
  - **onnxruntime/** - C++ ONNX runtime implementation
- **Root-level API servers** - Production inference servers
  - **server.py** - Full-featured API server with monitoring
  - **api_server.py** - Complete API with multiple endpoints
  - **api_server_simple.py** - Simplified API server

### API Server Architecture

The repository includes three API server implementations:

1. **server.py** - Main production server
   - Full RESTful API with multiple endpoints
   - Speaker verification, batch verification, embedding extraction
   - Health monitoring and configuration management
   - Designed for production deployment with Gunicorn/Waitress
   - Supports CPU, CUDA, and MPS (Apple Silicon) devices

2. **api_server_simple.py** - Simplified version
   - Lightweight implementation for quick deployment
   - Core speaker verification functionality
   - Minimal dependencies

3. **api_server.py** - Feature-rich API
   - URL-based audio input support
   - Advanced configuration options
   - Comprehensive error handling

#### API Endpoints (server.py)
- `GET /health` - Health check and status
- `POST /verify` - Verify if two audio files are from the same speaker
- `POST /verify_batch` - Batch verification (one reference vs multiple candidates)
- `POST /extract_embedding` - Extract 192-dimensional speaker embedding
- `POST /compare_embeddings` - Compare two pre-extracted embeddings
- `GET /config` - Get current configuration
- `POST /config` - Update configuration (threshold, model path, etc.)

#### API Input Methods
All endpoints support three input methods:
1. File upload (multipart/form-data)
2. URL (JSON with audio_url fields)
3. Local file path (JSON with audio_path fields)

#### Supported Audio Formats
WAV, MP3, FLAC, M4A, OGG, WMA, AAC (automatically converted to 16kHz mono)

### Experiment Pipeline

Each experiment directory (egs/dataset/model/) follows a standard 6-stage pipeline:
1. **Stage 1-2**: Data preparation (prepare_data.sh, prepare_data_csv.py)
   - Downloads and organizes dataset
   - Creates Kaldi-style wav.scp and utt2spk files
   - Generates CSV training index (utt_id, wav_path, speaker_id, duration)
2. **Stage 3**: Model training with data augmentation
   - Multi-GPU distributed training via torchrun
   - On-the-fly augmentation (noise, reverberation, speed perturbation)
3. **Stage 4**: Large-margin fine-tuning (optional)
   - Improves discrimination with larger margins
   - Resumes from stage 3 checkpoint
4. **Stage 5**: Embedding extraction
   - Extracts embeddings from test set
   - Supports parallel extraction with multiple GPUs
5. **Stage 6**: Score computation and evaluation
   - Computes EER, minDCF metrics
   - Generates scores for trial pairs

### Configuration System
- **YAML files** in `egs/<dataset>/<model>/conf/` define:
  - Model architecture (model type, embedding size, layers)
  - Training hyperparameters (learning rate, batch size, epochs, optimizer)
  - Data augmentation (MUSAN noise, RIRs reverberation, speed perturbation)
  - Loss function (AAMSoftmax margin, scale)
- **Environment files**: `.env` and `config.env` for API server configuration
- **path.sh**: Sets up PYTHONPATH and environment for experiments

### Model Architectures
- **CAM++** (campplus/): Context-Aware Model with multi-layer aggregation and channel attention
- **ERes2Net** (eres2net/): Enhanced Res2Net with squeeze-excitation blocks (base, large, huge, V2 variants)
- **ECAPA-TDNN** (ecapa_tdnn/): Emphasized Channel Attention, Propagation and Aggregation
- **ResNet** (resnet/): Standard ResNet architectures (ResNet34, ResNet50, ResNet152, ResNet293)
- **Res2Net** (res2net/): Multi-scale feature extraction with hierarchical connections
- **RDINO** (rdino/): Self-supervised learning with DINO approach
- **SDPN**: Self-supervised learning with dual-path network
- **X-vector** (xvector/): Traditional x-vector architecture

### Training Features
- Multi-GPU distributed training via torchrun
- Dynamic data loading with on-the-fly augmentation
- Curriculum learning with speed perturbation (0.9, 1.0, 1.1)
- Large-margin fine-tuning strategy
- Checkpoint saving and resuming (CKPT-EPOCH-XX-00 format)
- Mixed precision training support
- Gradient accumulation for large batch sizes

### Evaluation Metrics
- **EER** (Equal Error Rate) - Primary metric for speaker verification
- **DER** (Diarization Error Rate) - For speaker diarization tasks
- **minDCF** (minimum Detection Cost Function) - Detection cost at various operating points
- **Cosine similarity** - Direct embedding comparison

### Data Preparation
- **Kaldi-style formats**: wav.scp (audio paths), utt2spk (utterance to speaker mapping)
- **CSV format**: Training data with columns: utt_id, wav_path, speaker_id, duration
- **Filtering**: Support for filtering by duration and speaker count
- **Augmentation datasets**: MUSAN (noise), RIRs (reverberation)

### Augmentation Pipeline
- **Speed perturbation**: 0.9x, 1.0x, 1.1x (triples training data)
- **Noise addition**: MUSAN dataset (music, speech, noise)
- **Reverberation**: RIRs (room impulse responses)
- **SpecAugment**: Spectral masking for robustness

### Model Export and Deployment
- PyTorch to ONNX conversion with dynamic batch size
- Optimized C++ ONNX runtime for CPU inference
- Support for streaming and batch processing
- Quantization support (INT8) for reduced memory
- ModelScope integration for easy model distribution

## Key Implementation Details

### Production Deployment
- **Gunicorn**: Production-grade WSGI server (recommended)
  - Multi-worker support (default: 2 workers)
  - Timeout: 120 seconds
  - Logs: logs/access.log, logs/error.log
- **Waitress**: Cross-platform alternative (Windows-friendly)
- **Systemd service**: speaker-server.service for auto-start
- **Environment variables**: Configured via .env file
- **Port management**: Default port 7001 (configurable)

### Testing and Monitoring
- **test_client.py**: Comprehensive API testing client
- **test_verify_api.py**: Verification endpoint testing
- **test_concurrency.py**: Concurrent request testing
- **test_real_audio.py**: Real audio file testing
- **test_monitoring.py**: Server monitoring tests
- **test.html**: Web-based testing interface

### Model Loading
- Models auto-download from ModelScope on first use (~400MB)
- Cached in `pretrained/` or `models/` directory
- Supports multiple device types: CUDA, MPS (Apple Silicon), CPU
- Lazy loading for faster server startup

### Audio Processing
- Automatic resampling to 16kHz
- Stereo to mono conversion
- Format conversion via soundfile/librosa
- Duration validation (min/max duration checks)
- Temporary file cleanup after processing

### Error Handling
- Comprehensive try-catch blocks in API endpoints
- Detailed error messages returned to client
- Logging for debugging and monitoring
- Graceful degradation on model loading failures

### Performance Considerations
- **Single verification**: ~500ms on CPU
- **Batch processing**: More efficient for multiple comparisons
- **Embedding caching**: Store embeddings to avoid re-computation
- **Concurrent requests**: Supported (10-20 QPS typical)
- **Memory usage**: ~2GB with model loaded

## Available Pretrained Models

From ModelScope (auto-download):
- `iic/speech_eres2net_sv_zh-cn_16k-common` - ERes2Net Chinese (200k speakers)
- `iic/speech_eres2netv2_sv_zh-cn_16k-common` - ERes2NetV2 Chinese
- `iic/speech_campplus_sv_zh-cn_16k-common` - CAM++ Chinese (192-dim embeddings)
- `iic/speech_eres2net_sv_en_voxceleb_16k` - ERes2Net English (VoxCeleb)
- `iic/speech_ecapa_tdnn_sv_en_voxceleb_16k` - ECAPA-TDNN English
- `iic/speech_sdpn_ecapa_tdnn_sv_en_voxceleb_16k` - SDPN self-supervised

## Configuration Files

- **.env** - Main environment configuration (port, device, model, workers)
- **config.env** - Additional configuration options
- **requirements.txt** - Full framework dependencies
- **requirements-inference.txt** - Inference-only dependencies (lightweight)
- **requirements_api.txt** - API server dependencies
- **requirements_api_simple.txt** - Minimal API dependencies

## Documentation Files

- **README.md** - Main project documentation
- **README_INFERENCE.md** - Inference-only setup guide
- **API_README.md** - API quick start guide (Chinese)
- **API_DOCUMENTATION.md** - Detailed API documentation (Chinese)
- **deploy_commands.md** - Deployment commands
- **MONITORING_SETUP.md** - Monitoring configuration
- **MONITORING_FIX.md** - Monitoring troubleshooting
- **RESOURCE_USAGE.md** - Resource usage analysis
