"""CS-Agent - 生产级 AI 客服系统"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from agent.core import Agent, AgentConfig
from agent.tools import create_default_tools

app = FastAPI(title="CS-Agent API", version="1.0.0")

# 全局 Agent 实例
agent = None


@app.on_event("startup")
async def startup():
    global agent
    config = AgentConfig(
        model="gpt-4o-mini",
        system_prompt="你是一个专业的 AI 客服助手，善于使用工具解决问题。",
        tools=create_default_tools()
    )
    agent = Agent(config)


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    reply: str
    session_id: str


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    try:
        reply = await agent.run(request.message)
        return ChatResponse(reply=reply, session_id=request.session_id or "default")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    return {"status": "healthy", "model": agent.config.model if agent else "not initialized"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
