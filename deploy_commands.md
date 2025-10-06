# 🚀 部署命令指南

## 在阿里云服务器上执行以下命令：

### 1. 停止当前开发服务器
```bash
cd /root/speaker  # 或你的项目目录
pkill -f "python server.py"
lsof -ti:7001 | xargs -r kill -9
```

### 2. 安装生产环境依赖
```bash
conda activate 3D-Speaker
pip install gunicorn==21.2.0 waitress==2.1.2
```

### 3. 创建日志目录
```bash
mkdir -p logs
```

### 4. 设置脚本权限
```bash
chmod +x start_production.sh stop_server.sh
```

### 5. 启动生产服务器
```bash
./start_production.sh
```

### 6. 检查服务状态
```bash
# 检查进程
ps aux | grep gunicorn

# 检查端口
netstat -tlnp | grep 7001

# 测试API
curl http://localhost:7001/health
```

### 7. 查看日志
```bash
tail -f logs/error.log
tail -f logs/access.log
```

### 8. （可选）设置系统服务
创建 `/etc/systemd/system/speaker-server.service`:
```ini
[Unit]
Description=3D-Speaker Inference Server
After=network.target

[Service]
Type=forking
User=root
WorkingDirectory=/root/speaker
Environment="PATH=/root/miniconda3/envs/3D-Speaker/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=/root/speaker/start_production.sh
ExecStop=/root/speaker/stop_server.sh
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

然后执行：
```bash
systemctl daemon-reload
systemctl enable speaker-server
systemctl start speaker-server
systemctl status speaker-server
```

## 🔧 故障排查

### 如果服务无法启动：
1. 检查端口占用：`lsof -i:7001`
2. 检查Python环境：`which python`
3. 检查依赖安装：`pip list | grep gunicorn`
4. 查看错误日志：`tail -100 logs/error.log`

### 如果无法访问API：
1. 检查防火墙：`firewall-cmd --list-ports`
2. 检查阿里云安全组规则（确保7001端口开放）
3. 测试本地连接：`curl http://127.0.0.1:7001/health`