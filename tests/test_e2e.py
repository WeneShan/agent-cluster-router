"""端到端测试 — 需要 Router + Adapters 全部运行"""
import pytest
import time
import httpx


BASE_URL = "http://127.0.0.1:8000"


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_router_health():
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE_URL}/health")
        assert resp.status_code == 200
        assert resp.json()["ready"] is True


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_nodes_listed():
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE_URL}/nodes")
        assert resp.status_code == 200
        nodes = resp.json()["nodes"]
        assert len(nodes) >= 5


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_chat_hermes():
    """测试 Hermes 后端"""
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            f"{BASE_URL}/chat",
            json={
                "messages": [{"role": "user", "content": "Say hello in one word."}],
                "preferred": "hermes",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["backend"] == "hermes"
        assert data["success"] is True
        assert len(data["content"]) > 0


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_chat_openclaw():
    """测试 OpenClaw 后端"""
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            f"{BASE_URL}/chat",
            json={
                "messages": [{"role": "user", "content": "Say hello in one word."}],
                "preferred": "openclaw",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["backend"] == "openclaw"
        assert data["success"] is True
        assert len(data["content"]) > 0


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_session_memory():
    """测试跨轮会话记忆"""
    async with httpx.AsyncClient(timeout=120) as client:
        # Turn 1: 设置上下文
        resp1 = await client.post(
            f"{BASE_URL}/chat",
            json={
                "messages": [{"role": "user", "content": "Remember: my favorite color is blue."}],
                "preferred": "hermes",
            },
        )
        assert resp1.status_code == 200
        data1 = resp1.json()
        session_id = data1.get("session_id")
        assert session_id

        # Turn 2: 引用上下文
        resp2 = await client.post(
            f"{BASE_URL}/chat",
            json={
                "session_id": session_id,
                "messages": [{"role": "user", "content": "What is my favorite color?"}],
                "preferred": "hermes",
            },
        )
        assert resp2.status_code == 200
        data2 = resp2.json()
        # 应该能回忆起 blue
        content = data2["content"].lower()
        assert "blue" in content, f"Expected 'blue' in response, got: {content[:100]}"


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_cross_backend_session():
    """测试跨后端会话 — Hermes 设上下文 → OpenClaw 读取"""
    async with httpx.AsyncClient(timeout=120) as client:
        # Turn 1: Hermes 设置上下文
        resp1 = await client.post(
            f"{BASE_URL}/chat",
            json={
                "messages": [{"role": "user", "content": "Memorize: the project name is 'Nebula'."}],
                "preferred": "hermes",
            },
        )
        assert resp1.status_code == 200
        session_id = resp1.json().get("session_id")

        # Turn 2: OpenClaw 读取
        resp2 = await client.post(
            f"{BASE_URL}/chat",
            json={
                "session_id": session_id,
                "messages": [{"role": "user", "content": "What's the project name I told you earlier?"}],
                "preferred": "openclaw",
            },
        )
        assert resp2.status_code == 200
        data2 = resp2.json()
        assert data2["backend"] == "openclaw"
        content = data2["content"].lower()
        # OpenClaw 应该能通过 prompt 历史看到
        assert "nebula" in content, f"Expected 'nebula' in cross-backend response: {content[:150]}"


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_sessions_list():
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE_URL}/sessions")
        assert resp.status_code == 200
        assert "sessions" in resp.json()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_canary_config():
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE_URL}/canary")
        assert resp.status_code == 200
        assert "canary_ratio" in resp.json()
