"""端到端测试 — 验证 Router 全链路"""
import pytest
import subprocess
import time
import httpx
import asyncio


BASE_URL = "http://127.0.0.1:8000"


@pytest.fixture(scope="module")
def start_services():
    """启动所有后端服务"""
    venv = "/srv/agent-cluster/venv/bin/python3"
    
    # 启动 Hermes Adapter (后台)
    hermes_proc = subprocess.Popen(
        [venv, "adapter/hermes_adapter.py"],
        cwd="/srv/agent-cluster",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    
    # 启动 OpenClaw Mock (后台)
    oc_proc = subprocess.Popen(
        [venv, "adapter/openclaw_mock.py"],
        cwd="/srv/agent-cluster",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    
    # 启动 Router (后台)
    router_proc = subprocess.Popen(
        [venv, "router/server.py"],
        cwd="/srv/agent-cluster",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    
    # 等待服务就绪
    time.sleep(3)
    
    yield
    
    # 清理
    for proc in [hermes_proc, oc_proc, router_proc]:
        proc.terminate()
        proc.wait()


@pytest.mark.asyncio
async def test_router_health():
    """测试 Router 自身健康检查"""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE_URL}/health")
        assert resp.status_code == 200
        assert resp.json()["ready"] is True


@pytest.mark.asyncio
async def test_list_nodes():
    """测试节点列表"""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE_URL}/nodes")
        assert resp.status_code == 200
        nodes = resp.json()["nodes"]
        assert len(nodes) == 2  # oc-mock-1 + hm-1


@pytest.mark.asyncio
async def test_cluster_status():
    """测试集群状态"""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE_URL}/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "openclaw" in data
        assert "hermes" in data


@pytest.mark.asyncio
async def test_chat_preferred_openclaw():
    """测试手动指定 OpenClaw (mock 响应很快)"""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{BASE_URL}/chat",
            json={
                "messages": [{"role": "user", "content": "hello"}],
                "preferred": "openclaw",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["backend"] == "openclaw"


@pytest.mark.asyncio
async def test_chat_preferred_hermes():
    """测试手动指定 Hermes"""
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            f"{BASE_URL}/chat",
            json={
                "messages": [{"role": "user", "content": "say hello in one word"}],
                "preferred": "hermes",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["backend"] == "hermes"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
