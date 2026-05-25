#!/usr/bin/env bash
#set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
PID_DIR="$ROOT_DIR/.pids"
LOG_DIR="$ROOT_DIR/.logs"
NODE_BIN="$(dirname "$(command -v npx)")"
MOCK_FLAG="${EASYFUND_MOCK:-}"
DEV_FLAG="${EASYFUND_DEV:-}"
BACKEND_PORT="${EASYFUND_BACKEND_PORT:-8000}"
FRONTEND_PORT="${EASYFUND_FRONTEND_PORT:-3000}"

BACKEND_PID="$PID_DIR/backend.pid"
FRONTEND_PID="$PID_DIR/frontend.pid"
BACKEND_LOG="$LOG_DIR/backend.log"
FRONTEND_LOG="$LOG_DIR/frontend.log"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; }

init_dirs() {
  mkdir -p "$PID_DIR" "$LOG_DIR"
}

is_running() {
  local pid_file="$1"
  [[ -f "$pid_file" ]] && kill -0 "$(cat "$pid_file")" 2>/dev/null
}

# Kill a process and all its descendants (depth-first)
kill_tree() {
  local pid=$1 sig="${2:-TERM}"
  local children
  children=$(pgrep -P "$pid" 2>/dev/null || true)
  for child in $children; do
    kill_tree "$child" "$sig"
  done
  kill -"$sig" "$pid" 2>/dev/null || true
}

wait_for_port() {
  local port=$1 name=$2 timeout=15
  local i=0
  while ! lsof -iTCP:"$port" -sTCP:LISTEN -P -n >/dev/null 2>&1; do
    ((i++))
    if (( i >= timeout )); then
      error "$name failed to start on port $port (timeout ${timeout}s)"
      return 1
    fi
    sleep 1
  done
  info "$name is listening on port $port"
}

# ─── start ───────────────────────────────────────────────
start_backend() {
  if is_running "$BACKEND_PID"; then
    warn "Backend already running (PID $(cat "$BACKEND_PID"))"
    return 0
  fi
  info "Starting backend (FastAPI on :$BACKEND_PORT)..."
  cd "$ROOT_DIR"
  local mock_env=""
  if [[ "$MOCK_FLAG" == "1" ]]; then
    mock_env="EASYFUND_MOCK=1"
    info "Mock data mode enabled"
  fi
  nohup env $mock_env "$ROOT_DIR/.venv/bin/uvicorn" backend.app:app --host 0.0.0.0 --port "$BACKEND_PORT" --ssl-keyfile="$ROOT_DIR/.ssl/key.pem" --ssl-certfile="$ROOT_DIR/.ssl/cert.pem" > "$BACKEND_LOG" 2>&1 &
  echo $! > "$BACKEND_PID"
  wait_for_port "$BACKEND_PORT" "Backend"
}

start_frontend() {
  if is_running "$FRONTEND_PID"; then
    warn "Frontend already running (PID $(cat "$FRONTEND_PID"))"
    return 0
  fi
  info "Starting frontend (Vite on :$FRONTEND_PORT)..."
  cd "$ROOT_DIR/frontend"
  nohup ./node_modules/.bin/vite --host 0.0.0.0 --port "$FRONTEND_PORT" > "$FRONTEND_LOG" 2>&1 &
  echo $! > "$FRONTEND_PID"
  wait_for_port "$FRONTEND_PORT" "Frontend"
}

do_start() {
  init_dirs
  local dist_dir="$ROOT_DIR/frontend/dist"
  if [[ "$DEV_FLAG" != "1" ]]; then
    # Prod: auto-build frontend if dist is missing or source is newer
    local need_build=false
    if [[ ! -f "$dist_dir/index.html" ]]; then
      warn "frontend/dist not found — auto-building..."
      need_build=true
    elif [[ "$ROOT_DIR/frontend/src" -nt "$dist_dir/index.html" ]]; then
      info "frontend source changed — auto-building..."
      need_build=true
    fi
    if $need_build; then
      do_build
    fi
  fi
  start_backend
  if [[ "$DEV_FLAG" == "1" ]]; then
    start_frontend
  fi
  echo ""
  info "All services started! (mode: ${DEV_FLAG:+dev}${DEV_FLAG:-prod})"
  if [[ "$MOCK_FLAG" == "1" ]]; then
    info "  Data Mode: ${YELLOW}MOCK${NC} (示例数据)"
  fi
  if [[ "$DEV_FLAG" == "1" ]]; then
    info "  Frontend:  https://localhost:$FRONTEND_PORT"
    info "  Backend:   https://localhost:$BACKEND_PORT"
    info "  API Docs:  https://localhost:$BACKEND_PORT/docs"
  else
    info "  App:       https://localhost:$BACKEND_PORT"
    info "  API Docs:  https://localhost:$BACKEND_PORT/docs"
  fi
}

# ─── stop ────────────────────────────────────────────────
stop_service() {
  local name="$1" pid_file="$2"
  if ! is_running "$pid_file"; then
    # Clean up stale PID file if present
    [[ -f "$pid_file" ]] && rm -f "$pid_file"
    warn "$name is not running"
    return 0
  fi
  local pid
  pid=$(cat "$pid_file")
  info "Stopping $name (PID $pid)..."
  kill_tree "$pid" TERM
  # Wait up to 5s for graceful shutdown
  local i=0
  while kill -0 "$pid" 2>/dev/null; do
    ((i++))
    if (( i >= 5 )); then
      warn "Force killing $name..."
      kill_tree "$pid" 9
      break
    fi
    sleep 1
  done
  rm -f "$pid_file"
  info "$name stopped"
}

do_stop() {
  if [[ "$DEV_FLAG" == "1" ]]; then
    stop_service "Frontend" "$FRONTEND_PID"
  fi
  stop_service "Backend"  "$BACKEND_PID"
  info "All services stopped"
}

# ─── restart ─────────────────────────────────────────────
do_restart() {
  do_stop
  echo ""
  do_start
}

# ─── status ──────────────────────────────────────────────
do_status() {
  echo "Service Status:"
  echo "─────────────────────────────────────"
  echo -e "  Mode:      ${DEV_FLAG:+${YELLOW}DEV${NC}}${DEV_FLAG:-${GREEN}PROD${NC}}"
  if is_running "$BACKEND_PID"; then
    echo -e "  Backend:   ${GREEN}RUNNING${NC} (PID $(cat "$BACKEND_PID"), :$BACKEND_PORT)"
  else
    echo -e "  Backend:   ${RED}STOPPED${NC}"
  fi
  if [[ "$DEV_FLAG" == "1" ]]; then
    if is_running "$FRONTEND_PID"; then
      echo -e "  Frontend:  ${GREEN}RUNNING${NC} (PID $(cat "$FRONTEND_PID"), :$FRONTEND_PORT)"
    else
      echo -e "  Frontend:  ${RED}STOPPED${NC}"
    fi
  else
    local dist_dir="$ROOT_DIR/frontend/dist"
    if [[ -d "$dist_dir" ]]; then
      echo -e "  Frontend:  ${GREEN}dist served by backend${NC}"
    else
      echo -e "  Frontend:  ${RED}dist not found (run build)${NC}"
    fi
  fi
  if [[ "$MOCK_FLAG" == "1" ]]; then
    echo -e "  Data Mode: ${YELLOW}MOCK${NC}"
  else
    echo -e "  Data Mode: ${GREEN}REAL${NC}"
  fi
  echo "─────────────────────────────────────"
  echo ""
  echo "Data (SQLite):"
  local db_name="easyfund.db"
  if [[ "$MOCK_FLAG" == "1" ]]; then
    db_name="mock.db"
  fi
  local db_path="$ROOT_DIR/data/$db_name"
  if [[ -f "$db_path" ]]; then
    for table in accounts holdings transactions deposits exchange_rates fund_flows watchlist conversations; do
      local count=0
      count=$(sqlite3 "$db_path" "SELECT COUNT(*) FROM $table;" 2>/dev/null || echo "?")
      echo "  $table: $count records"
    done
  else
    echo "  Database not found: $db_path"
  fi
}

# ─── logs ────────────────────────────────────────────────
do_logs() {
  local target="${1:-all}"
  case "$target" in
    backend|b)  tail -f "$BACKEND_LOG" ;;
    frontend|f) tail -f "$FRONTEND_LOG" ;;
    all|*)      tail -f "$BACKEND_LOG" "$FRONTEND_LOG" ;;
  esac
}

# ─── import ──────────────────────────────────────────────
do_import() {
  local file="${1:-}"
  if [[ -z "$file" ]]; then
    error "Usage: $0 import <excel_file_path>"
    exit 1
  fi
  if [[ ! -f "$file" ]]; then
    error "File not found: $file"
    exit 1
  fi
  info "Importing: $file (AI auto-mapping)"
  cd "$ROOT_DIR"
  uv run python -c "
import asyncio
from backend.services.import_service import analyze_excel, import_excel_with_mapping
from backend.database import ensure_db
from pathlib import Path

async def do_import():
    await ensure_db('')
    content = Path('$file').read_bytes()
    session_id, mapping = await analyze_excel(content)
    print(f'  AI mapping confidence: {mapping.confidence}')
    for sheet in mapping.sheets:
        print(f'  Sheet: {sheet.sheet_name} -> {sheet.target_types}')
    result = await import_excel_with_mapping(session_id, mapping)
    for k, v in result.items():
        print(f'  {k}: {v}')
    print('Done!')

asyncio.run(do_import())
"
  info "Import complete. Restart backend to reload data."
}

# ─── build ───────────────────────────────────────────────
do_build() {
  info "Building frontend for production..."
  cd "$ROOT_DIR/frontend"
  "$NODE_BIN/npm" run build
  info "Build complete: frontend/dist/"
}

# ─── add-user ─────────────────────────────────────────────
do_add_user() {
  local username="${1:-}"
  local data_dir="${2:-}"
  local display_name="${3:-$username}"
  if [[ -z "$username" ]]; then
    error "Usage: $0 add-user <username> [data_dir] [display_name]"
    echo "  username     用户名 (必填)"
    echo "  data_dir     数据目录 (空=真实数据, mock=示例数据, 默认空)"
    echo "  display_name 显示名称 (默认=username)"
    exit 1
  fi
  info "Adding user: $username"
  cd "$ROOT_DIR"
  uv run python -c "
import json, getpass
from backend.auth import hash_password, USERS_PATH

password = getpass.getpass('Password: ')
password2 = getpass.getpass('Confirm password: ')
if password != password2:
    print('Error: passwords do not match')
    exit(1)

users = []
if USERS_PATH.exists():
    with open(USERS_PATH) as f:
        users = json.load(f)

if any(u['username'] == '$username' for u in users):
    print('Error: user already exists')
    exit(1)

users.append({
    'username': '$username',
    'password_hash': hash_password(password),
    'data_dir': '$data_dir',
    'display_name': '$display_name',
})

with open(USERS_PATH, 'w') as f:
    json.dump(users, f, ensure_ascii=False, indent=2)

print('User added successfully!')
"
}

# ─── help ────────────────────────────────────────────────
do_help() {
  cat <<EOF
EasyFund - 家庭资产管理服务管理脚本

Usage: $0 <command> [args]

Commands:
  start [options]      启动服务 (默认prod模式，仅backend)
  stop                 停止服务
  restart [options]    重启服务
  status               查看服务状态和数据概况
  logs [target]        查看日志 (backend|frontend|all, 默认all)
  import <file>        从Excel文件导入数据
  add-user <name> [dir] [display]
                       添加用户 (dir: 空=真实数据, mock=示例数据)
  build                构建前端生产版本
  help                 显示帮助信息

Options:
  --dev               开发模式: 分别启动backend + vite dev server
  --mock              使用 mock 示例数据
  --backend-port PORT 指定后端端口 (默认: 8000)
  --frontend-port PORT 指定前端端口 (仅dev模式, 默认: 3000)

Environment:
  EASYFUND_DEV=1            等同于 --dev，开发模式
  EASYFUND_MOCK=1           等同于 --mock，使用 mock 数据
  EASYFUND_BACKEND_PORT     等同于 --backend-port，指定后端端口
  EASYFUND_FRONTEND_PORT    等同于 --frontend-port，指定前端端口

Examples:
  $0 start                  # prod模式: backend托管frontend/dist
  $0 start --dev            # dev模式: backend + vite dev server
  $0 start --dev --mock     # dev + mock数据
  $0 build && $0 start      # 先构建再启动(prod)
  $0 logs backend
  $0 import /Users/shizhenhui/Downloads/资产分析.xlsx
  $0 status
EOF
}

# ─── main ────────────────────────────────────────────────
# Parse global flags and collect remaining args
REMAINING_ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --mock)
      MOCK_FLAG="1"
      export EASYFUND_MOCK=1
      shift
      ;;
    --dev)
      DEV_FLAG="1"
      export EASYFUND_DEV=1
      shift
      ;;
    --backend-port)
      BACKEND_PORT="$2"
      export EASYFUND_BACKEND_PORT="$2"
      shift 2
      ;;
    --frontend-port)
      FRONTEND_PORT="$2"
      export EASYFUND_FRONTEND_PORT="$2"
      shift 2
      ;;
    *)
      REMAINING_ARGS+=("$1")
      shift
      ;;
  esac
done

cmd="${REMAINING_ARGS[0]:-help}"
cmd_arg="${REMAINING_ARGS[1]:-}"

case "$cmd" in
  start)     do_start ;;
  stop)      do_stop ;;
  restart)   do_restart ;;
  status)    do_status ;;
  logs)      do_logs "${cmd_arg:-all}" ;;
  import)    do_import "$cmd_arg" ;;
  add-user)  do_add_user "$cmd_arg" "${REMAINING_ARGS[2]:-}" "${REMAINING_ARGS[3]:-}" ;;
  build)     do_build ;;
  help|*)    do_help ;;
esac
