"""
Project GOZEN - 御前会議オーケストレーター

海軍参謀（Claude）と陸軍参謀（Gemini）の建設的対立を通じて、
最高のエンジニアリング決定を導くマルチエージェントシステム。
"""

from __future__ import annotations

import asyncio
import yaml
from datetime import datetime
from pathlib import Path
from typing import Any, Literal, Optional

from gozen.dashboard import get_dashboard
from gozen.kaigun_sanbou import create_proposal as kaigun_create_proposal
from gozen.rikugun_sanbou import create_proposal as rikugun_create_proposal
from gozen.rikugun_sanbou import create_objection as rikugun_create_objection
from gozen.council_mode import (
    CouncilSessionState,
    ArbitrationResult,
    AdoptionJudgment
)
from gozen.shoki import Shoki, ShokiConfig
from gozen.config import get_rank_config


class GozenOrchestrator:
    """
    御前会議統括クラス（非同期ステートマシン版）
    
    役割:
    - 海軍・陸軍への提案/反論指示
    - ステート遷移の管理
    - 書記への記録指示
    """

    def __init__(
        self,
        default_mode: Literal["sequential", "parallel"] = "sequential",
        plan: Literal["pro", "max5x", "max20x"] = "pro",
        council_mode: Literal["council", "execute"] = "council",
        security_level: Optional[str] = None,
    ) -> None:
        self.mode = default_mode
        self.plan = plan
        self.council_mode = council_mode
        self.security_level = security_level
        self.queue_dir = Path(__file__).parent.parent / "queue"
        self.status_dir = Path(__file__).parent.parent / "status"
        self.sessions: dict[str, CouncilSessionState] = {}
        
        # キューディレクトリ作成
        for subdir in ["proposal", "objection", "decision", "execution", "sessions", "notification"]:
            (self.queue_dir / subdir).mkdir(parents=True, exist_ok=True)
            
        # 書記の初期化
        from gozen.config import SecurityLevel
        sl_enum = None
        if security_level:
            try:
                sl_enum = SecurityLevel(security_level)
            except ValueError:
                pass

        shoki_conf = get_rank_config("shoki", sl_enum)
        self.shoki = Shoki(ShokiConfig(
            model=shoki_conf.model,
            backend=shoki_conf.backend.value,
        ), security_level=security_level)

    async def init_session(self, session_id: str, mission: str, task: dict[str, Any]) -> CouncilSessionState:
        """セッション初期化 & 提案内示"""
        state = CouncilSessionState(session_id=session_id, mission=mission)
        state.status = "proposing"
        
        # ダッシュボード初期化
        dashboard = get_dashboard()
        await dashboard.session_start(session_id, mission, self.council_mode)
        
        # 海軍・陸軍による並列提案生成をバックグラウンド実行 (or 呼び出し元でawait)
        # ここではオーケストレーターは状態を返すのみ
        
        return state

    async def step_kaigun_proposal(self, session_id: str, task: dict[str, Any], security_level: Optional[str] = None) -> dict[str, Any]:
        """海軍参謀による提案生成"""
        print(f"\n⚓ [海軍参謀] 提案生成開始: {session_id}")
        from gozen.kaigun_sanbou import KaigunSanbou
        sl = security_level if security_level is not None else task.get("security_level", "public")
        sanbou = KaigunSanbou(security_level=sl)
        kaigun_task = await sanbou.create_proposal(task)
        print(f"✅ [海軍参謀] 提案生成完了")
        self._save_to_queue("proposal", f"{session_id}_kaigun", kaigun_task)
        return kaigun_task

    async def step_rikugun_objection(self, session_id: str, task: dict[str, Any], kaigun_proposal: dict[str, Any], security_level: Optional[str] = None) -> dict[str, Any]:
        """陸軍参謀による異議申し立て"""
        print(f"\n🎖️ [陸軍参謀] 異議生成開始: {session_id}")
        from gozen.rikugun_sanbou import RikugunSanbou
        sl = security_level if security_level is not None else task.get("security_level", "public")
        sanbou = RikugunSanbou(security_level=sl)
        rikugun_task = await sanbou.create_objection(task, kaigun_proposal)
        print(f"✅ [陸軍参謀] 異議生成完了")
        self._save_to_queue("proposal", f"{session_id}_rikugun", rikugun_task)
        return rikugun_task

    async def step_shoki_integration(self, session_id: str, task: dict[str, Any], kaigun_proposal: dict[str, Any], rikugun_proposal: dict[str, Any], security_level: Optional[str] = None) -> dict[str, Any]:
        """書記による統合案（折衷案）作成"""
        sl = security_level if security_level is not None else task.get("security_level", "public")
        from gozen.shoki import Shoki, ShokiConfig
        
        config = ShokiConfig(
            model="mock-model" if sl == "mock" else "gemini-1.5-flash",
            backend="mock" if sl == "mock" else "gemini_api"
        )
        shoki = Shoki(config=config, security_level=sl)
        merge_instruction = task.get("merge_instruction", "双方の利点を活かし統合せよ。")
        merged = await shoki.synthesize(kaigun_proposal, rikugun_proposal, merge_instruction)
        self._save_to_queue("proposal", f"{session_id}_integrated", merged)
        return merged

    async def generate_proposals(self, session_id: str, task: dict[str, Any]) -> dict[str, Any]:
        """海軍・陸軍の提案を生成（モードに応じて並列/直列）- Legacy Wrapper"""
        print(f"\n🏯 [御前会議] 提案生成開始: {session_id} (Mode: {self.mode})")
        
        if self.mode == "sequential":
            kaigun_task = await self.step_kaigun_proposal(session_id, task)
            rikugun_task = await self.step_rikugun_objection(session_id, task, kaigun_task)
        else:
            # 並列生成（既存ロジック・陸軍は独自提案）
            kaigun_task, rikugun_task = await asyncio.gather(
                kaigun_create_proposal(task),
                rikugun_create_proposal(task)
            )
            self._save_to_queue("proposal", f"{session_id}_kaigun", kaigun_task)
            self._save_to_queue("proposal", f"{session_id}_rikugun", rikugun_task)
        
        return {
            "kaigun_proposal": kaigun_task,
            "rikugun_proposal": rikugun_task
        }

    async def run_council_session(self, session_id: str, mission: str, security_level: Optional[str] = "public"):
        """御前会議の PCA サイクルを回す async generator"""
        self.security_level = security_level # クラス全体で共有
        state = CouncilSessionState(session_id=session_id, mission=mission, security_level=security_level)
        self.sessions[session_id] = state # 状態を保持（Future設定のため）
        
        task = {"task_id": session_id, "mission": mission, "requirements": [], "security_level": security_level}
        
        kaigun_proposal = None
        rikugun_objection = None
        
        # ダッシュボード初期化
        from gozen.dashboard import get_dashboard
        dashboard = get_dashboard()
        await dashboard.session_start(session_id, mission, self.council_mode)

        try:
            while state.round <= state.max_rounds:
                # --- 1. Propose (海軍) ---
                yield {"type": "PHASE", "phase": "proposal", "status": "in_progress", "round": state.round}
                
                if kaigun_proposal is None:
                    kaigun_proposal = await self.step_kaigun_proposal(session_id, task)
                
                yield {
                    "type": "PROPOSAL",
                    "round": state.round,
                    "content": kaigun_proposal.get("summary", ""),
                    "fullText": self._format_proposal(kaigun_proposal)
                }

                # --- 2. Challenge (陸軍) ---
                if rikugun_objection is None:
                    yield {"type": "PHASE", "phase": "objection", "status": "in_progress"}
                    rikugun_objection = await self.step_rikugun_objection(session_id, task, kaigun_proposal)
                    yield {
                        "type": "OBJECTION",
                        "round": state.round,
                        "content": rikugun_objection.get("summary", ""),
                        "fullText": self._format_proposal(rikugun_objection)
                    }

                # 書記による記録（ダッシュボード更新）
                await self.shoki.record(kaigun_proposal, rikugun_objection, state.round)

                # --- 3. Arbitrate (国家元首) ---
                options = [
                    {"value": 1, "label": "海軍案を採択", "type": "kaigun"},
                    {"value": 2, "label": "陸軍案を採択", "type": "rikugun"},
                    {"value": 3, "label": "折衷案を作成", "type": "integrate"},
                    {"value": 4, "label": "却下", "type": "reject"},
                ]
                yield {"type": "AWAITING_DECISION", "options": options, "round": state.round}
                
                state.current_decision_future = asyncio.get_running_loop().create_future()
                choice = await state.current_decision_future
                state.current_decision_future = None
                
                if choice == 1: # Adopt Kaigun
                    yield {"type": "decision", "from": "genshu", "content": "裁定: 海軍案を採択"}
                    await self._finalize_session(session_id, kaigun_proposal)
                    yield {"type": "PHASE", "phase": "complete", "status": "success"}
                    return
                elif choice == 2: # Adopt Rikugun
                    yield {"type": "decision", "from": "genshu", "content": "裁定: 陸軍案を採択"}
                    await self._finalize_session(session_id, rikugun_objection)
                    yield {"type": "PHASE", "phase": "complete", "status": "success"}
                    return
                elif choice == 3: # Integrate
                    yield {"type": "decision", "from": "genshu", "content": "裁定: 統合案を作成"}
                    yield {"type": "PHASE", "phase": "merged", "status": "in_progress"}
                    
                    merged = await self.step_shoki_integration(session_id, task, kaigun_proposal, rikugun_objection)
                    yield {
                        "type": "MERGED",
                        "content": merged.get("summary", ""),
                        "fullText": self._format_proposal(merged)
                    }
                    
                    # Wait for merge adoption decision
                    yield {
                        "type": "AWAITING_MERGE_DECISION",
                        "options": [
                            {"value": 1, "label": "折衷案を採用", "type": "adopt"},
                            {"value": 2, "label": "折衷案を却下", "type": "reject"},
                        ]
                    }
                    state.current_decision_future = asyncio.get_running_loop().create_future()
                    merge_choice = await state.current_decision_future
                    state.current_decision_future = None
                    
                    if merge_choice == 1:
                        await self._finalize_session(session_id, merged)
                        yield {"type": "PHASE", "phase": "complete", "status": "success"}
                        return
                    else:
                        # --- Validation Phase (New in Phase 22) ---
                        yield {"type": "PHASE", "phase": "validation", "status": "in_progress"}
                        yield {"type": "info", "from": "system", "content": "折衷案が却下されました。海軍参謀による妥当性検証を開始します。"}
                        
                        validation_proposal = await self._run_validation_logic(merged, kaigun_proposal, rikugun_objection)
                        
                        # 洗練記録
                        await self.shoki.record_refinement(validation_proposal, {"review": "折衷案却下による再調整"})
                        
                        yield {
                            "type": "VALIDATION",
                            "content": validation_proposal.get("summary", ""),
                            "fullText": self._format_proposal(validation_proposal)
                        }
                        
                        if "rejection_history" not in task: task["rejection_history"] = []
                        task["rejection_history"].append({
                            "round": state.round,
                            "rejected_proposal": merged,
                            "reject_reason": "コスト・実現性の懸念により却下"
                        })
                        
                        kaigun_proposal = validation_proposal
                        rikugun_objection = None # Reset objection for the next round
                        state.round += 1
                        yield {"type": "info", "from": "system", "content": f"第 {state.round} 回戦を開始します。"}
                        continue 
                elif choice == 4: # Reject
                    yield {"type": "decision", "from": "genshu", "content": "裁定: 却下（承認せず）"}
                    await dashboard.session_end("failed")
                    yield {"type": "COMPLETE", "result": {"approved": False}}
                    return
                
                state.round += 1

        except Exception as e:
            yield {"type": "ERROR", "message": f"Orchestration Error: {str(e)}"}

    async def _finalize_session(self, session_id: str, adopted_proposal: dict[str, Any]):
        """通達・公文書化"""
        from gozen.dashboard import get_dashboard
        dashboard = get_dashboard()
        await dashboard.phase_update("execution", "completed")
        
        notification = await self.notify_all(session_id, adopted_proposal)
        await dashboard.decision_update("adopted", notification.get("message", "採択通達"))
        
        doc = await self.create_official_document(session_id, notification)
        await dashboard.session_end("completed")

    def _format_proposal(self, proposal: dict[str, Any]) -> str:
        lines = []
        if "title" in proposal: lines.append(f"### {proposal['title']}\n")
        if "summary" in proposal: lines.append(proposal["summary"] + "\n")
        if "key_points" in proposal and proposal["key_points"]:
            lines.append("#### 主要ポイント")
            for point in proposal["key_points"]: lines.append(f"- {point}")
        return "\n".join(lines)

    async def integrate_proposals(
        self, 
        session_id: str,
        kaigun_proposal: dict[str, Any], 
        rikugun_proposal: dict[str, Any],
        instruction: str
    ) -> dict[str, Any]:
        """統合案の作成（書記）"""
        print(f"\n📜 [書記] 統合案起草中: {instruction}")
        
        merged = await self.shoki.synthesize(
            proposal=kaigun_proposal,
            objection=rikugun_proposal,
            merge_instruction=instruction
        )
        
        self._save_to_queue("proposal", f"{session_id}_integrated", merged)
        return merged

    async def notify_all(self, session_id: str, adopted_proposal: dict[str, Any]) -> dict[str, Any]:
        """全軍通達"""
        print(f"\n📢 [全軍通達] {session_id}")
        
        notification = {
            "session_id": session_id,
            "adopted": adopted_proposal,
            "notified_at": datetime.now().isoformat(),
            "message": f"本件、{adopted_proposal.get('from', 'unknown')}案を採択。全軍に通達する。"
        }
        
        self._save_to_queue("notification", session_id, notification)
        return notification

    async def create_official_document(self, session_id: str, notification: dict[str, Any]) -> dict[str, Any]:
        """公文書化"""
        print(f"\n📜 [書記] 公文書作成中: {session_id}")
        
        # セッションからセキュリティレベルを取得
        state = self.sessions.get(session_id)
        sl = state.security_level if state else "public"
        
        from gozen.shoki import Shoki, ShokiConfig
        config = ShokiConfig(
            model="mock-model" if sl == "mock" else "gemini-1.5-flash",
            backend="mock" if sl == "mock" else "gemini_api"
        )
        shoki = Shoki(config=config, security_level=sl)
        doc = await shoki.create_official_document(notification)
        
        # 保存
        self._save_to_queue("decision", f"{session_id}_official", doc)
        return doc

    async def _run_validation_logic(self, merged: dict[str, Any], original_kaigun: dict[str, Any], rikugun_objection: dict[str, Any]) -> dict[str, Any]:
        """折衷案却下時の妥当性検証（海軍参謀による反省と改善）"""
        print(f"\n⚓ [海軍参謀] 折衷案の妥当性検証を開始")
        
        # 妥当性検証用のプロンプト構築
        prompt = (
            "# 折衷案の妥当性検証\n\n"
            "国家元首より折衷案の妥当性検証を命じられました。\n"
            "海軍参謀として、以下の折衷案を検証し、改善提案を行ってください。\n\n"
            f"## 当初の海軍提案\n{original_kaigun.get('summary', 'N/A')}\n\n"
            f"## 陸軍の異議\n{rikugun_objection.get('summary', 'N/A')}\n\n"
            f"## 書記による折衷案（却下済み）\n{merged.get('summary', 'N/A')}\n\n"
            "## 指示\n"
            "折衷案は却下されました。却下理由（コスト・実現性の懸念）を特に重視し、海軍の理想を維持しつつも「大人」な改善案を提示してください。\n"
            "出力は必ず日本語とし、以下のJSON形式で回答してください。\n\n"
            "```json\n"
            "{\n"
            '  "title": "妥当性検証に基づく修正提案",\n'
            '  "summary": "検証結果と改善案の概要（300-500文字）",\n'
            '  "key_points": ["要点1", "要点2", "要点3"]\n'
            "}\n"
            "```"
        )
        
        from gozen.api_client import get_client
        client = get_client("kaigun_sanbou", security_level=self.security_level)
        result = await client.call(prompt)
        content = result.get("content", "")
        
        from gozen.utils.json_parser import parse_llm_json
        parsed = parse_llm_json(content)
        
        if parsed:
            parsed["from"] = "kaigun"
            return parsed
            
        return {
            "title": "妥当性検証修正案（予備）",
            "summary": content,
            "key_points": ["理想と現実の再調整"],
            "from": "kaigun"
        }

    def _save_to_queue(self, queue_type: str, file_id: str, content: dict[str, Any]) -> None:
        """キューにYAML保存"""
        filepath = self.queue_dir / queue_type / f"{file_id}.yaml"
        with open(filepath, "w", encoding="utf-8") as f:
            yaml.dump(content, f, allow_unicode=True, default_flow_style=False)
