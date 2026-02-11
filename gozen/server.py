"""
Project GOZEN - HTTP Server

FastAPI implementation for the Project GOZEN orchestrator.
Replaces the legacy CLI interaction with a RESTful API.
"""

import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json

from gozen.config import SERVER_PORT, SERVER_HOST
from gozen.gozen_orchestrator import GozenOrchestrator
from gozen.council_mode import ArbitrationResult, AdoptionJudgment, CouncilSessionState

# ============================================================
# WebSocket Manager
# ============================================================

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, session_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[session_id] = websocket

    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]

    async def send_personal_message(self, message: dict, session_id: str):
        if session_id in self.active_connections:
            await self.active_connections[session_id].send_json(message)

    async def broadcast(self, session_id: str, message: dict):
        if session_id in self.active_connections:
            try:
                await self.active_connections[session_id].send_json(message)
            except Exception as e:
                print(f"Error broadcasting to {session_id}: {e}")
                self.disconnect(session_id)

manager = ConnectionManager()

# ============================================================
# Data Models
# ============================================================

class TaskRequest(BaseModel):
    mission: str
    requirements: List[str] = []
    security_level: Optional[str] = "public"
    plan: Optional[str] = "pro"

class ArbitrateRequest(BaseModel):
    decision: str  # "kaigun", "rikugun", "integrate", "reject", "remand"
    reason: Optional[str] = ""
    integration_instruction: Optional[str] = ""

class FinalizeRequest(BaseModel):
    approved: bool
    comment: Optional[str] = ""

# ============================================================
# Server State
# ============================================================

# In-memory session storage (prototype)
_sessions: Dict[str, Any] = {}
_orchestrators: Dict[str, GozenOrchestrator] = {}

async def _run_proposal_phase(session_id: str, task: Dict[str, Any]):
    """Background task to generate proposals."""
    if session_id not in _orchestrators:
        return

    orch = _orchestrators[session_id]
    session = _sessions[session_id]

    try:
        # Notify start of proposal phase
        await manager.broadcast(session_id, {"type": "PHASE", "phase": "proposal", "status": "in_progress"})
        
        # 1. Kaigun Proposal
        if orch.mode == "sequential":
            kaigun_proposal = await orch.step_kaigun_proposal(session_id, task)
             # Broadcast Kaigun Proposal Immediately
            await manager.broadcast(session_id, {
                "type": "PROPOSAL",
                "content": kaigun_proposal.get("summary", ""),
                "fullText": kaigun_proposal.get("content", "")
            })
            session["kaigun_proposal"] = kaigun_proposal

            # Notify objection phase
            await manager.broadcast(session_id, {"type": "PHASE", "phase": "objection", "status": "in_progress"})

            # 2. Rikugun Objection
            rikugun_proposal = await orch.step_rikugun_objection(session_id, task, kaigun_proposal)
            # Broadcast Rikugun Objection
            await manager.broadcast(session_id, {
                "type": "OBJECTION",
                "content": rikugun_proposal.get("summary", ""),
                "fullText": rikugun_proposal.get("content", "")
            })
            session["rikugun_proposal"] = rikugun_proposal
            
        else:
             # Legacy/Parallel Mode (Keep if needed, or remove if unused)
            proposals = await orch.generate_proposals(session_id, task)
            session["kaigun_proposal"] = proposals["kaigun_proposal"]
            session["rikugun_proposal"] = proposals["rikugun_proposal"]
            
            # Broadcast results (simultaneous)
            await manager.broadcast(session_id, {
                "type": "PROPOSAL",
                "content": session["kaigun_proposal"].get("summary", ""),
                "fullText": session["kaigun_proposal"].get("content", "")
            })
            await manager.broadcast(session_id, {
                "type": "OBJECTION",
                "content": session["rikugun_proposal"].get("summary", ""),
                "fullText": session["rikugun_proposal"].get("content", "")
            })

        # Update session state
        session["status"] = "awaiting_arbitration"
        session["status"] = "awaiting_arbitration"
        session["updated_at"] = datetime.now().isoformat()
        
        # Notify ready for decision
        await manager.broadcast(session_id, {
            "type": "AWAITING_DECISION",
            "options": [
                {"value": 1, "label": "海軍案を採択", "type": "kaigun"},
                {"value": 2, "label": "陸軍案を採択", "type": "rikugun"},
                {"value": 3, "label": "折衷案を作成", "type": "integrate"},
                {"value": 4, "label": "却下", "type": "reject"},
            ]
        })
        
        print(f"✅ Proposals ready for session {session_id}")
        
    except Exception as e:
        print(f"❌ Error in proposal phase: {e}")
        session["status"] = "error"
        session["error"] = str(e)
        await manager.broadcast(session_id, {"type": "ERROR", "message": str(e)})

async def _run_integration_phase(session_id: str, instruction: str):
    """Background task to integrate proposals."""
    if session_id not in _orchestrators:
        return

    orch = _orchestrators[session_id]
    session = _sessions[session_id]
    
    try:
        session["status"] = "integrating"
        
        # Genshu's order
        await manager.broadcast(session_id, {
            "type": "info",
            "from": "genshu",
            "content": "両名の意見は理解した。これより書記に命じ、折衷案を作成させる。"
        })

        await manager.broadcast(session_id, {"type": "PHASE", "phase": "merged", "status": "in_progress"})
        
        kaigun = session.get("kaigun_proposal")
        rikugun = session.get("rikugun_proposal")
        
        if not kaigun or not rikugun:
            raise ValueError("Proposals not found for integration")

        merged = await orch.integrate_proposals(session_id, kaigun, rikugun, instruction)
        
        # Broadcast Merged Proposal
        await manager.broadcast(session_id, {
            "type": "MERGED",
            "content": merged.get("summary", ""),
            "fullText": merged.get("content", "")
        })
        
        session["integrated_proposal"] = merged
        session["status"] = "awaiting_adoption"
        session["updated_at"] = datetime.now().isoformat()
        
        # Notify ready for merge decision
        await manager.broadcast(session_id, {
            "type": "AWAITING_MERGE_DECISION",
            "options": [
                {"value": 1, "label": "折衷案を採用", "type": "adopt"},
                {"value": 2, "label": "折衷案を却下", "type": "reject"},
            ]
        })
        
    except Exception as e:
        print(f"❌ Error in integration phase: {e}")
        session["status"] = "error"
        session["error"] = str(e)
        await manager.broadcast(session_id, {"type": "ERROR", "message": str(e)})


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print(f"🏯 Project GOZEN Server starting on port {SERVER_PORT}...")
    yield
    # Shutdown
    print("🏯 Server shutting down...")

app = FastAPI(
    title="Project GOZEN 御前会議",
    version="2.2.0",
    description="API server for Project GOZEN council orchestration.",
    lifespan=lifespan
)

# CORS (Allow all for local development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# Static Files & Web UI
# ============================================================

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

# Static directory path
STATIC_DIR = Path(__file__).parent / "web" / "static"

# Mount /assets if it exists
if (STATIC_DIR / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(STATIC_DIR / "assets")), name="assets")

@app.get("/")
async def serve_spa():
    """Serve the Web UI."""
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "Web UI not found. Please run 'npm run build' in frontend directory."}

# ============================================================
# API Endpoints
# ============================================================

@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

@app.post("/api/v1/council/start")
async def start_council(request: TaskRequest, background_tasks: BackgroundTasks):
    """Start a new council session."""
    task_id = f"GOZEN-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    # Initialize orchestrator for this session
    orchestrator = GozenOrchestrator(
        default_mode="sequential",
        plan=request.plan or "pro",
        council_mode="council",
        security_level=request.security_level
    )
    _orchestrators[task_id] = orchestrator
    
    # Task definition
    task = {
        "task_id": task_id,
        "mission": request.mission,
        "requirements": request.requirements,
        "security_level": request.security_level
    }

    # Initialize session state in memory
    session_data = {
        "session_id": task_id,
        "status": "initializing",
        "mission": request.mission,
        "task": task,
        "created_at": datetime.now().isoformat(),
        "history": []
    }
    _sessions[task_id] = session_data

    # Trigger proposal generation
    background_tasks.add_task(_run_proposal_phase, task_id, task)
    
    return {
        "session_id": task_id,
        "status": "proposing",
        "message": "御前会議開廷。海軍・陸軍に提案を指示しました。"
    }

@app.get("/api/v1/council/{session_id}/status")
async def get_session_status(session_id: str):
    """Get the status of a council session."""
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    return _sessions[session_id]

@app.post("/api/v1/council/{session_id}/arbitrate")
async def arbitrate(session_id: str, request: ArbitrateRequest, background_tasks: BackgroundTasks):
    """Submit an arbitration decision."""
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = _sessions[session_id]
    orch = _orchestrators.get(session_id)
    if not orch:
        raise HTTPException(status_code=500, detail="Orchestrator not found")

    decision_type = request.decision # kaigun, rikugun, integrate, reject
    
    session["last_decision"] = {
        "type": decision_type,
        "reason": request.reason,
        "timestamp": datetime.now().isoformat()
    }

    if decision_type == "integrate":
        # Trigger integration
        if not request.integration_instruction:
            raise HTTPException(status_code=400, detail="Integration instruction required")
        background_tasks.add_task(_run_integration_phase, session_id, request.integration_instruction)
        return {"status": "integrating", "message": "統合案作成を開始しました。"}

    elif decision_type in ["kaigun", "rikugun"]:
        # Adopt one
        adopted_proposal = session.get(f"{decision_type}_proposal")
        if not adopted_proposal:
             raise HTTPException(status_code=400, detail=f"{decision_type} proposal not found")
        
        session["adopted_proposal"] = adopted_proposal
        session["status"] = "notifying"
        
        # In this simplified flow, we go straight to notification -> documentation
        # background_tasks.add_task(orch.notify_all, session_id, adopted_proposal)
        # Actually Notification -> Official Document
        
        background_tasks.add_task(_run_notification_flow, session_id, adopted_proposal)
        
        return {"status": "adopted", "message": f"{decision_type}案を採択しました。公文書作成へ移行します。"}

    elif decision_type == "reject":
        session["status"] = "rejected"
        return {"status": "rejected", "message": "全案却下されました。"}
        
    else:
        raise HTTPException(status_code=400, detail="Invalid decision type")


async def _run_notification_flow(session_id: str, adopted_proposal: Dict[str, Any]):
    if session_id not in _orchestrators:
        return
    orch = _orchestrators[session_id]
    session = _sessions[session_id]
    
    try:
        # 1. Notify
        notification = await orch.notify_all(session_id, adopted_proposal)
        session["notification"] = notification
        
        # 2. Create Document
        session["status"] = "documenting"
        doc = await orch.create_official_document(session_id, notification)
        
        # Broadcast Document (Shoki Summary)
        await manager.broadcast(session_id, {
            "type": "SHOKI_SUMMARY",
            "content": doc 
        })
        
        session["official_document"] = doc
        session["status"] = "completed"
        session["completed_at"] = datetime.now().isoformat()

        # Decide adopted type for frontend
        adopted_type = "kaigun"
        if adopted_proposal == session.get("rikugun_proposal"):
            adopted_type = "rikugun"
        elif adopted_proposal == session.get("integrated_proposal"):
            adopted_type = "integrated"

        # Broadcast Complete
        await manager.broadcast(session_id, {
            "type": "COMPLETE",
            "result": {
                "approved": True,
                "adopted": adopted_type,
                "loop_count": 1 # To implement loop count, we need to track it in session
            }
        })
        
    except Exception as e:
         print(f"❌ Error in notification flow: {e}")
         session["status"] = "error"
         session["error"] = str(e)
         await manager.broadcast(session_id, {"type": "ERROR", "message": str(e)})


@app.get("/api/v1/sessions")
async def list_sessions():
    """List all active sessions."""
    # Convert dict values to list, summary only
    summary_list = []
    for sid, data in _sessions.items():
        summary_list.append({
            "session_id": sid,
            "status": data.get("status"),
            "mission": data.get("mission"),
            "created_at": data.get("created_at")
        })
    return summary_list

@app.post("/api/sessions")
async def create_session():
    """Create a new session (for frontend)."""
    session_id = f"GOZEN-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    _sessions[session_id] = {
        "session_id": session_id,
        "status": "created",
        "created_at": datetime.now().isoformat(),
        "history": []
    }
    return {"session_id": session_id}

@app.post("/api/shutdown")
async def shutdown_server():
    """Shutdown the server."""
    import os, signal
    os.kill(os.getpid(), signal.SIGINT)
    return {"message": "Server shutting down"}

@app.websocket("/ws/council/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await manager.connect(session_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            # Handle client messages
            msg_type = data.get("type")
            
            if msg_type == "START":
                # Start the council
                mission = data.get("mission")
                # Initialize orchestrator if not exists (it shouldn't for new session)
                orchestrator = GozenOrchestrator(
                    default_mode="sequential",
                    plan="pro",
                    council_mode="council"
                )
                _orchestrators[session_id] = orchestrator
                
                task = {
                    "task_id": session_id,
                    "mission": mission,
                    "requirements": [],
                    # security_level defaults to None -> behaves as configured in config.py (usually API)
                }
                _sessions[session_id]["mission"] = mission
                _sessions[session_id]["task"] = task
                _sessions[session_id]["status"] = "proposing"
                
                # We need to run background task from inside WS? 
                # We can use asyncio.create_task
                asyncio.create_task(_run_proposal_phase(session_id, task))
                
            elif msg_type == "DECISION":
                choice = data.get("choice")
                # Map choice ID to decision type
                # 1: kaigun, 2: rikugun, 3: integrate, 4: reject
                decision_map = {1: "kaigun", 2: "rikugun", 3: "integrate", 4: "reject"}
                decision = decision_map.get(choice)
                
                if decision:
                    if decision == "integrate":
                        # For integrate, we need instruction. Frontend should send it?
                        # Frontend DecisionPanel doesn't send instruction for choice 3 directly... 
                        # Wait, the current UI doesn't seem to prompt for instruction for Integrate.
                        # It just sends choice 3.
                        # We'll use a default instruction for now or prompt user?
                        # Since UI is fixed, let's use default "両案の良いとこ取りで"
                        instruction = "双方の利点を活かし、懸念点を解消する形で統合せよ。"

                        # Broadcast the decision itself from Genshu
                        await manager.broadcast(session_id, {
                            "type": "decision",
                            "from": "genshu",
                            "content": "裁定: 統合案を作成"
                        })
                        
                        await manager.broadcast(session_id, {
                            "type": "info", 
                            "from": "genshu", 
                            "content": "統合指示: " + instruction
                        })
                        asyncio.create_task(_run_integration_phase(session_id, instruction))
                        
                    elif decision in ["kaigun", "rikugun"]:
                        # Broadcast the decision itself from Genshu
                        await manager.broadcast(session_id, {
                            "type": "decision",
                            "from": "genshu",
                            "content": f"裁定: {'海軍案を採択' if decision == 'kaigun' else '陸軍案を採択'}"
                        })
                        
                        session = _sessions[session_id]
                        adopted = session.get(f"{decision}_proposal")
                        asyncio.create_task(_run_notification_flow(session_id, adopted))
                        
                    elif decision == "reject":
                         await manager.broadcast(session_id, {
                            "type": "COMPLETE",
                            "result": {"approved": False}
                        })
            
            elif msg_type == "MERGE_DECISION":
                choice = data.get("choice")
                # 1: adopt, 2: reject (force validation? or reject entire?)
                # Code says: 1: '折衷案を採用', 2: '折衷案を却下（妥当性検証へ）'
                
                if choice == 1:
                    session = _sessions[session_id]
                    adopted = session.get("integrated_proposal")
                    asyncio.create_task(_run_notification_flow(session_id, adopted))
                elif choice == 2:
                    # Logic for rejection of merged proposal... 
                    # For now just end as reject
                     await manager.broadcast(session_id, {
                        "type": "COMPLETE",
                        "result": {"approved": False}
                    })

    except WebSocketDisconnect:
        manager.disconnect(session_id)
    except Exception as e:
        print(f"WS Error: {e}")
        manager.disconnect(session_id)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=SERVER_HOST, port=SERVER_PORT)
