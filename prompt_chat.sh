#!/usr/bin/env bash
set -euo pipefail

cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
PORT="${PROMPT_CHAT_PORT:-4760}"
HOST="${PROMPT_CHAT_HOST:-0.0.0.0}"

PY_BIN="python3"
if [[ -x .venv/bin/python ]]; then
    PY_BIN=".venv/bin/python"
fi

LAN_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "127.0.0.1")

echo "=========================================================="
echo "🎬 Video Prompt Chat đang chạy (hỗ trợ SSE):"
echo " - Cục bộ:       http://localhost:${PORT}"
echo " - Mạng nội bộ:  http://${LAN_IP}:${PORT}"
echo "=========================================================="

exec "$PY_BIN" -m uvicorn prompt_chat.server:app --host "$HOST" --port "$PORT" "$@"
