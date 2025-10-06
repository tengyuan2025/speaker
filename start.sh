#!/bin/bash
# 3D-Speaker 服务启动脚本

set -e

# 从 .env 文件加载配置（如果存在）
if [[ -f ".env" ]]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# 默认配置
HOST=${HOST:-"0.0.0.0"}
PORT=${PORT:-"7001"}
DEVICE=${DEVICE:-"cpu"}
MODEL_ID=${SPEAKER_MODEL_ID:-"iic/speech_eres2net_sv_zh-cn_16k-common"}
WORKERS=${WORKERS:-"1"}
DEBUG=${DEBUG:-"false"}

# 创建必要目录
mkdir -p uploads
mkdir -p models
mkdir -p logs

echo "========================================"
echo "🎙️  3D-Speaker 推理服务启动"
echo "========================================"
echo "主机: $HOST"
echo "端口: $PORT"
echo "设备: $DEVICE"
echo "模型: $MODEL_ID"
echo "工作进程: $WORKERS"
echo "========================================"

# 检查conda环境
if [[ "$CONDA_DEFAULT_ENV" != "3D-Speaker" ]] && [[ -n "$CONDA_DEFAULT_ENV" ]]; then
    echo "⚠️  当前conda环境: $CONDA_DEFAULT_ENV (建议使用: 3D-Speaker)"
elif [[ -z "$CONDA_DEFAULT_ENV" ]]; then
    echo "⚠️  未检测到conda环境"
fi

# 环境检查
echo ""
echo "🔍 环境检查..."

# 检查Python和依赖
python -c "
import sys
print(f'Python: {sys.version.split()[0]}')

# 检查关键依赖
deps = [
    ('torch', 'PyTorch'),
    ('modelscope', 'ModelScope'),
    ('flask', 'Flask'),
    ('soundfile', 'SoundFile'),
    ('numpy', 'NumPy')
]

missing = []
for module, name in deps:
    try:
        __import__(module)
        print(f'✅ {name}')
    except ImportError:
        print(f'❌ {name} - 未安装')
        missing.append(name)

if missing:
    print(f'\\n缺失依赖: {missing}')
    print('请运行: bash setup.sh')
    sys.exit(1)
else:
    print('\\n✅ 所有依赖检查通过')
" || {
    echo ""
    echo "❌ 依赖检查失败！"
    echo "请运行安装脚本: bash setup.sh"
    exit 1
}

# 检查服务器文件
if [[ ! -f "server.py" ]]; then
    echo "❌ server.py 文件不存在！"
    echo "请确保在正确的目录运行脚本"
    exit 1
fi

# 检查端口占用
if command -v netstat &> /dev/null; then
    if netstat -tuln | grep ":$PORT " > /dev/null; then
        echo "⚠️  端口 $PORT 已被占用"
        echo "正在尝试找到占用进程..."
        if command -v lsof &> /dev/null; then
            lsof -ti:$PORT | head -1 | xargs -r ps -p
        fi

        read -p "是否要终止占用进程？(y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            if command -v lsof &> /dev/null; then
                lsof -ti:$PORT | xargs -r kill -9
                echo "进程已终止"
            else
                echo "无法自动终止，请手动处理"
                exit 1
            fi
        else
            echo "请更改端口或手动终止占用进程"
            exit 1
        fi
    fi
fi

# 测试模型导入（快速检查）
echo ""
echo "🔄 初始化模型检查..."
python -c "
from modelscope.pipelines import pipeline
from modelscope.utils.constant import Tasks
print('✅ ModelScope 可以正常导入')
print('模型将在首次请求时自动下载')
" || {
    echo "❌ ModelScope 导入失败"
    echo "请检查网络连接或重新运行: bash setup.sh"
    exit 1
}

# 更新 test_api.py 的默认URL
if [[ -f "test_api.py" ]]; then
    sed -i.bak "s|http://localhost:8000|http://localhost:$PORT|g" test_api.py 2>/dev/null || true
fi

# 根据参数选择启动模式
case "${1:-development}" in
    "production"|"prod")
        echo ""
        echo "🚀 启动生产服务器 (Gunicorn)..."

        # 检查gunicorn是否安装
        if ! command -v gunicorn &> /dev/null; then
            echo "安装 Gunicorn..."
            pip install gunicorn
        fi

        # 设置生产环境变量
        export DEBUG=false

        echo "配置: $WORKERS 个工作进程，绑定 $HOST:$PORT"

        exec gunicorn \
            --bind $HOST:$PORT \
            --workers $WORKERS \
            --worker-class sync \
            --timeout ${TIMEOUT:-120} \
            --keepalive 5 \
            --max-requests 1000 \
            --max-requests-jitter 100 \
            --access-logfile ${ACCESS_LOG:-logs/access.log} \
            --error-logfile ${ERROR_LOG:-logs/error.log} \
            --log-level ${LOG_LEVEL:-info} \
            --preload \
            --pid logs/gunicorn.pid \
            server:app
        ;;

    "development"|"dev"|"")
        echo ""
        echo "🛠️  启动开发服务器 (Flask)..."

        # 设置开发环境变量
        export DEBUG=true
        export FLASK_ENV=development

        # 设置环境变量供server.py使用
        export HOST=$HOST
        export PORT=$PORT
        export DEVICE=$DEVICE
        export SPEAKER_MODEL_ID=$MODEL_ID

        echo "配置: 开发模式，调试已启用"

        # 直接运行Python服务器
        exec python server.py
        ;;

    "systemd"|"service")
        echo ""
        echo "🔧 安装为系统服务..."

        if [[ ! -f "speaker-server.service" ]]; then
            echo "❌ 服务文件不存在，请先运行: bash setup.sh"
            exit 1
        fi

        # 复制服务文件
        sudo cp speaker-server.service /etc/systemd/system/

        # 重新加载systemd
        sudo systemctl daemon-reload

        # 启用服务
        sudo systemctl enable speaker-server

        # 启动服务
        sudo systemctl start speaker-server

        echo "✅ 服务已安装并启动"
        echo "查看状态: sudo systemctl status speaker-server"
        echo "查看日志: sudo journalctl -u speaker-server -f"
        echo "停止服务: sudo systemctl stop speaker-server"
        ;;

    "test")
        echo ""
        echo "🧪 运行API测试..."

        # 启动服务器（后台）
        export DEBUG=false
        python server.py &
        SERVER_PID=$!

        # 等待服务器启动
        echo "等待服务器启动..."
        sleep 5

        # 运行测试
        if [[ -f "test_api.py" ]]; then
            python test_api.py --url "http://localhost:$PORT"
        else
            echo "使用curl测试基本功能..."
            curl -s "http://localhost:$PORT/health" | head -5
        fi

        # 停止服务器
        echo ""
        echo "停止测试服务器..."
        kill $SERVER_PID 2>/dev/null || true
        ;;

    "stop")
        echo ""
        echo "🛑 停止服务..."

        # 停止可能在运行的进程
        if [[ -f "logs/gunicorn.pid" ]]; then
            PID=$(cat logs/gunicorn.pid)
            if kill -0 $PID 2>/dev/null; then
                echo "停止 Gunicorn 进程 (PID: $PID)"
                kill $PID
                sleep 2
                kill -9 $PID 2>/dev/null || true
            fi
            rm -f logs/gunicorn.pid
        fi

        # 查找并停止在指定端口运行的进程
        if command -v lsof &> /dev/null; then
            PIDS=$(lsof -ti:$PORT)
            if [[ -n "$PIDS" ]]; then
                echo "停止端口 $PORT 上的进程: $PIDS"
                echo $PIDS | xargs kill
                sleep 2
                echo $PIDS | xargs kill -9 2>/dev/null || true
            fi
        fi

        echo "✅ 服务已停止"
        ;;

    "restart")
        echo ""
        echo "🔄 重启服务..."

        # 停止服务
        $0 stop
        sleep 2

        # 启动服务
        $0 production
        ;;

    "status")
        echo ""
        echo "📊 服务状态检查..."

        # 检查端口
        if command -v netstat &> /dev/null; then
            if netstat -tuln | grep ":$PORT " > /dev/null; then
                echo "✅ 端口 $PORT 正在监听"
            else
                echo "❌ 端口 $PORT 未监听"
            fi
        fi

        # 检查HTTP响应
        if command -v curl &> /dev/null; then
            if curl -s --connect-timeout 5 "http://localhost:$PORT/health" > /dev/null; then
                echo "✅ HTTP服务正常响应"
                curl -s "http://localhost:$PORT/health" | head -3
            else
                echo "❌ HTTP服务无响应"
            fi
        fi
        ;;

    "help"|"-h"|"--help")
        echo ""
        echo "📖 使用说明:"
        echo "  bash start.sh [模式]"
        echo ""
        echo "可用模式:"
        echo "  development  - 开发模式 (默认)"
        echo "  production   - 生产模式 (Gunicorn)"
        echo "  systemd      - 安装为系统服务"
        echo "  test         - 运行API测试"
        echo "  stop         - 停止服务"
        echo "  restart      - 重启服务"
        echo "  status       - 检查服务状态"
        echo "  help         - 显示此帮助"
        echo ""
        echo "示例:"
        echo "  bash start.sh              # 开发模式"
        echo "  bash start.sh production   # 生产模式"
        echo "  bash start.sh test         # 测试模式"
        echo ""
        echo "配置文件: .env"
        echo "日志目录: logs/"
        echo "文档地址: http://localhost:$PORT/"
        ;;

    *)
        echo "❌ 未知模式: $1"
        echo "使用 'bash start.sh help' 查看可用选项"
        exit 1
        ;;
esac