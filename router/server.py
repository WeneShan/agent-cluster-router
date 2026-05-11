#!/usr/bin/env python3
"""
Agent Cluster Router — 统一入口
对外: http://0.0.0.0:8000
对内: 调度 openclaw/hermes 后端
"""
import time
import uuid
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


# --- 会话管理 ---
class SessionManager:
    """内存会话存储：session_id → messages 列表"""
    def __init__(self):
        self._store: dict[str, list[dict]] = {}

    def get(self, session_id: str) -> list[dict]:
        return self._store.get(session_id, [])

    def append(self, session_id: str, messages: list[dict]):
        if session_id not in self._store:
            self._store[session_id] = []
        self._store[session_id].extend(messages)

    def delete(self, session_id: str):
        self._store.pop(session_id, None)

    def list_sessions(self) -> list[dict]:
        return [
            {"session_id": sid, "turns": len(msgs)}
            for sid, msgs in self._store.items()
        ]


# --- 全局状态 ---
registry = NodeRegistry()
routing_engine = RoutingEngine(registry)
health_checker = HealthChecker(registry)
session_manager = SessionManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动/关闭时管理健康检查"""
    await health_checker.start()
    yield
    await health_checker.stop()


app = FastAPI(
    title="Agent Cluster Router",
    description="OpenClaw + Hermes 混合集群统一入口",
    version="2.0.0",
    lifespan=lifespan,
)


# --- 请求模型 ---
class ChatMessage(BaseModel):
    role: str = "user"
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = []
    session_id: str = ""          # 空 = 新会话, 非空 = 续接
    preferred: str = "auto"       # auto | openclaw | hermes
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
    sessions = session_manager.list_sessions()
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
        "sessions": len(sessions),
    }


@app.get("/canary")
async def get_canary():
    """查看当前灰度配置"""
    return routing_engine.get_canary_status()


class CanaryConfig(BaseModel):
    ratio: float = 0.0
    target: str = "hermes"


@app.put("/canary")
async def set_canary(cfg: CanaryConfig):
    """动态设置灰度发布参数"""
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


@app.get("/sessions")
async def list_sessions():
    """列出所有活跃会话"""
    return {"sessions": session_manager.list_sessions()}


@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """删除指定会话"""
    session_manager.delete(session_id)
    return {"message": f"Session {session_id} deleted"}


class SessionDeleteRequest(BaseModel):
    session_id: str


@app.post("/sessions/delete")
async def delete_session_post(req: SessionDeleteRequest):
    """删除指定会话 (POST)"""
    session_manager.delete(req.session_id)
    return {"message": f"Session {req.session_id} deleted"}


@app.post("/chat")
async def chat(req: ChatRequest):
    """
    统一聊天入口 — 支持会话记忆
    
    会话模式:
      POST /chat {"session_id": "abc", "messages": [...]}
      → 加载历史 + 追加新消息 → 发完整上下文给后端 → 返回 session_id
    
    单次模式:
      POST /chat {"messages": [...]}
      → 直接转发，不保存历史
    """
    # 生成或使用已有 session_id
    session_id = req.session_id or str(uuid.uuid4())
    
    # 获取会话历史
    history = session_manager.get(session_id) if req.session_id else []
    
    # 追加新消息
    new_messages = [{"role": m.role, "content": m.content} for m in req.messages]
    session_manager.append(session_id, new_messages)
    
    # 构建完整上下文
    full_messages = history + new_messages
    if req.system_prompt:
        full_messages = [{"role": "system", "content": req.system_prompt}] + full_messages

    # 路由选择
    internal_req = AgentRequest(
        task=TaskDefinition(
            intent=TaskIntent(req.intent),
            priority=Priority.NORMAL,
            tags=req.tags,
        ),
        input=InputContext(
            messages=[Message(role=m["role"], content=m["content"]) for m in full_messages],
        ),
        routing=RoutingHint(
            preferred=RouteStrategy(req.preferred),
            canary_ratio=req.canary_ratio,
        ),
    )
    
    node = routing_engine.select_node(internal_req)
    if not node:
        raise HTTPException(status_code=503, detail="No healthy backend available")

    # 转发到后端（发送完整历史）
    start = time.time()
    async with httpx.AsyncClient(timeout=180) as client:
        try:
            resp = await client.post(
                f"{node.base_url}/chat",
                json={
                    "request_id": internal_req.request_id,
                    "messages": full_messages,
                    "session_id": session_id,
                    "timeout_ms": internal_req.runtime.timeout_ms,
                },
            )
            elapsed_ms = (time.time() - start) * 1000
            data = resp.json()

            return {
                "request_id": internal_req.request_id,
                "session_id": session_id,
                "backend": node.cluster,
                "node": node.name,
                "content": data.get("content", ""),
                "success": data.get("success", resp.status_code == 200),
                "elapsed_ms": elapsed_ms,
                "tokens_used": data.get("tokens_used", 0),
            }
        except httpx.RequestError as e:
            pool = registry.get_pool(node.cluster)
            if pool:
                pool.mark_unhealthy(node.name)
            raise HTTPException(
                status_code=502,
                detail=f"Backend {node.cluster}/{node.name} unreachable: {str(e)}",
            )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
