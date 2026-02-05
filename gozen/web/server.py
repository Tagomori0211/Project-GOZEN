"""
Project GOZEN Web Server

FastAPI + WebSocket による御前会議Web Interface。
"""

from __future__ import annotations

import asyncio
import uuid
import webbrowser
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles


class SessionPhase(str, Enum):
    """セッションのフェーズ"""
    IDLE = "idle"
    PROPOSAL = "proposal"
    OBJECTION = "objection"
    MERGED = "merged"
    DECISION = "decision"
    EXECUTION = "execution"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class SessionState:
    """セッション状態"""
    session_id: str
    mission: str = ""
    mode: str = "council"  # "council" or "execute"
    phase: SessionPhase = SessionPhase.IDLE
    proposal: dict[str, Any] | None = None
    objection: dict[str, Any] | None = None
    merged: dict[str, Any] | None = None
    decision: dict[str, Any] | None = None
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at: datetime = field(default_factory=datetime.now)

    # 裁定待ちFuture
    decision_future: asyncio.Future[int] | None = None


# セッション管理
sessions: dict[str, SessionState] = {}
# WebSocket接続管理
connections: dict[str, list[WebSocket]] = {}


def create_app() -> FastAPI:
    """FastAPIアプリケーション作成"""
    app = FastAPI(
        title="Project GOZEN - 御前会議",
        description="海軍参謀 vs 陸軍参謀 マルチエージェント意思決定システム",
        version="0.1.0",
    )

    # 静的ファイル配信（React build）
    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount("/assets", StaticFiles(directory=static_dir / "assets"), name="assets")

    # --- REST API ---

    @app.post("/api/sessions")
    async def create_session() -> dict[str, str]:
        """新規セッション作成"""
        session_id = str(uuid.uuid4())[:8]
        sessions[session_id] = SessionState(session_id=session_id)
        connections[session_id] = []
        return {"session_id": session_id}

    @app.get("/api/sessions/{session_id}")
    async def get_session(session_id: str) -> dict[str, Any]:
        """セッション状態取得"""
        if session_id not in sessions:
            return {"error": "Session not found"}

        state = sessions[session_id]
        return {
            "session_id": state.session_id,
            "mission": state.mission,
            "mode": state.mode,
            "phase": state.phase.value,
            "proposal": state.proposal,
            "objection": state.objection,
            "merged": state.merged,
            "decision": state.decision,
            "result": state.result,
            "error": state.error,
        }

    # --- WebSocket ---

    @app.websocket("/ws/council/{session_id}")
    async def websocket_council(websocket: WebSocket, session_id: str) -> None:
        """会議WebSocket"""
        await websocket.accept()

        # セッション確認/作成
        if session_id not in sessions:
            sessions[session_id] = SessionState(session_id=session_id)
            connections[session_id] = []

        connections[session_id].append(websocket)

        try:
            while True:
                data = await websocket.receive_json()
                await handle_client_message(session_id, data, websocket)
        except WebSocketDisconnect:
            if session_id in connections:
                connections[session_id].remove(websocket)

    # --- 静的ファイル（SPA対応） ---

    @app.get("/{path:path}")
    async def serve_spa(path: str) -> FileResponse:
        """SPAルーティング対応"""
        static_dir = Path(__file__).parent / "static"

        # 具体的なファイルが存在すればそれを返す
        file_path = static_dir / path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)

        # それ以外はindex.htmlを返す（SPAルーティング）
        index_path = static_dir / "index.html"
        if index_path.exists():
            return FileResponse(index_path)

        # index.htmlがない場合はプレースホルダー
        return FileResponse(
            static_dir / "placeholder.html",
            media_type="text/html",
        )

    return app


async def handle_client_message(
    session_id: str,
    data: dict[str, Any],
    websocket: WebSocket,
) -> None:
    """クライアントメッセージ処理"""
    msg_type = data.get("type")
    state = sessions.get(session_id)

    if not state:
        await websocket.send_json({"type": "ERROR", "message": "Session not found"})
        return

    if msg_type == "START":
        # 会議開始
        state.mission = data.get("mission", "")
        state.mode = data.get("mode", "council")

        # 非同期でオーケストレーター実行
        asyncio.create_task(run_council(session_id))

    elif msg_type == "DECISION":
        # 裁定受信
        choice = data.get("choice", 4)
        if state.decision_future and not state.decision_future.done():
            state.decision_future.set_result(choice)


async def broadcast(session_id: str, message: dict[str, Any]) -> None:
    """セッション内の全クライアントにブロードキャスト"""
    if session_id not in connections:
        return

    for ws in connections[session_id]:
        try:
            await ws.send_json(message)
        except Exception:
            pass


async def run_council(session_id: str) -> None:
    """御前会議を実行"""
    state = sessions.get(session_id)
    if not state:
        return

    try:
        from gozen.kaigun_sanbou import create_proposal as kaigun_create_proposal
        from gozen.rikugun_sanbou import create_objection as rikugun_create_objection

        task = {
            "task_id": f"WEB-{session_id}",
            "mission": state.mission,
            "requirements": [],
        }

        # --- 海軍提案 ---
        state.phase = SessionPhase.PROPOSAL
        await broadcast(session_id, {
            "type": "PHASE",
            "phase": "proposal",
            "status": "in_progress",
        })

        proposal = await kaigun_create_proposal(task)
        state.proposal = proposal

        await broadcast(session_id, {
            "type": "PROPOSAL",
            "content": {
                "title": proposal.get("title", ""),
                "summary": proposal.get("summary", ""),
                "key_points": proposal.get("key_points", []),
            },
            "fullText": format_proposal(proposal),
        })

        await broadcast(session_id, {
            "type": "PHASE",
            "phase": "proposal",
            "status": "completed",
        })

        # --- 陸軍異議 ---
        state.phase = SessionPhase.OBJECTION
        await broadcast(session_id, {
            "type": "PHASE",
            "phase": "objection",
            "status": "in_progress",
        })

        objection = await rikugun_create_objection(task, proposal)
        state.objection = objection

        await broadcast(session_id, {
            "type": "OBJECTION",
            "content": {
                "title": objection.get("title", ""),
                "summary": objection.get("summary", ""),
                "key_points": objection.get("key_points", []),
            },
            "fullText": format_proposal(objection),
        })

        await broadcast(session_id, {
            "type": "PHASE",
            "phase": "objection",
            "status": "completed",
        })

        # --- 裁定待ち ---
        state.phase = SessionPhase.DECISION
        await broadcast(session_id, {
            "type": "AWAITING_DECISION",
            "options": [
                {"value": 1, "label": "海軍案を採択"},
                {"value": 2, "label": "陸軍案を採択"},
                {"value": 3, "label": "統合案を作成"},
                {"value": 4, "label": "却下"},
            ],
        })

        # 裁定を待つ
        state.decision_future = asyncio.get_event_loop().create_future()
        choice = await state.decision_future

        # 裁定処理
        merged_content = None
        if choice == 3:
            # 統合案作成
            state.phase = SessionPhase.MERGED
            await broadcast(session_id, {
                "type": "PHASE",
                "phase": "merged",
                "status": "in_progress",
            })

            merged_content = await integrate_proposals(proposal, objection)
            state.merged = merged_content

            await broadcast(session_id, {
                "type": "MERGED",
                "content": {
                    "title": merged_content.get("title", ""),
                    "summary": merged_content.get("summary", ""),
                    "key_points": merged_content.get("key_points", []),
                },
                "fullText": format_proposal(merged_content),
            })

            await broadcast(session_id, {
                "type": "PHASE",
                "phase": "merged",
                "status": "completed",
            })

        # 裁定結果
        decision_map = {
            1: {"approved": True, "adopted": "kaigun", "content": proposal},
            2: {"approved": True, "adopted": "rikugun", "content": objection},
            3: {"approved": True, "adopted": "integrated", "content": merged_content},
            4: {"approved": False, "adopted": None, "content": None},
        }

        decision = decision_map.get(choice, decision_map[4])
        decision["timestamp"] = datetime.now().isoformat()
        state.decision = decision

        # 実行モードの場合
        if state.mode == "execute" and decision.get("approved"):
            state.phase = SessionPhase.EXECUTION
            await broadcast(session_id, {
                "type": "PHASE",
                "phase": "execution",
                "status": "in_progress",
            })

            result = await execute_orders(decision, task, state.mode)
            state.result = result

            await broadcast(session_id, {
                "type": "PHASE",
                "phase": "execution",
                "status": "completed",
            })

        # 完了
        state.phase = SessionPhase.COMPLETED
        await broadcast(session_id, {
            "type": "COMPLETE",
            "result": {
                "approved": decision.get("approved"),
                "adopted": decision.get("adopted"),
                "mode": state.mode,
            },
        })

    except Exception as e:
        state.phase = SessionPhase.ERROR
        state.error = str(e)
        await broadcast(session_id, {
            "type": "ERROR",
            "message": str(e),
        })


async def integrate_proposals(
    proposal: dict[str, Any],
    objection: dict[str, Any],
) -> dict[str, Any]:
    """提案と異議を統合"""
    try:
        from gozen.shoki import Shoki, ShokiConfig
        from gozen.config import get_rank_config

        config = get_rank_config("shoki")
        shoki = Shoki(ShokiConfig(
            model=config.model,
            backend=config.backend.value,
        ))

        merged = await shoki.synthesize(
            proposal,
            objection,
            merge_instruction="海軍の理想と陸軍の現実を統合した折衷案を作成せよ"
        )
        return merged

    except Exception:
        # フォールバック
        return {
            "title": "統合案（簡易マージ）",
            "kaigun_elements": proposal.get("key_points", []),
            "rikugun_elements": objection.get("key_points", []),
            "summary": "海軍の理想と陸軍の現実を統合した折衷案",
        }


async def execute_orders(
    decision: dict[str, Any],
    task: dict[str, Any],
    mode: str,
) -> dict[str, Any]:
    """実行部隊への指令"""
    adopted = decision.get("adopted")

    if adopted == "kaigun":
        from gozen.kaigun_sanbou.teitoku import execute as teitoku_execute
        return await teitoku_execute(decision, task, mode="sequential")

    elif adopted == "rikugun":
        from gozen.rikugun_sanbou.shikan import execute as shikan_execute
        return await shikan_execute(decision, task, mode="sequential")

    else:
        from gozen.kaigun_sanbou.teitoku import execute as teitoku_execute
        from gozen.rikugun_sanbou.shikan import execute as shikan_execute

        kaigun_result, rikugun_result = await asyncio.gather(
            teitoku_execute(decision, task, mode="sequential"),
            shikan_execute(decision, task, mode="sequential"),
        )

        return {
            "kaigun_result": kaigun_result,
            "rikugun_result": rikugun_result,
        }


def format_proposal(proposal: dict[str, Any]) -> str:
    """提案をマークダウン形式でフォーマット"""
    lines = []

    if "title" in proposal:
        lines.append(f"### {proposal['title']}")
        lines.append("")

    if "summary" in proposal:
        lines.append(proposal["summary"])
        lines.append("")

    if "key_points" in proposal and proposal["key_points"]:
        lines.append("#### 主要ポイント")
        for point in proposal["key_points"]:
            lines.append(f"- {point}")
        lines.append("")

    if "reasoning" in proposal:
        lines.append("#### 根拠")
        lines.append(proposal["reasoning"])
        lines.append("")

    return "\n".join(lines) if lines else str(proposal)


def start_server(
    host: str = "127.0.0.1",
    port: int = 8080,
    open_browser: bool = True,
) -> None:
    """サーバー起動"""
    import uvicorn

    # プレースホルダーHTML作成（ビルド前用）
    static_dir = Path(__file__).parent / "static"
    static_dir.mkdir(exist_ok=True)

    placeholder = static_dir / "placeholder.html"
    if not (static_dir / "index.html").exists():
        placeholder.write_text("""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <title>御前会議 - ビルド待ち</title>
    <style>
        body {
            background: #0f172a;
            color: #f8fafc;
            font-family: sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
        }
        .container { text-align: center; }
        h1 { color: #fbbf24; font-size: 3rem; }
        p { color: #94a3b8; }
        code { background: #1e293b; padding: 0.5rem 1rem; border-radius: 4px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>御前会議</h1>
        <p>フロントエンドのビルドが必要です</p>
        <p><code>cd frontend && npm install && npm run build</code></p>
    </div>
</body>
</html>
""", encoding="utf-8")

    if open_browser:
        import threading
        def open_browser_delayed() -> None:
            import time
            time.sleep(1)
            webbrowser.open(f"http://{host}:{port}")
        threading.Thread(target=open_browser_delayed, daemon=True).start()

    app = create_app()
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    start_server()
