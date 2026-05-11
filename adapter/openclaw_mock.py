#!/usr/bin/env python3
"""
OpenClaw Mock Adapter — 模拟 OpenClaw Agent 的 HTTP API
当真实 OpenClaw 安装后，替换此文件或修改 config.yaml 的 base_url 指向真实服务
"""
from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="OpenClaw Mock", version="1.0.0")


class ChatRequest(BaseModel):
    request_id: str = ""
    messages: list[dict] = []
    timeout_ms: int = 60000


@app.get("/health")
async def health():
    return {"status": "ok", "ready": True, "backend": "openclaw-mock"}


@app.post("/chat")
async def chat(req: ChatRequest):
    user_input = ""
    for m in req.messages:
        if m.get("role") == "user":
            user_input = m["content"]
            break

    return {
        "request_id": req.request_id,
        "content": f"[OpenClaw Mock] 收到请求: {user_input[:200]}...\n"
                   f"请求 ID: {req.request_id}\n"
                   f"(这是模拟响应。安装真实 OpenClaw 后，修改 config.yaml 的 base_url 即可)",
        "success": True,
        "elapsed_ms": 15.0,
        "tokens_used": 30,
    }


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8082, log_level="info")
