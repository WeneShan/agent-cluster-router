#!/usr/bin/env python3
"""
Agent Cluster Router — 统一入口
对外: http://0.0.0.0:8000
对内: 调度 openclaw/hermes 后端
"""
import time
import httpx
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

from router.registry import NodeRegistry
from router.routing import RoutingEngine
from router.health import HealthChecker
from router.models import (
    AgentRequest, Message, TaskDefinition,
    InputContext, RoutingHint, TaskIntent,
    Priority, RouteStrategy,
)


# --- 全局状态 ---
registry = NodeRegistry()
routing_engine = RoutingEngine(registry)
health_checker = HealthChecker(registry)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动/关闭时管理健康检查"""
    await health_checker.start()
    yield
    await health_checker.stop()


app = FastAPI(
    title="Agent Cluster Router",
    description="OpenClaw + Hermes 混合集群统一入口",
    version="1.0.0",
    lifespan=lifespan,
)


# --- 请求模型 ---
class ChatMessage(BaseModel):
    role: str = "user"
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = []
    preferred: str = "auto"  # auto | openclaw | hermes
    tags: list[str] = []
    canary_ratio: float = 0.0
    system_prompt: str = ""
    intent: str = "chat"


# --- 端点 ---
@app.get("/health")
async def router_health():
    """Router 自身健康检查"""
    return {"status": "ok", "ready": True}


@app.get("/nodes")
async def list_nodes():
    """查看所有注册节点"""
    return {"nodes": registry.list_all()}


@app.get("/status")
async def cluster_status():
    """集群状态概览"""
    return {
        "openclaw": {
            "total": len(registry.get_pool("openclaw").nodes) if registry.get_pool("openclaw") else 0,
            "healthy": len(registry.get_pool("openclaw").healthy_nodes()) if registry.get_pool("openclaw") else 0,
        },
        "hermes": {
            "total": len(registry.get_pool("hermes").nodes) if registry.get_pool("hermes") else 0,
            "healthy": len(registry.get_pool("hermes").healthy_nodes()) if registry.get_pool("hermes") else 0,
        },
    }


@app.post("/chat")
async def chat(req: ChatRequest):
    """
    统一聊天入口 — Router 根据策略选择后端并转发请求
    """
    # 构建内部标准请求
    system_msgs = [Message(role="system", content=req.system_prompt)] if req.system_prompt else []
    user_msgs = [Message(role=m.role, content=m.content) for m in req.messages]

    internal_req = AgentRequest(
        task=TaskDefinition(
            intent=TaskIntent(req.intent),
            priority=Priority.NORMAL,
            tags=req.tags,
        ),
        input=InputContext(
            messages=system_msgs + user_msgs,
        ),
        routing=RoutingHint(
            preferred=RouteStrategy(req.preferred),
            canary_ratio=req.canary_ratio,
        ),
    )

    # 路由选择
    node = routing_engine.select_node(internal_req)
    if not node:
        raise HTTPException(status_code=503, detail="No healthy backend available")

    # 转发到后端
    start = time.time()
    async with httpx.AsyncClient(timeout=120) as client:
        try:
            resp = await client.post(
                f"{node.base_url}/chat",
                json={
                    "request_id": internal_req.request_id,
                    "messages": internal_req.to_dict()["input"]["messages"],
                    "timeout_ms": internal_req.runtime.timeout_ms,
                },
            )
            elapsed_ms = (time.time() - start) * 1000
            data = resp.json()

            return {
                "request_id": internal_req.request_id,
                "backend": node.cluster,
                "node": node.name,
                "content": data.get("content", ""),
                "success": data.get("success", resp.status_code == 200),
                "elapsed_ms": elapsed_ms,
                "tokens_used": data.get("tokens_used", 0),
            }
        except httpx.RequestError as e:
            # 标记节点为不健康
            pool = registry.get_pool(node.cluster)
            if pool:
                pool.mark_unhealthy(node.name)
            raise HTTPException(
                status_code=502,
                detail=f"Backend {node.cluster}/{node.name} unreachable: {str(e)}",
            )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
