"""
Project GOZEN - HTTP Server

FastAPI implementation for the Project GOZEN orchestrator.
Replaces the legacy CLI interaction with a RESTful API.
"""

import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from gozen.config import SERVER_PORT, SERVER_HOST
from gozen.gozen_orchestrator import GozenOrchestrator
from gozen.council_mode import ArbitrationResult, AdoptionJudgment, CouncilSessionState

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
        proposals = await orch.generate_proposals(session_id, task)
        
        # Update session state
        session["kaigun_proposal"] = proposals["kaigun_proposal"]
        session["rikugun_proposal"] = proposals["rikugun_proposal"]
        session["status"] = "awaiting_arbitration"
        session["updated_at"] = datetime.now().isoformat()
        
        print(f"✅ Proposals ready for session {session_id}")
        
    except Exception as e:
        print(f"❌ Error in proposal phase: {e}")
        session["status"] = "error"
        session["error"] = str(e)

async def _run_integration_phase(session_id: str, instruction: str):
    """Background task to integrate proposals."""
    if session_id not in _orchestrators:
        return

    orch = _orchestrators[session_id]
    session = _sessions[session_id]
    
    try:
        session["status"] = "integrating"
        
        kaigun = session.get("kaigun_proposal")
        rikugun = session.get("rikugun_proposal")
        
        if not kaigun or not rikugun:
            raise ValueError("Proposals not found for integration")

        merged = await orch.integrate_proposals(session_id, kaigun, rikugun, instruction)
        
        session["integrated_proposal"] = merged
        session["status"] = "awaiting_final_approval" # Or back to arbitration? In new flow, it's final approval of doc?
        # Actually simplified: Integrate -> Await Approval of Integrated -> Notify
        # Let's say "awaiting_arbitration" again but with integrated one? 
        # For simplicity, let's say "awaiting_adoption"
        session["status"] = "awaiting_adoption"
        session["updated_at"] = datetime.now().isoformat()
        
    except Exception as e:
        print(f"❌ Error in integration phase: {e}")
        session["status"] = "error"
        session["error"] = str(e)


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
        default_mode="parallel",
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
        
        session["official_document"] = doc
        session["status"] = "completed"
        session["completed_at"] = datetime.now().isoformat()
        
    except Exception as e:
         print(f"❌ Error in notification flow: {e}")
         session["status"] = "error"
         session["error"] = str(e)


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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=SERVER_HOST, port=SERVER_PORT)
