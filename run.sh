#!/bin/bash
# 🧸 Twinkle Mallow AI 客服系统一键启动脚本

# 确保脚本在它的目录下运行
cd "$(dirname "$0")"

echo "--------------------------------------------------"
echo "🚀 正在启动 Twinkle Mallow AI 客服系统..."
echo "--------------------------------------------------"

# 1. 杀死之前可能占用了 8000 端口或 cloudflared 的残留进程
lsof -ti:8000 | xargs kill -9 2>/dev/null
pkill -f "cloudflared" 2>/dev/null

# 2. 启动 FastAPI 后端服务 (后台运行)
python3 -m uvicorn app:app --host 0.0.0.0 --port 8000 > server.log 2>&1 &
SERVER_PID=$!

echo "⏳ 正在等待本地服务初始化 (5秒)..."
sleep 5

# 3. 启动 Cloudflare Tunnel，将本地 8000 端口映射到公网 HTTPS (后台运行)
echo "🌐 正在启动 Cloudflare 隧道，生成公网安全链接 (HTTPS)..."
if [ -f "../cloudflared" ]; then
    ../cloudflared tunnel --url http://localhost:8000 > tunnel.log 2>&1 &
    TUNNEL_PID=$!
else
    echo "❌ 错误: 未找到 cloudflared 模块，请检查上级目录。"
    kill $SERVER_PID
    exit 1
fi

# 等待隧道获取公网 URL
echo "⏳ 正在生成公网链接 (约10秒)..."
sleep 10

# 提取生成的 trycloudflare.com 链接
PUBLIC_URL=$(grep -oE "https://[a-zA-Z0-9.-]+\.trycloudflare\.com" tunnel.log | head -n 1)

echo "=================================================="
echo "🎉 系统启动成功！"
echo "💻 本地测试与配置中心：http://localhost:8000"
if [ -n "$PUBLIC_URL" ]; then
    echo "🌐 公网安全 Webhook 链接：$PUBLIC_URL"
    echo "👉 复制此链接到你的 TikTok 商家后台 Webhook 中：$PUBLIC_URL/api/chat"
else
    echo "⚠️ 警告: 无法自动读取公网链接，请查看 tunnel.log 获取。"
fi
echo "=================================================="
echo "📢 电脑将自动为你打开测试控制面板网页。"
echo "📢 保持此终端窗口不要关闭，关闭将停止服务。"
echo "🛑 退出系统：请在此窗口中按 Ctrl + C"
echo "=================================================="

# 自动在默认浏览器中打开控制面板
open "http://localhost:8000"

# 优雅退出逻辑，捕获 Ctrl+C 并清理后台进程
cleanup() {
    echo -e "\n🛑 正在关闭服务并退出..."
    kill $SERVER_PID 2>/dev/null
    kill $TUNNEL_PID 2>/dev/null
    exit 0
}

trap cleanup INT

# 持续等待
wait
