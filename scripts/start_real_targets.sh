#!/usr/bin/env bash
# Start (or restart with clean state) the two real open-source targets used in the evaluation.
# usage: scripts/start_real_targets.sh <venv-bin-dir>
V=${1:-/home/claude/venv_real/bin}
D=$(cd "$(dirname "$0")/.." && pwd)/real_state
for f in "$D/httpbin.pid" "$D/chroma.pid"; do [ -f "$f" ] && kill "$(cat "$f")" 2>/dev/null; done
# also free the ports if an older, pid-less instance is still running
for port in 8081 8082; do fuser -k ${port}/tcp >/dev/null 2>&1; done
sleep 1
rm -rf "$D"; mkdir -p "$D/chroma_data" "$D/logs"
nohup $V/gunicorn -b 127.0.0.1:8081 httpbin:app > "$D/logs/httpbin.log" 2>&1 & echo $! > "$D/httpbin.pid"
nohup $V/chroma run --path "$D/chroma_data" --host 127.0.0.1 --port 8082 > "$D/logs/chroma.log" 2>&1 & echo $! > "$D/chroma.pid"
for i in $(seq 1 60); do
  curl -s -o /dev/null http://127.0.0.1:8081/get && curl -s -o /dev/null http://127.0.0.1:8082/api/v2/heartbeat && break; sleep 0.5; done
echo "targets up: httpbin :8081, chroma :8082"
