#!/bin/sh
# 在容器内启动私有 FastAPI + 对公网暴露的 Streamlit。
set -eu
PORT="${PORT:-10000}"
export PORT

python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 &
api_pid=$!

shutdown() {
  kill "$api_pid" 2>/dev/null || true
  wait "$api_pid" 2>/dev/null || true
}
trap shutdown EXIT INT TERM

# 仅 Streamlit 对外服务；关闭不必要的开发功能，保留安全检查。
python -m streamlit run frontend.py \
  --server.address=0.0.0.0 \
  --server.port="$PORT" \
  --server.headless=true \
  --server.enableCORS=true \
  --server.enableXsrfProtection=true \
  --browser.gatherUsageStats=false
