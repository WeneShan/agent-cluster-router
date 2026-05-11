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
    canary = routing_engine.get_canary_status()
    oc_pool = registry.get_pool("openclaw")
    hm_pool = registry.get_pool("hermes")
    return {
        "openclaw": {
            "total": len(oc_pool.nodes) if oc_pool else 0,
            "healthy": len(oc_pool.healthy_nodes()) if oc_pool else 0,
        },
        "hermes": {
            "total": len(hm_pool.nodes) if hm_pool else 0,
            "healthy": len(hm_pool.healthy_nodes()) if hm_pool else 0,
        },
        "canary": {
            "ratio": canary["canary_ratio"],
            "target": canary["canary_target"],
            "description": f"{canary['canary_ratio']*100:.0f}% → {canary['canary_target']}, "
                           f"{(1-canary['canary_ratio'])*100:.0f}% → {canary['default_target']}",
        },
        "requests": canary["request_counts"],
        "total_canary_requests": canary["total_canary_requests"],
    }


@app.get("/canary")
async def get_canary():
    """查看当前灰度配置"""
    return routing_engine.get_canary_status()


class CanaryConfig(BaseModel):
    ratio: float = 0.0        # 0.0-1.0, 灰度目标的后端流量占比
    target: str = "hermes"    # 灰度目标: hermes | openclaw


@app.put("/canary")
async def set_canary(cfg: CanaryConfig):
    """动态设置灰度发布参数
    
    Example:
      PUT /canary  {"ratio": 0.3, "target": "hermes"}
      → 30% 流量走 Hermes, 70% 走 OpenClaw
      
      PUT /canary  {"ratio": 1.0, "target": "openclaw"}
      → 100% 流量走 OpenClaw
    """
    if cfg.target not in ("hermes", "openclaw"):
        raise HTTPException(status_code=400, detail="target must be 'hermes' or 'openclaw'")
    routing_engine.set_canary(cfg.ratio, cfg.target)
    routing_engine.reset_counts()
    return {
        "message": "Canary updated",
        "ratio": cfg.ratio,
        "target": cfg.target,
        "description": f"{cfg.ratio*100:.0f}% → {cfg.target}",
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
