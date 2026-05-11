#!/usr/bin/env python3
"""
OpenClaw Adapter — 将 openclaw agent 封装为 HTTP REST API
Router 通过 http://127.0.0.1:8082 调用此服务来调度 OpenClaw

前置条件：用户已运行 openclaw configure 配置 API key
测试命令：openclaw agent --agent cluster-agent --local --message "hello" --json
"""
import subprocess
import json
import time
import re
import os
import uuid
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="OpenClaw Adapter", version="2.0.0")

# Agent ID used for one-shot calls (created via openclaw agents add)
OPENCLAW_AGENT = os.environ.get("OPENCLAW_AGENT_ID", "cluster-agent")
OPENCLAW_MODEL = os.environ.get("OPENCLAW_MODEL", "deepseek/deepseek-v4-pro")
OPENCLAW_TIMEOUT = int(os.environ.get("OPENCLAW_TIMEOUT", "120"))


class ChatRequest(BaseModel):
    request_id: str = ""
    messages: list[dict] = []
    session_id: str = ""
    timeout_ms: int = 120000


@app.get("/health")
async def health():
    """健康检查 — Router 用来探测 OpenClaw 是否就绪"""
    try:
        result = subprocess.run(
            ["openclaw", "--version"],
            capture_output=True, text=True, timeout=5
        )
        ready = result.returncode == 0
        
        # 额外检查 agent 是否可用
        if ready:
            result2 = subprocess.run(
                ["openclaw", "agents", "list"],
                capture_output=True, text=True, timeout=5
            )
            ready = OPENCLAW_AGENT in result2.stdout
        
        return {"status": "ok", "ready": ready, "backend": "openclaw"}
    except Exception as e:
        return {"status": "error", "ready": False, "backend": "openclaw", "error": str(e)}


@app.post("/chat")
async def chat(req: ChatRequest):
    """
    接收 Router 转发的聊天请求，调用 openclaw agent --local 并返回结果
    支持多轮对话：将完整消息历史拼接为对话 prompt
    """
    # 拼接完整对话为 prompt
    prompt = _format_conversation(req.messages)
    if not prompt:
        raise HTTPException(status_code=400, detail="No messages provided")

    # 使用 Router 传来的 session_id 保持连续性
    session_id = req.session_id or f"router-{req.request_id[:8] if req.request_id else uuid.uuid4().hex[:8]}"
    
    timeout_sec = min(req.timeout_ms / 1000, OPENCLAW_TIMEOUT)
    start = time.time()

    try:
        result = subprocess.run(
            [
                "openclaw", "agent",
                "--agent", OPENCLAW_AGENT,
                "--model", OPENCLAW_MODEL,
                "--local",
                "--session-id", session_id,
                "--message", prompt,
                "--json",
                "--timeout", str(int(timeout_sec)),
            ],
            capture_output=True,
            text=True,
            timeout=timeout_sec + 10,  # extra buffer for openclaw overhead
        )
        elapsed_ms = (time.time() - start) * 1000

        # 尝试解析 JSON 输出
        output = result.stdout.strip()
        content = ""
        error = None
        
        if output:
            try:
                data = json.loads(output)
                # openclaw agent --json 返回: payloads[0].text, meta.agentMeta.usage
                content = (
                    (data.get("payloads") or [{}])[0].get("text") or
                    data.get("reply") or data.get("text") or data.get("content") or output
                )
                # 提取 token 用量
                agent_meta = data.get("meta", {}).get("agentMeta", {})
                usage = agent_meta.get("usage", {}) or agent_meta.get("lastCallUsage", {})
                tokens = usage.get("total", 0)
            except json.JSONDecodeError:
                # 不是 JSON，直接使用原始输出
                content = output
                # 去除 ANSI 颜色码
                content = re.sub(r'\\x1b\\[[0-9;]*m', '', content)
                tokens = len(content.split())

        if not content and result.stderr:
            # 检查是否有错误
            stderr_clean = re.sub(r'\x1b\[[0-9;]*m', '', result.stderr)
            if "Error:" in stderr_clean or "error:" in stderr_clean.lower():
                error = stderr_clean[:500]
                content = ""
            else:
                content = stderr_clean

        return {
            "request_id": req.request_id,
            "content": content.strip(),
            "success": result.returncode == 0 and bool(content),
            "elapsed_ms": elapsed_ms,
            "tokens_used": tokens,
            "error": error,
        }
    except subprocess.TimeoutExpired:
        elapsed_ms = (time.time() - start) * 1000
        return {
            "request_id": req.request_id,
            "content": "",
            "success": False,
            "elapsed_ms": elapsed_ms,
            "tokens_used": 0,
            "error": "OpenClaw request timed out",
        }
    except FileNotFoundError:
        return {
            "request_id": req.request_id,
            "content": "",
            "success": False,
            "elapsed_ms": 0,
            "tokens_used": 0,
            "error": "openclaw command not found. Is it installed? Run: npm install -g openclaw",
        }


def _format_conversation(messages: list[dict]) -> str:
    """将消息列表格式化为对话 prompt"""
    parts = []
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content", "")
        if role == "system":
            parts.append(f"[System]\n{content}")
        elif role == "user":
            parts.append(f"[User]\n{content}")
        elif role == "assistant":
            parts.append(f"[Assistant]\n{content}")
    return "\n\n".join(parts)


if __name__ == "__main__":
    print(f"[OpenClaw Adapter] Agent: {OPENCLAW_AGENT}")
    uvicorn.run(app, host="127.0.0.1", port=8082, log_level="info")
