"""
Project GOZEN - HTTP Server

Consolidated FastAPI implementation for the Project GOZEN orchestrator.
Handles REST API, WebSocket communication, and SPA static file serving.
Integrated with GozenOrchestrator's async generator and Human-in-the-loop flow.
"""

import asyncio
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from gozen.config import SERVER_PORT, SERVER_HOST
from gozen.gozen_orchestrator import GozenOrchestrator

# ============================================================
# WebSocket Manager
# ============================================================

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, session_id: str, websocket: WebSocket):
        await websocket.accept()
        if session_id not in self.active_connections:
            self.active_connections[session_id] = []
        self.active_connections[session_id].append(websocket)

    def disconnect(self, session_id: str, websocket: WebSocket):
        if session_id in self.active_connections:
            if websocket in self.active_connections[session_id]:
                self.active_connections[session_id].remove(websocket)
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]

    async def broadcast(self, session_id: str, message: dict):
        if session_id in self.active_connections:
            for connection in self.active_connections[session_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    print(f"Error broadcasting to session {session_id}: {e}")

manager = ConnectionManager()

# ============================================================
# Global Orchestrator & State
# ============================================================

# We use a single global orchestrator to manage all sessions
orchestrator = GozenOrchestrator()

# ============================================================
# Data Models
# ============================================================

class TaskRequest(BaseModel):
    mission: str
    requirements: List[str] = []
    security_level: Optional[str] = "public"
    plan: Optional[str] = "pro"

class DecisionRequest(BaseModel):
    choice: int

# ============================================================
# Lifecycle & App Setup
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"🏯 Project GOZEN Server starting on http://{SERVER_HOST}:{SERVER_PORT}")
    yield
    print("🏯 Server shutting down...")

app = FastAPI(
    title="Project GOZEN 御前会議",
    version="3.1.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# Background Runner
# ============================================================

async def _orchestration_runner(session_id: str, mission: str):
    """Orchestrator generatorを回してWebSocketにブロードキャストする"""
    try:
        # セッションからセキュリティレベルを取得
        state = orchestrator.sessions.get(session_id)
        sl = state.security_level if state else "public"
        
        async for event in orchestrator.run_council_session(session_id, mission, security_level=sl):
            await manager.broadcast(session_id, event)
    except Exception as e:
        await manager.broadcast(session_id, {"type": "ERROR", "message": f"Runner Error: {str(e)}"})

# ============================================================
# API Endpoints
# ============================================================

@app.get("/api/v1/health")
async def health_check():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

class SessionRequest(BaseModel):
    security_level: str = "public"

@app.post("/api/sessions")
async def api_create_session(request: SessionRequest):
    # Frontend usually calls this to get a session ID before WS
    session_id = f"GOZEN-{str(uuid.uuid4())[:8]}"
    
    # セッション状態を事前作成（セキュリティレベルを保持するため）
    from gozen.council_mode import CouncilSessionState
    orchestrator.sessions[session_id] = CouncilSessionState(
        session_id=session_id,
        mission="",
        security_level=request.security_level
    )
    
    return {"session_id": session_id}

@app.post("/api/sessions/{session_id}/decision")
async def api_submit_decision(session_id: str, request: DecisionRequest):
    """Resume the Orchestrator by setting the future result"""
    state = orchestrator.sessions.get(session_id)
    if not state or not state.current_decision_future:
        raise HTTPException(status_code=400, detail="No active decision pending for this session.")
    
    if not state.current_decision_future.done():
        state.current_decision_future.set_result(request.choice)
        return {"status": "ok", "message": "Decision submitted."}
    return {"status": "error", "message": "Decision already processed."}

@app.post("/api/shutdown")
async def shutdown_server():
    import os, signal, threading, time
    def kill(): time.sleep(1); os.kill(os.getpid(), signal.SIGINT)
    threading.Thread(target=kill).start()
    return {"message": "Server shutting down"}

# ============================================================
# WebSocket
# ============================================================

@app.websocket("/ws/council/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await manager.connect(session_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "START":
                mission = data.get("mission")
                # Trigger the async runner
                asyncio.create_task(_orchestration_runner(session_id, mission))
            
            elif msg_type == "DECISION" or msg_type == "MERGE_DECISION" or msg_type == "PREMORTEM_DECISION":
                # Handle decisions sent via WebSocket as well
                choice = data.get("choice")
                state = orchestrator.sessions.get(session_id)
                if state and state.current_decision_future and not state.current_decision_future.done():
                    state.current_decision_future.set_result(choice)

    except WebSocketDisconnect:
        manager.disconnect(session_id, websocket)

# ============================================================
# Static Files & SPA
# ============================================================

STATIC_DIR = Path(__file__).parent / "web" / "static"

if (STATIC_DIR / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(STATIC_DIR / "assets")), name="assets")

@app.get("/{path:path}")
async def serve_spa(path: str):
    file_path = STATIC_DIR / path
    if file_path.exists() and file_path.is_file(): return FileResponse(file_path)
    index_file = STATIC_DIR / "index.html"
    if index_file.exists(): return FileResponse(index_file)
    return {"error": "Frontend not found"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=SERVER_HOST, port=SERVER_PORT)
