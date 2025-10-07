# 声纹识别API监控系统

## 概述

为了诊断API连接失败问题，已在 `/home/pi/workspace/speaker/server.py` 中添加了完整的日志和监控系统。

## 新增功能

### 1. 详细日志记录

**日志文件位置**: `logs/speaker_api_YYYYMMDD.log`

- 每天自动创建新的日志文件
- 记录所有请求的详细信息（时间戳、文件名、行号、详细错误）
- 控制台同时输出简化日志

**日志示例**:
```
2025-10-07 10:15:23 - INFO - ✅ /verify - 2.134s - IP: 192.168.1.100
2025-10-07 10:15:25 - INFO - ❌ /verify - 0.045s - IP: 192.168.1.100 - Error: Audio1: Audio too short: 0.3s (min: 0.5s)
```

### 2. 请求监控统计

**`RequestMonitor` 类** 自动跟踪以下指标：

- **总请求数** (`total_requests`)
- **成功次数** (`success_count`)
- **失败次数** (`error_count`)
- **成功率** (`success_rate`)
- **平均响应时间** (`avg_response_time`)
- **最近100条请求历史** (包含时间戳、endpoint、成功状态、响应时间、错误信息、客户端IP)

**自动统计打印**: 每10个请求打印一次统计摘要
```
============================================================
📊 API统计 - 总请求: 20
   成功: 18 | 失败: 2 | 成功率: 90.0%
   平均响应时间: 1.856s
============================================================
```

### 3. 增强的 `/health` 端点

现在 `/health` 端点返回完整的统计信息：

```bash
curl http://tenyuan.tech:7001/health
```

**响应示例**:
```json
{
  "status": "healthy",
  "model_loaded": true,
  "model_id": "iic/speech_eres2net_sv_zh-cn_16k-common",
  "device": "cpu",
  "timestamp": 1728282123.456,
  "uptime": 3600.5,
  "statistics": {
    "total_requests": 20,
    "success_count": 18,
    "error_count": 2,
    "success_rate": "90.00%",
    "avg_response_time": "1.856s",
    "recent_requests": [
      {
        "timestamp": 1728282100.123,
        "endpoint": "/verify",
        "success": true,
        "duration": 2.134,
        "error": null,
        "client_ip": "192.168.1.100"
      },
      // ... 最近10条
    ]
  }
}
```

### 4. 监控的 `/verify` 端点

现在每个 `/verify` 请求都会：

1. **记录客户端IP** - 可以识别哪些客户端遇到问题
2. **记录请求时长** - 包含完整请求处理时间（不仅是推理时间）
3. **记录成功/失败状态** - 自动分类请求结果
4. **记录错误信息** - 失败时记录具体错误原因
5. **写入日志文件** - 所有信息持久化到日志文件

## 使用方法

### 查看实时日志

```bash
# SSH到服务器
ssh pi@tenyuan.tech

# 进入项目目录
cd /home/pi/workspace/speaker

# 实时查看日志
tail -f logs/speaker_api_$(date +%Y%m%d).log

# 或者查看最近100行
tail -n 100 logs/speaker_api_$(date +%Y%m%d).log
```

### 查看统计信息

```bash
# 通过健康检查端点
curl http://tenyuan.tech:7001/health | jq '.statistics'

# 或者使用 Python 客户端
python3 << EOF
import requests
response = requests.get('http://tenyuan.tech:7001/health')
stats = response.json()['statistics']
print(f"总请求: {stats['total_requests']}")
print(f"成功率: {stats['success_rate']}")
print(f"平均响应: {stats['avg_response_time']}")
EOF
```

### 分析失败请求

```bash
# 查找所有失败的请求
grep "❌" logs/speaker_api_$(date +%Y%m%d).log

# 查找特定IP的请求
grep "192.168.1.100" logs/speaker_api_$(date +%Y%m%d).log

# 统计错误类型
grep "Error:" logs/speaker_api_$(date +%Y%m%d).log | cut -d':' -f4- | sort | uniq -c
```

## 重启服务以应用更改

```bash
cd /home/pi/workspace/speaker

# 停止当前服务
./stop_production.sh

# 启动新服务（应用监控功能）
./start_production.sh

# 检查服务状态
curl http://tenyuan.tech:7001/health
```

## 诊断问题流程

### 1. 检查整体健康状态
```bash
curl http://tenyuan.tech:7001/health
```
- 查看 `status` 是否为 "healthy"
- 查看 `success_rate` 成功率
- 查看 `avg_response_time` 平均响应时间

### 2. 监控实时日志
```bash
tail -f logs/speaker_api_$(date +%Y%m%d).log
```
在客户端（xiaoyu-server）触发几次语音识别，观察：
- 是否收到请求？
- 请求的响应时间是多少？
- 是否有错误？错误信息是什么？

### 3. 分析失败模式
```bash
# 查看最近的失败
grep "❌" logs/speaker_api_$(date +%Y%m%d).log | tail -20

# 按客户端IP分组
grep "❌" logs/speaker_api_$(date +%Y%m%d).log | awk '{print $NF}' | sort | uniq -c
```

### 4. 检查客户端重试是否生效

在客户端日志中查找：
- `⚠️ API调用失败 (尝试 1/3)，0.5秒后重试...` - 表示重试机制工作
- `❌ API调用失败，已达到最大重试次数` - 表示连续3次都失败

如果服务器日志显示**收到**请求但客户端报告**连接失败**，说明问题在网络层（超时、丢包等）。

如果服务器日志**没有**请求记录而客户端报告**连接失败**，说明请求根本没到达服务器（网络中断、防火墙等）。

## 预期诊断结果

### 场景1: 服务器过载
- 日志显示大量请求
- 平均响应时间很长（>5秒）
- 成功率降低
- **解决**: 增加 worker 数量或升级服务器

### 场景2: 网络不稳定
- 日志显示部分时段没有请求
- 客户端报告连接失败但服务器没有日志
- **解决**: 检查网络路由、防火墙、代理设置

### 场景3: 客户端超时设置过短
- 日志显示请求成功但耗时较长
- 客户端报告超时
- **解决**: 增加客户端超时时间（voice_verify.py 的 timeout 参数）

### 场景4: 音频文件问题
- 日志显示 "Audio too short" 或 "Invalid audio file" 错误
- **解决**: 检查音频录制质量和时长

## 相关文件

- **服务器代码**: `/home/pi/workspace/speaker/server.py`
- **日志目录**: `/home/pi/workspace/speaker/logs/`
- **启动脚本**: `/home/pi/workspace/speaker/start_production.sh`
- **停止脚本**: `/home/pi/workspace/speaker/stop_production.sh`
- **客户端代码**: `/home/pi/workspace/xiaoyu-server/voice_verify.py`

## 监控代码位置

### RequestMonitor 类定义
`server.py` 行 56-126

### /verify 端点监控
`server.py` 行 270-380

### /health 端点统计
`server.py` 行 248-268

## 下一步优化建议

1. **添加 Prometheus metrics** - 用于长期监控和可视化
2. **邮件/钉钉告警** - 成功率低于90%时自动告警
3. **请求日志数据库** - 将请求历史存入数据库便于查询分析
4. **慢请求分析** - 单独记录响应时间>3秒的请求
5. **IP黑名单** - 自动屏蔽异常IP
