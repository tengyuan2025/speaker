# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

3D-Speaker is an open-source toolkit for single- and multi-modal speaker verification, speaker recognition, and speaker diarization. The project supports multiple deep learning architectures (CAM++, ERes2Net, ERes2NetV2, ECAPA-TDNN, ResNet) and datasets (VoxCeleb, CNCeleb, 3D-Speaker).

## Common Commands

### Environment Setup
```bash
# Create conda environment
conda create -n 3D-Speaker python=3.8
conda activate 3D-Speaker
pip install -r requirements.txt
```

### Running Experiments
```bash
# Navigate to experiment directory
cd egs/<dataset>/<model-name>/
# Set Python path and environment
. ./path.sh
# Run full pipeline
bash run.sh
# Run specific stages with GPU configuration
bash run.sh --stage 3 --stop_stage 5 --gpus "0 1 2 3"
```

### Training Models
```bash
# Single GPU training
python speakerlab/bin/train.py --config conf/<model>.yaml --gpu 0 \
       --data data/<dataset>/train/train.csv --exp_dir exp/<model>

# Multi-GPU training with torchrun
torchrun --nproc_per_node=4 speakerlab/bin/train.py --config conf/<model>.yaml --gpu "0 1 2 3" \
         --data data/<dataset>/train/train.csv --noise data/musan/wav.scp --reverb data/rirs/wav.scp --exp_dir exp/<model>
```

### Inference with Pretrained Models
```bash
# Speaker verification
python speakerlab/bin/infer_sv.py --model_id iic/speech_eres2net_sv_zh-cn_16k-common
python speakerlab/bin/infer_sv_batch.py --model_id iic/speech_campplus_sv_zh-cn_16k-common --wavs wav_list.txt

# Speaker diarization
python speakerlab/bin/infer_diarization.py --wav wav_path --out_dir output/
python speakerlab/bin/infer_diarization.py --wav wav_path --out_dir output/ --include_overlap --hf_access_token $HF_TOKEN

# Self-supervised models
python speakerlab/bin/infer_sv_ssl.py --model_id iic/speech_sdpn_ecapa_tdnn_sv_en_voxceleb_16k
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

# Build ONNX runtime
cd runtime/onnxruntime/
mkdir build && cd build
cmake .. && make
```

## Architecture

### Directory Structure
- **egs/** - Experiment recipes for different datasets and models
  - **3dspeaker/** - Recipes for 3D-Speaker dataset
  - **voxceleb/** - Recipes for VoxCeleb dataset  
  - **cnceleb/** - Recipes for CNCeleb dataset
- **speakerlab/** - Core library implementation
  - **bin/** - Training and inference scripts
  - **models/** - Model architectures (CAM++, ERes2Net, ECAPA-TDNN, etc.)
  - **dataset/** - Dataset loaders and data augmentation
  - **loss/** - Loss functions (AAMSoftmax, SubCenter-AAMSoftmax, etc.)
  - **process/** - Audio processing (augmentation, feature extraction)
  - **utils/** - Utility functions (metrics, schedulers, configuration)
- **runtime/** - Deployment solutions
  - **onnxruntime/** - C++ ONNX runtime implementation

### Experiment Pipeline
Each experiment directory (egs/dataset/model/) follows a standard pipeline:
1. **Stage 1-2**: Data preparation (prepare_data.sh, prepare_data_csv.py)
2. **Stage 3**: Model training with data augmentation
3. **Stage 4**: Large-margin fine-tuning (optional)
4. **Stage 5**: Embedding extraction
5. **Stage 6**: Score computation and evaluation

### Configuration System
- YAML configuration files in `conf/` define model architecture, training hyperparameters, and data augmentation
- Key parameters: model type, embedding size, learning rate, batch size, number of epochs
- Support for noise augmentation (MUSAN) and reverberation (RIRs)

### Model Architectures
- **CAM++**: Channel and context-aware model with multi-layer aggregation
- **ERes2Net**: Enhanced Res2Net with squeeze-excitation blocks
- **ERes2NetV2**: Improved version with better efficiency
- **ECAPA-TDNN**: Emphasized channel attention, propagation and aggregation
- **ResNet**: Standard ResNet architectures (ResNet34, ResNet50)
- **Res2Net**: Multi-scale feature extraction
- **RDINO/SDPN**: Self-supervised learning approaches

### Training Features
- Multi-GPU distributed training via torchrun
- Dynamic data loading with on-the-fly augmentation
- Curriculum learning with speed perturbation
- Large-margin fine-tuning strategy
- Checkpoint saving and resuming

### Evaluation Metrics
- EER (Equal Error Rate) for speaker verification
- DER (Diarization Error Rate) for speaker diarization  
- minDCF (minimum Detection Cost Function)
- Cosine similarity scoring

## Key Implementation Details

### Data Preparation
- Audio files organized as Kaldi-style scp files (wav.scp, utt2spk)
- CSV format for training data with columns: utt_id, wav_path, speaker_id, duration
- Support for data filtering by duration and speaker count

### Augmentation Pipeline
- Speed perturbation (0.9, 1.0, 1.1)
- Addition of noise (MUSAN dataset)
- Addition of reverberation (RIRs dataset)
- SpecAugment for spectral masking

### Model Export
- PyTorch to ONNX conversion with dynamic batch size
- Optimized C++ runtime for CPU inference
- Support for streaming and batch processing

### Distributed Training
- Uses torchrun for multi-GPU training
- Gradient accumulation for large batch sizes
- Mixed precision training support