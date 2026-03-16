"""
Ada REST API - HTTP API for external integration
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import asyncio
import logging
import uvicorn

from ada.core.context import Agent, AgentConfig

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Ada API",
    description="HTTP API for Ada AI Assistant",
    version="0.1.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global agent instance
_agent: Optional[Agent] = None


def get_agent() -> Agent:
    """Get or create agent instance"""
    global _agent
    if _agent is None:
        config = AgentConfig()
        _agent = Agent(config)
    return _agent


# Request/Response models

class ProcessRequest(BaseModel):
    """Request to process user input"""
    text: str
    context: Optional[Dict[str, Any]] = None
    stream: bool = False


class ProcessResponse(BaseModel):
    """Response from processing"""
    success: bool
    message: str
    output: Optional[Dict[str, Any]] = None
    skill_used: Optional[str] = None


class SkillInfo(BaseModel):
    """Skill information"""
    id: str
    name: str
    description: str
    category: str
    version: str


class MemoryStoreRequest(BaseModel):
    """Request to store memory"""
    content: str
    type: str = "semantic"
    metadata: Optional[Dict[str, Any]] = None


class MemorySearchRequest(BaseModel):
    """Request to search memories"""
    query: str
    limit: int = 10


class StatusResponse(BaseModel):
    """Status response"""
    status: str
    version: str
    mode: str
    skills_count: int


# API Endpoints

@app.get("/")
async def root():
    """Root endpoint"""
    return {"name": "Ada API", "version": "0.1.0"}


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.get("/status", response_model=StatusResponse)
async def status():
    """Get agent status"""
    agent = get_agent()

    return StatusResponse(
        status="running",
        version="0.1.0",
        mode=agent.mode.value if hasattr(agent, 'mode') else "normal",
        skills_count=len(agent._registry) if hasattr(agent, '_registry') else 0,
    )


@app.post("/process", response_model=ProcessResponse)
async def process(request: ProcessRequest):
    """Process user input"""
    agent = get_agent()

    try:
        result = await agent.process(request.text)

        return ProcessResponse(
            success=result.success,
            message=result.message,
            output=result.output,
            skill_used=result.skill_id,
        )

    except Exception as e:
        logger.error(f"Error processing request: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/skills", response_model=List[SkillInfo])
async def list_skills():
    """List available skills"""
    agent = get_agent()

    if not hasattr(agent, '_registry'):
        return []

    skills = []
    for skill in agent._registry.list_skills():
        skills.append(SkillInfo(
            id=skill.metadata.id,
            name=skill.metadata.name,
            description=skill.metadata.description,
            category=skill.metadata.category,
            version=skill.metadata.version,
        ))

    return skills


@app.get("/skills/{skill_id}", response_model=SkillInfo)
async def get_skill(skill_id: str):
    """Get skill information"""
    agent = get_agent()

    if not hasattr(agent, '_registry'):
        raise HTTPException(status_code=404, detail="Skills not loaded")

    metadata = agent._registry.get_skill_metadata(skill_id)
    if not metadata:
        raise HTTPException(status_code=404, detail="Skill not found")

    return SkillInfo(
        id=metadata["id"],
        name=metadata["name"],
        description=metadata["description"],
        category=metadata["category"],
        version=metadata["version"],
    )


@app.post("/skills/{skill_id}/execute", response_model=ProcessResponse)
async def execute_skill(skill_id: str, request: ProcessRequest):
    """Execute a specific skill"""
    agent = get_agent()

    try:
        result = await agent.execute_skill(skill_id, request.text)

        return ProcessResponse(
            success=result.success,
            message=result.message,
            output=result.output,
            skill_used=skill_id,
        )

    except Exception as e:
        logger.error(f"Error executing skill: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/memory/store")
async def store_memory(request: MemoryStoreRequest):
    """Store a memory"""
    agent = get_agent()

    if not hasattr(agent, '_memory'):
        raise HTTPException(status_code=501, detail="Memory not available")

    from ada.memory.base import Memory, MemoryType

    memory = Memory(
        content=request.content,
        memory_type=MemoryType(request.type),
        metadata=request.metadata or {},
    )

    try:
        memory_id = await agent._memory.store(memory)
        return {"id": memory_id, "success": True}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/memory/search")
async def search_memory(request: MemorySearchRequest):
    """Search memories"""
    agent = get_agent()

    if not hasattr(agent, '_memory'):
        raise HTTPException(status_code=501, detail="Memory not available")

    from ada.memory.base import MemoryQuery

    query = MemoryQuery(text=request.query, limit=request.limit)

    try:
        memories = await agent._memory.search(query)
        return {
            "memories": [m.to_dict() for m in memories],
            "count": len(memories),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# WebSocket support for streaming

@app.websocket("/ws")
async def websocket_endpoint(websocket):
    """WebSocket endpoint for real-time communication"""
    await websocket.accept()

    agent = get_agent()

    try:
        while True:
            data = await websocket.receive_text()

            # Process message
            result = await agent.process(data)

            # Send response
            await websocket.send_json({
                "success": result.success,
                "message": result.message,
                "output": result.output,
            })

    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await websocket.close()


def run_api(host: str = "0.0.0.0", port: int = 8000):
    """Run the API server"""
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_api()
