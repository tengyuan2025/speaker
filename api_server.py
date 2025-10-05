#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import time
import tempfile
import hashlib
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory, render_template_string
from flask_cors import CORS
import numpy as np
import torch
import torchaudio

# 修复 ModelScope 兼容性问题后导入
from modelscope.pipelines import pipeline
from modelscope.utils.constant import Tasks
import logging
from concurrent.futures import ThreadPoolExecutor
import requests
from werkzeug.utils import secure_filename

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 配置
class Config:
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 最大文件50MB
    ALLOWED_EXTENSIONS = {'wav', 'mp3', 'flac', 'm4a', 'ogg', 'wma', 'aac'}
    MODEL_ID = 'iic/speech_campplus_sv_zh-cn_16k-common'  # 默认模型
    DEVICE = 'cuda' if torch.cuda.is_available() else 'mps' if torch.backends.mps.is_available() else 'cpu'
    THRESHOLD = 0.5  # 相似度阈值
    CACHE_DIR = Path(tempfile.gettempdir()) / 'speaker_verification_cache'

app.config.from_object(Config)
app.config['CACHE_DIR'].mkdir(exist_ok=True)

# 全局变量存储模型
sv_pipeline = None
executor = ThreadPoolExecutor(max_workers=4)

def init_model(model_id=None):
    """初始化说话人验证模型"""
    global sv_pipeline
    if sv_pipeline is None:
        model_id = model_id or app.config['MODEL_ID']
        logger.info(f"Loading model: {model_id} on device: {app.config['DEVICE']}")

        try:
            if app.config['DEVICE'] == 'mps':
                # MPS 设备处理
                sv_pipeline = pipeline(
                    task=Tasks.speaker_verification,
                    model=model_id,
                    device='cpu'  # 先在CPU加载
                )
                # 然后转移到MPS
                if hasattr(sv_pipeline, 'model'):
                    sv_pipeline.model = sv_pipeline.model.to('mps')
            else:
                sv_pipeline = pipeline(
                    task=Tasks.speaker_verification,
                    model=model_id,
                    device=app.config['DEVICE']
                )
            logger.info("Model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise

def allowed_file(filename):
    """检查文件类型是否允许"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def download_audio(url, save_path):
    """从URL下载音频文件"""
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
    """处理音频来源，返回本地文件路径"""
    temp_file = None

    # 如果是文件上传
    if hasattr(audio_source, 'read'):
        if not allowed_file(audio_source.filename):
            raise ValueError(f"File type not allowed: {audio_source.filename}")

        # 保存上传的文件
        filename = secure_filename(audio_source.filename)
        temp_file = app.config['CACHE_DIR'] / f"{time.time()}_{filename}"
        audio_source.save(str(temp_file))
        return str(temp_file), True

    # 如果是URL
    elif isinstance(audio_source, str) and audio_source.startswith(('http://', 'https://')):
        # 从URL下载
        url_hash = hashlib.md5(audio_source.encode()).hexdigest()
        temp_file = app.config['CACHE_DIR'] / f"{url_hash}.audio"

        if not temp_file.exists():
            if not download_audio(audio_source, temp_file):
                raise ValueError(f"Failed to download audio from URL: {audio_source}")

        return str(temp_file), True

    # 如果是本地路径
    elif isinstance(audio_source, str):
        if not Path(audio_source).exists():
            raise ValueError(f"File not found: {audio_source}")
        return audio_source, False

    else:
        raise ValueError("Invalid audio source type")

def verify_speakers(audio1_path, audio2_path):
    """验证两个音频是否为同一说话人"""
    try:
        result = sv_pipeline((audio1_path, audio2_path))
        score = result['score']
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

def extract_embedding(audio_path):
    """提取音频的说话人特征向量"""
    try:
        # 使用pipeline提取特征
        result = sv_pipeline.model(audio_path)
        embedding = result['embs'][0].detach().cpu().numpy()

        return embedding
    except Exception as e:
        logger.error(f"Failed to extract embedding: {e}")
        return None

@app.route('/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({
        'status': 'healthy',
        'model': app.config['MODEL_ID'],
        'device': app.config['DEVICE'],
        'model_loaded': sv_pipeline is not None
    })

@app.route('/verify', methods=['POST'])
def verify():
    """
    说话人验证接口
    支持三种方式：
    1. 文件上传: 使用 multipart/form-data，audio1 和 audio2 字段
    2. URL: JSON body，包含 audio1_url 和 audio2_url
    3. 本地路径: JSON body，包含 audio1_path 和 audio2_path
    """
    temp_files = []

    try:
        # 初始化模型
        if sv_pipeline is None:
            init_model()

        # 获取音频源
        audio1_source = None
        audio2_source = None

        # 检查文件上传
        if 'audio1' in request.files and 'audio2' in request.files:
            audio1_source = request.files['audio1']
            audio2_source = request.files['audio2']

        # 检查JSON请求
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

        # 处理音频文件
        audio1_path, is_temp1 = get_audio_path(audio1_source)
        audio2_path, is_temp2 = get_audio_path(audio2_source)

        if is_temp1:
            temp_files.append(audio1_path)
        if is_temp2:
            temp_files.append(audio2_path)

        # 执行验证
        result = verify_speakers(audio1_path, audio2_path)

        return jsonify(result)

    except Exception as e:
        logger.error(f"Request failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

    finally:
        # 清理临时文件
        for temp_file in temp_files:
            try:
                Path(temp_file).unlink()
            except:
                pass

@app.route('/verify_batch', methods=['POST'])
def verify_batch():
    """
    批量说话人验证接口
    输入: 一个参考音频和多个待验证音频
    """
    temp_files = []

    try:
        if sv_pipeline is None:
            init_model()

        data = request.json
        if not data or 'reference' not in data or 'candidates' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing reference or candidates'
            }), 400

        # 处理参考音频
        ref_path, is_temp = get_audio_path(data['reference'])
        if is_temp:
            temp_files.append(ref_path)

        # 批量验证
        results = []
        for candidate in data['candidates']:
            try:
                cand_path, is_temp = get_audio_path(candidate)
                if is_temp:
                    temp_files.append(cand_path)

                result = verify_speakers(ref_path, cand_path)
                results.append({
                    'candidate': candidate,
                    'result': result
                })
            except Exception as e:
                results.append({
                    'candidate': candidate,
                    'result': {'success': False, 'error': str(e)}
                })

        return jsonify({
            'success': True,
            'reference': data['reference'],
            'results': results
        })

    except Exception as e:
        logger.error(f"Batch verification failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

    finally:
        for temp_file in temp_files:
            try:
                Path(temp_file).unlink()
            except:
                pass

@app.route('/extract_embedding', methods=['POST'])
def extract():
    """
    提取说话人特征向量接口
    返回192维的特征向量
    """
    temp_file = None

    try:
        if sv_pipeline is None:
            init_model()

        # 获取音频源
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

        # 处理音频文件
        audio_path, is_temp = get_audio_path(audio_source)
        if is_temp:
            temp_file = audio_path

        # 提取特征
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
    比较两个特征向量的相似度
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

        # 计算余弦相似度
        similarity = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))

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
    获取或更新配置
    """
    if request.method == 'GET':
        return jsonify({
            'model_id': app.config['MODEL_ID'],
            'device': app.config['DEVICE'],
            'threshold': app.config['THRESHOLD'],
            'max_file_size': app.config['MAX_CONTENT_LENGTH'],
            'allowed_extensions': list(app.config['ALLOWED_EXTENSIONS'])
        })

    else:  # POST
        data = request.json
        if 'threshold' in data:
            app.config['THRESHOLD'] = float(data['threshold'])

        if 'model_id' in data and data['model_id'] != app.config['MODEL_ID']:
            app.config['MODEL_ID'] = data['model_id']
            # 重新加载模型
            global sv_pipeline
            sv_pipeline = None
            init_model()

        return jsonify({'success': True, 'config': {
            'model_id': app.config['MODEL_ID'],
            'threshold': app.config['THRESHOLD']
        }})

@app.route('/')
def index():
    """提供测试页面"""
    try:
        with open('test.html', 'r', encoding='utf-8') as f:
            html_content = f.read()
        # 将API地址设置为当前服务器地址（使用JavaScript动态获取，避免CORS问题）
        html_content = html_content.replace(
            "let currentApiUrl = 'http://localhost:5002';",
            "let currentApiUrl = window.location.origin;"
        )
        # 修复输入框中的默认值
        html_content = html_content.replace(
            'value="http://localhost:5002"',
            'value=""'
        )
        # 在页面加载时设置正确的API地址
        html_content = html_content.replace(
            "document.addEventListener('DOMContentLoaded', function() {",
            """document.addEventListener('DOMContentLoaded', function() {
            // 设置API地址输入框的值
            document.getElementById('apiUrl').value = window.location.origin;"""
        )
        return html_content
    except FileNotFoundError:
        return '''
        <h1>Speaker Verification API</h1>
        <p>API服务正在运行</p>
        <p>测试页面未找到，请确保 test.html 文件存在</p>
        <h2>API接口:</h2>
        <ul>
            <li><a href="/health">/health</a> - 健康检查</li>
            <li>POST /verify - 说话人验证</li>
            <li>POST /extract_embedding - 特征提取</li>
        </ul>
        '''

@app.route('/test.html')
def test_page():
    """提供测试页面的别名"""
    return index()

if __name__ == '__main__':
    # 启动时预加载模型
    logger.info("Starting Speaker Verification API Server...")
    init_model()

    # 启动服务器
    app.run(
        host='0.0.0.0',
        port=5002,
        debug=False,
        threaded=True
    )