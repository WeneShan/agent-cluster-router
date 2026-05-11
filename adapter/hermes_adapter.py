#!/usr/bin/env python3
"""
Hermes Adapter — 将 hermes chat -q 封装为 HTTP REST API
Router 通过 http://127.0.0.1:8081 调用此服务来调度 Hermes
"""
import subprocess
import json
import time
import re
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="Hermes Adapter", version="1.0.0")


class ChatRequest(BaseModel):
    request_id: str = ""
    messages: list[dict] = []
    timeout_ms: int = 120000
    max_steps: int = 20


@app.get("/health")
async def health():
    """健康检查端点 — Router 用来探测是否就绪"""
    try:
        result = subprocess.run(
            ["hermes", "--version"],
            capture_output=True, text=True, timeout=5
        )
        return {"status": "ok", "ready": result.returncode == 0, "backend": "hermes"}
    except Exception:
        return {"status": "error", "ready": False, "backend": "hermes"}


@app.post("/chat")
async def chat(req: ChatRequest):
    """
    接收 Router 转发的聊天请求，调用 hermes chat -q 并返回结果
    """
    # 提取最后一条 user 消息作为 prompt
    user_messages = [m["content"] for m in req.messages if m.get("role") == "user"]
    if not user_messages:
        raise HTTPException(status_code=400, detail="No user message found")

    prompt = user_messages[-1]
    # 如果有 system 消息，前置
    system_msgs = [m["content"] for m in req.messages if m.get("role") == "system"]
    if system_msgs:
        prompt = system_msgs[0] + "\n\n" + prompt

    start = time.time()
    timeout_sec = min(req.timeout_ms / 1000, 180)  # max 3min
    
    # 构建环境变量（需要 hermes 在 PATH 中）
    env = os.environ.copy()
    env["HERMES_HOME"] = env.get("HERMES_HOME", os.path.expanduser("~/.hermes"))

    try:
        result = subprocess.run(
            ["hermes", "chat", "-q", prompt, "-Q"],
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            env=env,
        )
        elapsed_ms = (time.time() - start) * 1000

        # 提取输出（去除 ANSI 颜色码）
        output = result.stdout
        output = re.sub(r'\x1b\[[0-9;]*m', '', output)

        # 估算 token
        tokens = len(output.split())

        return {
            "request_id": req.request_id,
            "content": output.strip() or result.stderr.strip(),
            "success": result.returncode == 0,
            "elapsed_ms": elapsed_ms,
            "tokens_used": tokens,
            "error": result.stderr[:500] if result.returncode != 0 else None,
        }
    except subprocess.TimeoutExpired:
        elapsed_ms = (time.time() - start) * 1000
        return {
            "request_id": req.request_id,
            "content": "",
            "success": False,
            "elapsed_ms": elapsed_ms,
            "tokens_used": 0,
            "error": "Hermes request timed out",
        }


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8081, log_level="info")
