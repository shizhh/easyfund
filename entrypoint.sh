#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_PORT="${EASYFUND_BACKEND_PORT:-8000}"
MOCK_FLAG="${EASYFUND_MOCK:-}"

echo "ROOT_DIR:      $ROOT_DIR"
echo "BACKEND_PORT:  $BACKEND_PORT"
echo "EASYFUND_MOCK: ${MOCK_FLAG:-0}"

MOCK_ENV=""
if [[ "$MOCK_FLAG" == "1" ]]; then
    MOCK_ENV="EASYFUND_MOCK=1"
fi

# Detect uvicorn path: prefer .venv, fallback to system PATH
UVICORN_BIN="$ROOT_DIR/.venv/bin/uvicorn"
if [[ ! -x "$UVICORN_BIN" ]]; then
    UVICORN_BIN="uvicorn"
fi

# SSL: only enable if cert files exist
SSL_ARGS=""
if [[ -f "$ROOT_DIR/.ssl/cert.pem" && -f "$ROOT_DIR/.ssl/key.pem" ]]; then
    SSL_ARGS="--ssl-keyfile=$ROOT_DIR/.ssl/key.pem --ssl-certfile=$ROOT_DIR/.ssl/cert.pem"
    echo "SSL:           enabled"
else
    echo "SSL:           disabled"
fi

exec env $MOCK_ENV "$UVICORN_BIN" \
    backend.app:app \
    --host 0.0.0.0 \
    --port "$BACKEND_PORT" \
    $SSL_ARGS