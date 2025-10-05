# 🎙️ Speaker Verification API 接口文档

## 目录
- [快速开始](#快速开始)
- [API基础信息](#api基础信息)
- [接口列表](#接口列表)
- [详细接口说明](#详细接口说明)
- [错误码](#错误码)
- [测试工具](#测试工具)
- [FAQ](#faq)

## 快速开始

### 1. 启动服务
```bash
# 使用启动脚本
./start_api_simple.sh

# 或直接运行（默认端口5001）
python api_server_simple.py --port 5001
```

### 2. 测试服务是否正常
```bash
curl http://localhost:5001/health
```

### 3. 验证两个音频
```bash
curl -X POST http://localhost:5001/verify \
  -F "audio1=@speaker1.wav" \
  -F "audio2=@speaker2.wav"
```

## API基础信息

| 属性 | 说明 |
|------|------|
| **基础URL** | `http://localhost:5001` |
| **协议** | HTTP/HTTPS |
| **数据格式** | JSON / Multipart Form |
| **字符编码** | UTF-8 |
| **响应格式** | JSON |

## 接口列表

| 接口 | 方法 | 说明 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/verify` | POST | 验证两个音频是否为同一说话人 |
| `/verify_batch` | POST | 批量验证多个音频 |
| `/extract_embedding` | POST | 提取音频特征向量 |
| `/compare_embeddings` | POST | 比较两个特征向量 |
| `/config` | GET/POST | 获取或更新配置 |

## 详细接口说明

### 1. 健康检查 `/health`

**请求方式：** GET

**请求示例：**
```bash
curl http://localhost:5001/health
```

**响应示例：**
```json
{
    "status": "healthy",
    "model_loaded": true,
    "device": "cpu",
    "model_path": "pretrained/speech_campplus_sv_zh-cn_16k-common/campplus_cn_common.pt"
}
```

---

### 2. 说话人验证 `/verify`

**请求方式：** POST

**功能说明：** 验证两个音频是否来自同一说话人

**支持的音频格式：**
- WAV, MP3, FLAC, M4A, OGG, WMA, AAC

**请求参数：**

#### 方式1：文件上传（推荐）

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| audio1 | file | 是 | 第一个音频文件 |
| audio2 | file | 是 | 第二个音频文件 |

**请求示例：**
```python
import requests

url = "http://localhost:5001/verify"
files = {
    'audio1': open('speaker1.wav', 'rb'),
    'audio2': open('speaker2.wav', 'rb')
}
response = requests.post(url, files=files)
print(response.json())
```

```bash
# curl示例
curl -X POST http://localhost:5001/verify \
  -F "audio1=@/path/to/audio1.wav" \
  -F "audio2=@/path/to/audio2.wav"
```

#### 方式2：URL传递

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| audio1_url | string | 是 | 第一个音频的URL |
| audio2_url | string | 是 | 第二个音频的URL |

**请求示例：**
```python
import requests

url = "http://localhost:5001/verify"
data = {
    "audio1_url": "http://example.com/audio1.wav",
    "audio2_url": "http://example.com/audio2.wav"
}
response = requests.post(url, json=data)
print(response.json())
```

#### 方式3：本地路径

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| audio1_path | string | 是 | 第一个音频的本地路径 |
| audio2_path | string | 是 | 第二个音频的本地路径 |

**请求示例：**
```python
import requests

url = "http://localhost:5001/verify"
data = {
    "audio1_path": "/Users/xxx/Desktop/audio1.wav",
    "audio2_path": "/Users/xxx/Desktop/audio2.wav"
}
response = requests.post(url, json=data)
print(response.json())
```

**响应参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| success | boolean | 请求是否成功 |
| score | float | 相似度分数 (0-1) |
| is_same_speaker | boolean | 是否为同一说话人 |
| threshold | float | 判断阈值 |
| confidence | string | 置信度 (high/medium/low) |
| error | string | 错误信息（仅在失败时） |

**响应示例：**
```json
{
    "success": true,
    "score": 0.8756,
    "is_same_speaker": true,
    "threshold": 0.5,
    "confidence": "high"
}
```

---

### 3. 批量验证 `/verify_batch`

**请求方式：** POST

**功能说明：** 将一个参考音频与多个候选音频进行比对

**请求参数：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| reference | string | 是 | 参考音频（URL或路径） |
| candidates | array | 是 | 候选音频数组 |

**请求示例：**
```python
import requests

url = "http://localhost:5001/verify_batch"
data = {
    "reference": "/path/to/reference.wav",
    "candidates": [
        "/path/to/candidate1.wav",
        "/path/to/candidate2.wav",
        "http://example.com/candidate3.wav"
    ]
}
response = requests.post(url, json=data)
print(response.json())
```

**响应示例：**
```json
{
    "success": true,
    "reference": "/path/to/reference.wav",
    "results": [
        {
            "candidate": "/path/to/candidate1.wav",
            "result": {
                "success": true,
                "score": 0.923,
                "is_same_speaker": true,
                "threshold": 0.5,
                "confidence": "high"
            }
        },
        {
            "candidate": "/path/to/candidate2.wav",
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

---

### 4. 提取特征向量 `/extract_embedding`

**请求方式：** POST

**功能说明：** 提取音频的说话人特征向量（192维）

**请求参数：**

#### 方式1：文件上传

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| audio | file | 是 | 音频文件 |

#### 方式2：URL/路径

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| audio_url | string | 否 | 音频URL |
| audio_path | string | 否 | 音频本地路径 |

**请求示例：**
```python
# 文件上传
files = {'audio': open('speaker.wav', 'rb')}
response = requests.post("http://localhost:5001/extract_embedding", files=files)

# URL方式
data = {"audio_url": "http://example.com/audio.wav"}
response = requests.post("http://localhost:5001/extract_embedding", json=data)
```

**响应示例：**
```json
{
    "success": true,
    "embedding": [0.123, -0.456, 0.789, ...],  // 192个浮点数
    "dimension": 192
}
```

---

### 5. 比较特征向量 `/compare_embeddings`

**请求方式：** POST

**功能说明：** 直接比较两个已提取的特征向量

**请求参数：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| embedding1 | array | 是 | 第一个特征向量 |
| embedding2 | array | 是 | 第二个特征向量 |

**请求示例：**
```python
data = {
    "embedding1": [0.123, -0.456, ...],  # 192维
    "embedding2": [0.234, -0.567, ...]   # 192维
}
response = requests.post("http://localhost:5001/compare_embeddings", json=data)
```

**响应示例：**
```json
{
    "success": true,
    "similarity": 0.854,
    "is_same_speaker": true,
    "threshold": 0.5
}
```

---

### 6. 配置管理 `/config`

**GET - 获取配置**
```bash
curl http://localhost:5001/config
```

响应：
```json
{
    "device": "cpu",
    "threshold": 0.5,
    "max_file_size": 52428800,
    "allowed_extensions": ["wav", "mp3", "flac", "m4a", "ogg", "wma", "aac"],
    "model_path": "pretrained/model.pt"
}
```

**POST - 更新配置**
```python
data = {
    "threshold": 0.6,  # 更新判断阈值
    "model_path": "/path/to/new/model.pt"  # 更换模型
}
response = requests.post("http://localhost:5001/config", json=data)
```

## 错误码

| 状态码 | 说明 |
|--------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 500 | 服务器内部错误 |

**错误响应格式：**
```json
{
    "success": false,
    "error": "错误描述信息"
}
```

## 测试工具

### 使用网页测试（见 test.html）
1. 打开 `test.html` 文件
2. 选择两个音频文件
3. 点击"验证说话人"按钮

### 使用Python脚本测试
```python
# 见 test_client.py 文件
python test_client.py
```

### 使用cURL测试
```bash
# 健康检查
curl http://localhost:5001/health

# 验证说话人
curl -X POST http://localhost:5001/verify \
  -F "audio1=@test1.wav" \
  -F "audio2=@test2.wav"
```

## FAQ

### Q1: 支持什么音频格式？
A: 支持 WAV, MP3, FLAC, M4A, OGG, WMA, AAC 格式。

### Q2: 音频有什么要求？
A: 建议使用16kHz采样率，单声道，时长3秒以上的音频。系统会自动转换格式。

### Q3: 相似度分数多少算同一人？
A: 默认阈值是0.5，超过0.5判定为同一人。可通过 `/config` 接口调整阈值。

### Q4: 特征向量是多少维？
A: 默认模型输出192维特征向量。

### Q5: 如何提高准确率？
A:
- 使用高质量音频（清晰、无噪音）
- 音频时长在3-10秒之间
- 说话内容包含足够的语音特征
- 根据实际场景调整阈值

### Q6: 服务支持并发吗？
A: 是的，服务支持多线程并发处理请求。

## 性能指标

| 指标 | 数值 |
|------|------|
| 单次验证延迟 | < 500ms (CPU) |
| 并发处理能力 | 10-20 QPS |
| 内存占用 | ~2GB |
| 模型大小 | ~400MB |

## 更新日志

- v1.0.0 (2024-01) - 初始版本发布
  - 支持说话人验证
  - 支持批量验证
  - 支持特征提取

## 联系方式

如有问题，请提交Issue到项目仓库。