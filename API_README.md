# Speaker Verification API 说话人验证接口文档

## 快速开始

### 1. 安装依赖
```bash
pip install -r requirements_api.txt
```

### 2. 启动服务
```bash
# 方式1：使用启动脚本
./start_api.sh

# 方式2：直接运行
python api_server.py
```

服务将在 `http://localhost:5000` 启动

## API 接口说明

### 1. 健康检查
**GET** `/health`

检查服务状态和模型加载情况

响应示例：
```json
{
    "status": "healthy",
    "model": "iic/speech_campplus_sv_zh-cn_16k-common",
    "device": "cuda",
    "model_loaded": true
}
```

### 2. 说话人验证
**POST** `/verify`

验证两个音频是否为同一说话人

#### 支持三种方式：

**方式1: 文件上传**
```bash
curl -X POST http://localhost:5000/verify \
  -F "audio1=@speaker1.wav" \
  -F "audio2=@speaker2.wav"
```

**方式2: URL**
```bash
curl -X POST http://localhost:5000/verify \
  -H "Content-Type: application/json" \
  -d '{
    "audio1_url": "http://example.com/audio1.wav",
    "audio2_url": "http://example.com/audio2.wav"
  }'
```

**方式3: 本地路径**
```bash
curl -X POST http://localhost:5000/verify \
  -H "Content-Type: application/json" \
  -d '{
    "audio1_path": "/path/to/audio1.wav",
    "audio2_path": "/path/to/audio2.wav"
  }'
```

响应示例：
```json
{
    "success": true,
    "score": 0.8523,
    "is_same_speaker": true,
    "threshold": 0.5,
    "confidence": "high"
}
```

### 3. 批量验证
**POST** `/verify_batch`

将一个参考音频与多个候选音频进行比对

请求示例：
```json
{
    "reference": "http://example.com/reference.wav",
    "candidates": [
        "http://example.com/candidate1.wav",
        "http://example.com/candidate2.wav",
        "/path/to/local/audio.wav"
    ]
}
```

响应示例：
```json
{
    "success": true,
    "reference": "http://example.com/reference.wav",
    "results": [
        {
            "candidate": "http://example.com/candidate1.wav",
            "result": {
                "success": true,
                "score": 0.923,
                "is_same_speaker": true,
                "threshold": 0.5,
                "confidence": "high"
            }
        },
        {
            "candidate": "http://example.com/candidate2.wav",
            "result": {
                "success": true,
                "score": 0.234,
                "is_same_speaker": false,
                "threshold": 0.5,
                "confidence": "high"
            }
        }
    ]
}
```

### 4. 提取特征向量
**POST** `/extract_embedding`

提取音频的说话人特征向量（192维）

请求示例：
```bash
# 文件上传
curl -X POST http://localhost:5000/extract_embedding \
  -F "audio=@speaker.wav"

# URL方式
curl -X POST http://localhost:5000/extract_embedding \
  -H "Content-Type: application/json" \
  -d '{"audio_url": "http://example.com/audio.wav"}'
```

响应示例：
```json
{
    "success": true,
    "embedding": [0.123, -0.456, ...],  // 192维向量
    "dimension": 192
}
```

### 5. 比较特征向量
**POST** `/compare_embeddings`

直接比较两个已提取的特征向量

请求示例：
```json
{
    "embedding1": [0.123, -0.456, ...],
    "embedding2": [0.234, -0.567, ...]
}
```

响应示例：
```json
{
    "success": true,
    "similarity": 0.854,
    "is_same_speaker": true,
    "threshold": 0.5
}
```

### 6. 配置管理
**GET** `/config` - 获取当前配置
**POST** `/config` - 更新配置

获取配置响应：
```json
{
    "model_id": "iic/speech_campplus_sv_zh-cn_16k-common",
    "device": "cuda",
    "threshold": 0.5,
    "max_file_size": 52428800,
    "allowed_extensions": ["wav", "mp3", "flac", "m4a", "ogg", "wma", "aac"]
}
```

更新配置请求：
```json
{
    "threshold": 0.6,
    "model_id": "iic/speech_eres2net_sv_zh-cn_16k-common"
}
```

## Python 客户端示例

```python
import requests
import json

# 服务地址
BASE_URL = "http://localhost:5000"

# 1. 健康检查
response = requests.get(f"{BASE_URL}/health")
print(response.json())

# 2. 验证两个音频文件
with open("audio1.wav", "rb") as f1, open("audio2.wav", "rb") as f2:
    files = {
        "audio1": f1,
        "audio2": f2
    }
    response = requests.post(f"{BASE_URL}/verify", files=files)
    result = response.json()

    if result["is_same_speaker"]:
        print(f"同一说话人 (相似度: {result['score']:.3f})")
    else:
        print(f"不同说话人 (相似度: {result['score']:.3f})")

# 3. 批量验证
data = {
    "reference": "/path/to/reference.wav",
    "candidates": [
        "/path/to/candidate1.wav",
        "/path/to/candidate2.wav"
    ]
}
response = requests.post(f"{BASE_URL}/verify_batch", json=data)
results = response.json()

for item in results["results"]:
    candidate = item["candidate"]
    is_same = item["result"]["is_same_speaker"]
    score = item["result"]["score"]
    print(f"{candidate}: {'同一人' if is_same else '不同人'} ({score:.3f})")

# 4. 提取特征向量
with open("speaker.wav", "rb") as f:
    files = {"audio": f}
    response = requests.post(f"{BASE_URL}/extract_embedding", files=files)
    embedding = response.json()["embedding"]
    print(f"特征向量维度: {len(embedding)}")

# 5. 比较特征向量
data = {
    "embedding1": embedding1,
    "embedding2": embedding2
}
response = requests.post(f"{BASE_URL}/compare_embeddings", json=data)
similarity = response.json()["similarity"]
print(f"相似度: {similarity:.3f}")
```

## 配置说明

### 环境变量
- `FLASK_ENV`: 运行环境 (development/production)
- `FLASK_PORT`: 服务端口 (默认5000)

### 模型选择
API支持多个预训练模型：
- `iic/speech_campplus_sv_zh-cn_16k-common` (中文，推荐)
- `iic/speech_eres2net_sv_zh-cn_16k-common` (中文)
- `iic/speech_eres2net_sv_en_voxceleb_16k` (英文)

### 性能优化
- 服务启动时自动预加载模型
- 支持CUDA、MPS（Apple Silicon）和CPU
- 支持并发请求处理
- 自动清理临时文件

### 支持的音频格式
- WAV
- MP3
- FLAC
- M4A
- OGG
- WMA
- AAC

### 错误处理
所有接口在出错时会返回：
```json
{
    "success": false,
    "error": "错误描述"
}
```

## 部署建议

### 生产环境部署
```bash
# 使用gunicorn部署
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 api_server:app

# 或使用uWSGI
pip install uwsgi
uwsgi --http 0.0.0.0:5000 --module api_server:app --processes 4
```

### Docker部署
```dockerfile
FROM python:3.8

WORKDIR /app
COPY requirements_api.txt .
RUN pip install -r requirements_api.txt

COPY . .
EXPOSE 5000

CMD ["python", "api_server.py"]
```

### 注意事项
1. 首次启动会下载模型文件（约400MB）
2. 建议使用GPU加速，CPU推理速度较慢
3. 相似度阈值默认为0.5，可根据实际场景调整
4. 音频文件建议采样率16kHz，单声道