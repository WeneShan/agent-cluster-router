"""Router API 端点测试（使用 TestClient）"""
import pytest
import sys
sys.path.insert(0, "/srv/agent-cluster")

from fastapi.testclient import TestClient

# 导入 app 前，mock 掉 lifespan（避免启动后台健康检查）
import router.server as server_module

# 用 dummy lifespan 替换
from contextlib import asynccontextmanager

@asynccontextmanager
async def dummy_lifespan(app):
    yield

server_module.lifespan = dummy_lifespan
server_module.app.router.lifespan_context = dummy_lifespan

# 重建 app 避开 lifespan
from fastapi import FastAPI

# 直接用已有的 app 实例但绕过 lifespan
client = TestClient(server_module.app)


class TestRouterAPI:
    def test_health(self):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["ready"] is True

    def test_list_nodes(self):
        resp = client.get("/nodes")
        assert resp.status_code == 200
        nodes = resp.json()["nodes"]
        assert len(nodes) == 5  # 5 nodes total

    def test_cluster_status(self):
        resp = client.get("/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "openclaw" in data
        assert "hermes" in data
        assert data["openclaw"]["total"] == 2  # oc-1, oc-2
        assert data["hermes"]["total"] == 3    # hm-1, hm-2, hm-3
        assert data["openclaw"]["healthy"] == 1  # only oc-1 healthy
        assert data["hermes"]["healthy"] == 1    # only hm-1 healthy

    def test_get_canary(self):
        resp = client.get("/canary")
        assert resp.status_code == 200
        data = resp.json()
        assert "canary_ratio" in data

    def test_set_canary(self):
        resp = client.put("/canary", json={"ratio": 0.5, "target": "hermes"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["ratio"] == 0.5

    def test_set_canary_invalid_target(self):
        resp = client.put("/canary", json={"ratio": 0.5, "target": "gpt"})
        assert resp.status_code == 400

    def test_list_sessions_empty(self):
        resp = client.get("/sessions")
        assert resp.status_code == 200
        assert isinstance(resp.json()["sessions"], list)

    def test_delete_session(self):
        resp = client.delete("/sessions/test-123")
        assert resp.status_code == 200

    def test_delete_session_post(self):
        resp = client.post("/sessions/delete", json={"session_id": "test-123"})
        assert resp.status_code == 200
