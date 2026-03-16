"""
Ada REST API - Complete implementation with WebSocket support
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
import uvicorn
import json

from ada.core.agent import AdaAgent, create_agent
from ada.core.context import AgentConfig
from ada.skill.base import SkillResult

logger = logging.getLogger(__name__)

# Global agent instance
_agent: Optional[AdaAgent] = None
_config: Optional[AgentConfig] = None


# Lifespan manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan"""
    global _agent, _config

    # Startup
    _config = AgentConfig()
    _agent = await create_agent(_config)
    logger.info("Ada API started")

    yield

    # Shutdown
    if _agent:
        await _agent.shutdown()
    logger.info("Ada API stopped")


# Create FastAPI app
app = FastAPI(
    title="Ada API",
    description="HTTP API for Ada AI Assistant",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer(auto_error=False)


# ============== Models ==============

class ProcessRequest(BaseModel):
    """Request to process user input"""
    text: str = Field(..., description="User input text")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context")
    stream: bool = Field(default=False, description="Enable streaming response")


class ProcessResponse(BaseModel):
    """Response from processing"""
    success: bool
    message: str
    output: Optional[Dict[str, Any]] = None
    skill_used: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class SkillInfo(BaseModel):
    """Skill information"""
    id: str
    name: str
    description: str
    category: str
    version: str
    tags: List[str] = []
    permissions: List[str] = []
    examples: List[str] = []


class SkillExecuteRequest(BaseModel):
    """Request to execute a skill"""
    input_text: str
    params: Optional[Dict[str, Any]] = None


class MemoryStoreRequest(BaseModel):
    """Request to store memory"""
    content: str
    type: str = "semantic"
    metadata: Optional[Dict[str, Any]] = None
    importance: float = 0.5


class MemorySearchRequest(BaseModel):
    """Request to search memories"""
    query: str
    limit: int = 10
    types: Optional[List[str]] = None


class MemoryResult(BaseModel):
    """Memory search result"""
    id: str
    content: str
    type: str
    created_at: str
    importance: float


class StatusResponse(BaseModel):
    """Status response"""
    status: str
    version: str
    mode: str
    skills_count: int
    memory_count: int
    uptime_seconds: float


class EventSubscription(BaseModel):
    """Event subscription request"""
    event_types: List[str]
    webhook_url: Optional[str] = None


class ErrorResponse(BaseModel):
    """Error response"""
    error: str
    detail: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


# ============== Dependencies ==============

def get_agent() -> AdaAgent:
    """Get agent instance"""
    if _agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    return _agent


async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Optional[str]:
    """Verify API token (optional)"""
    if credentials is None:
        return None
    # For now, accept any token
    return credentials.credentials


# ============== Endpoints ==============

@app.get("/", tags=["Root"])
async def root():
    """Root endpoint"""
    return {
        "name": "Ada API",
        "version": "0.1.0",
        "docs": "/docs",
        "websocket": "/ws"
    }


@app.get("/health", tags=["Health"])
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/ready", tags=["Health"])
async def ready(agent: AdaAgent = Depends(get_agent)):
    """Readiness check endpoint"""
    return {
        "ready": agent._initialized,
        "timestamp": datetime.now().isoformat()
    }


# ============== Process Endpoints ==============

@app.post("/process", response_model=ProcessResponse, tags=["Process"])
async def process(
    request: ProcessRequest,
    agent: AdaAgent = Depends(get_agent),
    token: Optional[str] = Depends(verify_token)
):
    """Process user input and return response"""
    try:
        result = await agent.process(request.text)

        return ProcessResponse(
            success=result.success,
            message=result.message,
            output=result.output,
            skill_used=result.skill_id,
        )

    except Exception as e:
        logger.error(f"Process error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/process/stream", tags=["Process"])
async def process_stream(
    request: ProcessRequest,
    agent: AdaAgent = Depends(get_agent)
):
    """Process input with streaming response"""
    async def generate():
        try:
            # Register callback for streaming
            chunks = []

            def on_chunk(text):
                chunks.append(text)

            agent.on_response(on_chunk)

            # Process
            result = await agent.process(request.text)

            # Stream response
            for i, char in enumerate(result.message):
                yield json.dumps({
                    "type": "chunk",
                    "content": char,
                    "index": i
                }) + "\n"

            yield json.dumps({
                "type": "done",
                "success": result.success,
                "output": result.output
            }) + "\n"

        except Exception as e:
            yield json.dumps({
                "type": "error",
                "message": str(e)
            }) + "\n"

    return StreamingResponse(
        generate(),
        media_type="application/x-ndjson"
    )


# ============== Skills Endpoints ==============

@app.get("/skills", response_model=List[SkillInfo], tags=["Skills"])
async def list_skills(
    category: Optional[str] = Query(None, description="Filter by category"),
    search: Optional[str] = Query(None, description="Search query"),
    agent: AdaAgent = Depends(get_agent)
):
    """List available skills"""
    if search:
        skills = agent.skill_registry.search(search)
    else:
        skills = agent.skill_registry.list_skills(category=category)

    return [
        SkillInfo(
            id=s.metadata.id,
            name=s.metadata.name,
            description=s.metadata.description,
            category=s.metadata.category,
            version=s.metadata.version,
            tags=s.metadata.tags,
            permissions=s.metadata.permissions,
            examples=s.metadata.examples,
        )
        for s in skills
    ]


@app.get("/skills/{skill_id}", response_model=SkillInfo, tags=["Skills"])
async def get_skill(
    skill_id: str,
    agent: AdaAgent = Depends(get_agent)
):
    """Get skill information"""
    skill = agent.skill_registry.get(skill_id)

    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    return SkillInfo(
        id=skill.metadata.id,
        name=skill.metadata.name,
        description=skill.metadata.description,
        category=skill.metadata.category,
        version=skill.metadata.version,
        tags=skill.metadata.tags,
        permissions=skill.metadata.permissions,
        examples=skill.metadata.examples,
    )


@app.post("/skills/{skill_id}/execute", response_model=ProcessResponse, tags=["Skills"])
async def execute_skill(
    skill_id: str,
    request: SkillExecuteRequest,
    agent: AdaAgent = Depends(get_agent),
    token: Optional[str] = Depends(verify_token)
):
    """Execute a specific skill"""
    skill = agent.skill_registry.get(skill_id)

    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    try:
        result = await agent.execute_skill(skill_id, request.input_text)

        return ProcessResponse(
            success=result.success,
            message=result.message,
            output=result.output,
            skill_used=skill_id,
        )

    except Exception as e:
        logger.error(f"Skill execution error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============== Memory Endpoints ==============

@app.post("/memory/store", tags=["Memory"])
async def store_memory(
    request: MemoryStoreRequest,
    agent: AdaAgent = Depends(get_agent)
):
    """Store a memory"""
    if not agent.memory_store:
        raise HTTPException(status_code=501, detail="Memory not available")

    from ada.memory.base import Memory, MemoryType

    try:
        memory_type = MemoryType(request.type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid memory type: {request.type}")

    memory = Memory(
        content=request.content,
        memory_type=memory_type,
        metadata=request.metadata or {},
        importance=request.importance,
    )

    try:
        memory_id = await asyncio.get_event_loop().run_in_executor(
            None, agent.memory_store.save, memory
        )
        return {"id": memory_id, "success": True}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/memory/search", response_model=List[MemoryResult], tags=["Memory"])
async def search_memory(
    request: MemorySearchRequest,
    agent: AdaAgent = Depends(get_agent)
):
    """Search memories"""
    if not agent.memory_store:
        raise HTTPException(status_code=501, detail="Memory not available")

    from ada.memory.base import MemoryQuery, MemoryType

    types = None
    if request.types:
        try:
            types = [MemoryType(t) for t in request.types]
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    query = MemoryQuery(
        text=request.query,
        limit=request.limit,
        memory_types=types
    )

    try:
        memories = await asyncio.get_event_loop().run_in_executor(
            None, agent.memory_store.search, query
        )

        return [
            MemoryResult(
                id=m.id,
                content=m.content,
                type=m.memory_type.value,
                created_at=m.created_at.isoformat(),
                importance=m.importance,
            )
            for m in memories
        ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/memory/stats", tags=["Memory"])
async def memory_stats(agent: AdaAgent = Depends(get_agent)):
    """Get memory statistics"""
    if not agent.memory_store:
        raise HTTPException(status_code=501, detail="Memory not available")

    from ada.memory.base import MemoryType

    stats = {
        "total": agent.memory_store.count(),
        "by_type": {}
    }

    for mem_type in MemoryType:
        count = agent.memory_store.count(memory_type=mem_type)
        if count > 0:
            stats["by_type"][mem_type.value] = count

    return stats


@app.delete("/memory/{memory_id}", tags=["Memory"])
async def delete_memory(
    memory_id: str,
    agent: AdaAgent = Depends(get_agent)
):
    """Delete a memory"""
    if not agent.memory_store:
        raise HTTPException(status_code=501, detail="Memory not available")

    success = agent.memory_store.delete(memory_id)

    if success:
        return {"success": True}
    else:
        raise HTTPException(status_code=404, detail="Memory not found")


# ============== Status Endpoints ==============

@app.get("/status", response_model=StatusResponse, tags=["Status"])
async def status(agent: AdaAgent = Depends(get_agent)):
    """Get agent status"""
    memory_count = 0
    if agent.memory_store:
        memory_count = agent.memory_store.count()

    return StatusResponse(
        status="running" if agent._initialized else "initializing",
        version="0.1.0",
        mode=agent.context.mode.value,
        skills_count=len(agent.skill_registry),
        memory_count=memory_count,
        uptime_seconds=0.0,  # Would track actual uptime
    )


# ============== Conversation Endpoints ==============

@app.get("/conversation/history", tags=["Conversation"])
async def get_history(
    limit: int = Query(20, ge=1, le=100),
    agent: AdaAgent = Depends(get_agent)
):
    """Get conversation history"""
    history = agent.context.conversation_history[-limit:]

    return {
        "messages": [
            {
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat() if hasattr(msg, 'timestamp') else None
            }
            for msg in history
        ]
    }


@app.delete("/conversation/history", tags=["Conversation"])
async def clear_history(agent: AdaAgent = Depends(get_agent)):
    """Clear conversation history"""
    agent.context.conversation_history.clear()
    return {"success": True}


# ============== WebSocket Endpoint ==============

class ConnectionManager:
    """Manage WebSocket connections"""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass


manager = ConnectionManager()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time communication"""
    await manager.connect(websocket)
    agent = get_agent()

    try:
        while True:
            data = await websocket.receive_text()

            try:
                request = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON"
                })
                continue

            # Handle different message types
            msg_type = request.get("type", "process")

            if msg_type == "process":
                text = request.get("text", "")

                # Send thinking status
                await websocket.send_json({
                    "type": "status",
                    "status": "thinking"
                })

                # Process
                result = await agent.process(text)

                # Send response
                await websocket.send_json({
                    "type": "response",
                    "success": result.success,
                    "message": result.message,
                    "output": result.output,
                    "skill": result.skill_id
                })

            elif msg_type == "ping":
                await websocket.send_json({
                    "type": "pong",
                    "timestamp": datetime.now().isoformat()
                })

            elif msg_type == "subscribe":
                # Subscribe to events
                event_types = request.get("events", [])
                await websocket.send_json({
                    "type": "subscribed",
                    "events": event_types
                })

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


# ============== Events Endpoints ==============

@app.post("/events/emit", tags=["Events"])
async def emit_event(
    event_type: str,
    data: Dict[str, Any],
    agent: AdaAgent = Depends(get_agent)
):
    """Emit a custom event"""
    from ada.events.base import Event

    event = Event.custom(event_type, data)
    await agent.event_bus.publish(event)

    return {"success": True, "event_id": event.id}


# ============== Error Handlers ==============

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=str(exc.detail),
            timestamp=datetime.now().isoformat()
        ).dict()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal server error",
            detail=str(exc),
            timestamp=datetime.now().isoformat()
        ).dict()
    )


# ============== Server ==============

def run_api(host: str = "0.0.0.0", port: int = 8000, reload: bool = False):
    """Run the API server"""
    uvicorn.run(
        "ada.api.main:app",
        host=host,
        port=port,
        reload=reload,
    )


if __name__ == "__main__":
    run_api()
