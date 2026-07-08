"""
知墨教育 - FastAPI 主应用
提供静态文件服务 + AI 聊天 API
"""
import os
import json
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

from chatbot import chat_stream

app = FastAPI(title="知墨教育")

# CORS（开发环境允许所有来源）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# 聊天 API
# ============================================================

@app.post("/api/chat")
async def chat(request: Request):
    """流式聊天接口 - SSE"""
    body = await request.json()
    message = body.get("message", "")
    history = body.get("history", [])
    
    async def event_generator():
        async for chunk in chat_stream(message, history):
            yield f"data: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Content-Type": "text/event-stream; charset=utf-8",
        }
    )

# ============================================================
# 静态文件服务
# ============================================================

PUBLIC_DIR = Path(__file__).parent / "public"

@app.get("/")
async def index():
    return FileResponse(PUBLIC_DIR / "index.html")

app.mount("/static", StaticFiles(directory=str(PUBLIC_DIR)), name="static")

@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "zhimu-education"}

# 所有未匹配的路由返回 index.html（SPA fallback）
@app.get("/{path:path}")
async def fallback(path: str):
    file_path = PUBLIC_DIR / path
    if file_path.is_file():
        return FileResponse(file_path)
    return FileResponse(PUBLIC_DIR / "index.html")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 3000))
    uvicorn.run(app, host="0.0.0.0", port=port)
