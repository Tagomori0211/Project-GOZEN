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
from typing import Any, Callable
from pathlib import Path


from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles


class SessionPhase(str, Enum):
    """セッションのフェーズ"""
    IDLE = "idle"
    PROPOSAL = "proposal"
    OBJECTION = "objection"
    MERGED = "merged"
    MERGE_DECISION = "merge_decision"
    VALIDATION = "validation"
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
    loop_count: int = 0

    # 裁定待ちFuture
    decision_future: asyncio.Future[int] | None = None
    merge_decision_future: asyncio.Future[int] | None = None


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

    elif msg_type == "MERGE_DECISION":
        # 折衷案の採用/却下
        choice = data.get("choice", 2)  # 1=採用, 2=却下
        if state.merge_decision_future and not state.merge_decision_future.done():
            state.merge_decision_future.set_result(choice)


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

        # --- 会議ループ ---
        current_proposal = proposal
        current_objection = objection
        max_loops = 5
        decision = None

        while state.loop_count < max_loops:
            state.loop_count += 1

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
                "loopCount": state.loop_count,
            })

            # 裁定を待つ
            state.decision_future = asyncio.get_event_loop().create_future()
            choice = await state.decision_future

            if choice == 1:
                decision = {"approved": True, "adopted": "kaigun", "content": current_proposal}
                break
            elif choice == 2:
                decision = {"approved": True, "adopted": "rikugun", "content": current_objection}
                break
            elif choice == 3:
                # 統合案作成
                state.phase = SessionPhase.MERGED
                await broadcast(session_id, {
                    "type": "PHASE",
                    "phase": "merged",
                    "status": "in_progress",
                })

                merged_content = await integrate_proposals(current_proposal, current_objection)
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

                # --- 折衷案の採用/却下選択 ---
                state.phase = SessionPhase.MERGE_DECISION
                await broadcast(session_id, {
                    "type": "AWAITING_MERGE_DECISION",
                    "options": [
                        {"value": 1, "label": "採用（承認）"},
                        {"value": 2, "label": "却下（妥当性検証へ）"},
                    ],
                })

                state.merge_decision_future = asyncio.get_event_loop().create_future()
                merge_choice = await state.merge_decision_future

                print(f"DEBUG: Merge choice received: {merge_choice}")

                if merge_choice == 1:
                    # 採用 - 承認スタンプ
                    await broadcast(session_id, {
                        "type": "APPROVED_STAMP",
                    })
                    decision = {"approved": True, "adopted": "integrated", "content": merged_content}
                    break
                else:
                    # 却下 - 妥当性検証ループ
                    print("DEBUG: Merge rejected, starting validation loop")
                    state.phase = SessionPhase.VALIDATION
                    await broadcast(session_id, {
                        "type": "PHASE",
                        "phase": "validation",
                        "status": "in_progress",
                    })

                    await broadcast(session_id, {
                        "type": "INFO",
                        "from": "system",
                        "content": "折衷案が却下されました。海軍参謀による妥当性検証を開始します。",
                    })

                    # 海軍による妥当性検証
                    validation_result = await validate_merged_proposal(
                        merged_content, current_proposal, current_objection
                    )

                    await broadcast(session_id, {
                        "type": "VALIDATION",
                        "content": {
                            "title": validation_result.get("title", ""),
                            "summary": validation_result.get("summary", ""),
                            "key_points": validation_result.get("key_points", []),
                        },
                        "fullText": format_proposal(validation_result),
                    })

                    await broadcast(session_id, {
                        "type": "PHASE",
                        "phase": "validation",
                        "status": "completed",
                    })

                    # 新たな提案として設定
                    current_proposal = validation_result

                    # 陸軍の再検討
                    state.phase = SessionPhase.OBJECTION
                    await broadcast(session_id, {
                        "type": "PHASE",
                        "phase": "objection",
                        "status": "in_progress",
                    })

                    current_objection = await rikugun_create_objection(
                        {"mission": validation_result.get("summary", ""), "requirements": []},
                        validation_result
                    )
                    state.objection = current_objection

                    await broadcast(session_id, {
                        "type": "OBJECTION",
                        "content": {
                            "title": current_objection.get("title", ""),
                            "summary": current_objection.get("summary", ""),
                            "key_points": current_objection.get("key_points", []),
                        },
                        "fullText": format_proposal(current_objection),
                    })

                    await broadcast(session_id, {
                        "type": "PHASE",
                        "phase": "objection",
                        "status": "completed",
                    })

                    await broadcast(session_id, {
                        "type": "INFO",
                        "from": "system",
                        "content": f"会議ループ {state.loop_count} 回目: 再度裁定をお願いいたします。",
                    })
                    continue

            else:  # choice == 4 or invalid
                # 却下 - 再提案ループ
                state.phase = SessionPhase.PROPOSAL
                await broadcast(session_id, {
                    "type": "INFO",
                    "from": "system",
                    "content": "案が却下されました。海軍参謀による再提案を作成します（コスト・実現性重視）。",
                })

                # 却下履歴追加
                if "rejection_history" not in task:
                    task["rejection_history"] = []
                
                task["rejection_history"].append({
                    "iteration": state.loop_count,
                    "kaigun_proposal": current_proposal,
                    "rikugun_objection": current_objection,
                    "reject_reason": "全体的な見直しが必要（コスト・実現性）",
                })

                # 海軍再提案
                await broadcast(session_id, {
                    "type": "PHASE",
                    "phase": "proposal",
                    "status": "in_progress",
                })
                
                current_proposal = await kaigun_create_proposal(task)
                state.proposal = current_proposal

                await broadcast(session_id, {
                    "type": "PROPOSAL",
                    "content": {
                        "title": current_proposal.get("title", ""),
                        "summary": current_proposal.get("summary", ""),
                        "key_points": current_proposal.get("key_points", []),
                    },
                    "fullText": format_proposal(current_proposal),
                })
                
                await broadcast(session_id, {
                    "type": "PHASE",
                    "phase": "proposal",
                    "status": "completed",
                })

                # 陸軍再異議
                state.phase = SessionPhase.OBJECTION
                await broadcast(session_id, {
                    "type": "PHASE",
                    "phase": "objection",
                    "status": "in_progress",
                })

                current_objection = await rikugun_create_objection(task, current_proposal)
                state.objection = current_objection

                await broadcast(session_id, {
                    "type": "OBJECTION",
                    "content": {
                        "title": current_objection.get("title", ""),
                        "summary": current_objection.get("summary", ""),
                        "key_points": current_objection.get("key_points", []),
                    },
                    "fullText": format_proposal(current_objection),
                })

                await broadcast(session_id, {
                    "type": "PHASE",
                    "phase": "objection",
                    "status": "completed",
                })

                continue

        if decision is None:
            decision = {"approved": False, "adopted": None, "content": None, "reason": "max_loops_reached"}

        print(f"DEBUG: Decision reached: {decision}")

        decision["timestamp"] = datetime.now().isoformat()
        decision["loop_count"] = state.loop_count
        state.decision = decision

        if decision.get("approved"):
            # --- 書記による要約 ---
            try:
                print("DEBUG: Calling Shoki summarize_decision...")
                from gozen.shoki import Shoki, ShokiConfig
                from gozen.config import get_rank_config
                config = get_rank_config("shoki")
                shoki = Shoki(ShokiConfig(
                    model=config.model,
                    backend=config.backend.value,
                ))
                
                await broadcast(session_id, {
                    "type": "INFO",
                    "from": "shoki",
                    "content": "書記が決定事項の通達文を作成中...",
                })
                
                summary_text = await shoki.summarize_decision(decision)
                print(f"DEBUG: Shoki summary received: {summary_text}")
                
                await broadcast(session_id, {
                    "type": "SHOKI_SUMMARY",
                    "content": summary_text,
                })
                print("DEBUG: SHOKI_SUMMARY broadcasted")
                
            except Exception as e:
                print(f"書記要約エラー: {e}")
                import traceback
                traceback.print_exc()

        # 完了
        state.phase = SessionPhase.COMPLETED
        await broadcast(session_id, {
            "type": "COMPLETE",
            "result": {
                "approved": decision.get("approved"),
                "adopted": decision.get("adopted"),
                "mode": state.mode,
                "loop_count": state.loop_count,
            },
        })

    except Exception as e:
        state.phase = SessionPhase.ERROR
        state.error = str(e)
        await broadcast(session_id, {
            "type": "ERROR",
            "message": str(e),
        })


async def validate_merged_proposal(
    merged: dict[str, Any],
    original_proposal: dict[str, Any],
    objection: dict[str, Any],
) -> dict[str, Any]:
    """海軍参謀による折衷案の妥当性検証"""
    try:
        # デバッグ: 強制的にフォールバック
        raise Exception("Debug mode")
        from gozen.api_client import get_client

        client = get_client("kaigun_sanbou")

        # ペルソナプロンプトを読み込む
        prompt_file = Path(__file__).parent.parent.parent / "prompts" / "kaigun_sanbou.prompt"
        if prompt_file.exists():
            with open(prompt_file, "r", encoding="utf-8") as f:
                persona_prompt = f.read()
        else:
            persona_prompt = ""

        prompt = (
            f"{persona_prompt}\n\n"
            "# 折衷案の妥当性検証\n\n"
            "国家元首より折衷案の妥当性検証を命じられました。\n"
            "海軍参謀として、以下の折衷案を検証し、改善提案を行ってください。\n\n"
            f"## 当初の海軍提案\n{original_proposal.get('summary', 'N/A')}\n\n"
            f"## 陸軍の異議\n{objection.get('summary', 'N/A')}\n\n"
            f"## 書記の折衷案\n{merged.get('summary', 'N/A')}\n\n"
            "## 指示\n"
            "折衷案は却下されました。却下理由（主にコスト・実現性）を踏まえ、改善案を提示してください。\n"
            "特に「現実的なコスト感覚」と「実現可能性」を重視してください。\n"
            "海軍の理想を維持しつつも、陸軍の懸念（コスト・リソース）に十分配慮した「大人」な修正案を作成してください。\n\n"
            "## 出力形式\n"
            "以下のJSON形式で回答してください。\n\n"
            "```json\n"
            "{\n"
            '  "summary": "修正提案の概要（300-500文字）",\n'
            '  "validation": {"issues": ["問題点1", "問題点2"], "improvements": ["改善点1", "改善点2"]},\n'
            '  "key_points": ["要点1", "要点2", "要点3"]\n'
            "}\n"
            "```"
        )

        result = await client.call(prompt)
        content = result.get("content", "")

        # JSONパース
        import json
        text = content.strip()
        if "```json" in text:
            start = text.index("```json") + 7
            end = text.index("```", start)
            text = text[start:end].strip()
        elif "```" in text:
            start = text.index("```") + 3
            end = text.index("```", start)
            text = text[start:end].strip()

        try:
            parsed = json.loads(text)
            return {
                "type": "validation",
                "from": "kaigun_sanbou",
                "title": "折衷案妥当性検証",
                **parsed,
            }
        except (json.JSONDecodeError, ValueError):
            return {
                "type": "validation",
                "from": "kaigun_sanbou",
                "title": "折衷案妥当性検証",
                "summary": content,
                "key_points": [],
            }

    except Exception as e:
        return {
            "type": "validation",
            "from": "kaigun_sanbou",
            "title": "折衷案妥当性検証（フォールバック）",
            "summary": f"折衷案には改善の余地があります。海軍の理想と陸軍の現実のバランスを再検討する必要があります。エラー: {e}",
            "key_points": ["理想と現実のバランス", "段階的実装の検討", "コスト効率の改善"],
        }


async def integrate_proposals(
    proposal: dict[str, Any],
    objection: dict[str, Any],
) -> dict[str, Any]:
    """提案と異議を統合"""
    try:
        # デバッグ: 強制的にフォールバック
        raise Exception("Debug mode")
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
