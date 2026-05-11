#!/bin/bash
# start.sh — 启动 Agent Cluster 所有服务
set -e
DIR=/srv/agent-cluster
VENV=$DIR/venv/bin/python3
cd $DIR

echo "=== Agent Cluster Start ==="

# Create log dirs
mkdir -p /srv/openclaw/logs /srv/hermes/logs

# 1. OpenClaw Adapter (8082)
echo "[1/3] Starting OpenClaw Adapter on :8082..."
PYTHONPATH=$DIR $VENV adapter/openclaw_adapter.py > /srv/openclaw/logs/adapter.log 2>&1 &
OC_PID=$!
echo "  PID=$OC_PID"

# 2. Hermes Adapter (8081)
echo "[2/3] Starting Hermes Adapter on :8081..."
PYTHONPATH=$DIR $VENV adapter/hermes_adapter.py > /srv/hermes/logs/adapter.log 2>&1 &
HM_PID=$!
echo "  PID=$HM_PID"

# 3. Router (8000)
echo "[3/3] Starting Router on :8000..."
PYTHONPATH=$DIR $VENV router/server.py > /tmp/router.log 2>&1 &
RT_PID=$!
echo "  PID=$RT_PID"

sleep 3

# Health check
echo ""
echo "=== Health Check ==="
echo -n "Router:   "; curl -sf http://127.0.0.1:8000/health && echo "OK" || echo "FAIL"
echo -n "Hermes:   "; curl -sf http://127.0.0.1:8081/health && echo "OK" || echo "FAIL"
echo -n "OpenClaw: "; curl -sf http://127.0.0.1:8082/health && echo "OK" || echo "FAIL"

echo ""
echo "=== Cluster Ready ==="
echo "Router:  http://127.0.0.1:8000"
echo "Nodes:   curl http://127.0.0.1:8000/nodes"
echo "Status:  curl http://127.0.0.1:8000/status"

# Save PIDs
echo "$OC_PID $HM_PID $RT_PID" > /tmp/agent-cluster.pids

wait
