#!/bin/bash
# stop.sh — 停止 Agent Cluster 所有服务
echo "=== Agent Cluster Stop ==="

if [ -f /tmp/agent-cluster.pids ]; then
    for pid in $(cat /tmp/agent-cluster.pids); do
        kill $pid 2>/dev/null && echo "Killed PID=$pid" || echo "PID=$pid not running"
    done
    rm /tmp/agent-cluster.pids
else
    pkill -f "adapter/hermes_adapter" 2>/dev/null && echo "Killed hermes adapter"
    pkill -f "adapter/openclaw_adapter" 2>/dev/null && echo "Killed openclaw adapter"
    pkill -f "router/server" 2>/dev/null && echo "Killed router"
fi

echo "Done."
