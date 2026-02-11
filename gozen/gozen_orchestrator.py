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
        default_mode: Literal["sequential", "parallel"] = "parallel",
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

    async def generate_proposals(self, session_id: str, task: dict[str, Any]) -> dict[str, Any]:
        """海軍・陸軍の提案を並列生成"""
        print(f"\n🏯 [御前会議] 提案生成開始: {session_id}")
        
        kaigun_task, rikugun_task = await asyncio.gather(
            kaigun_create_proposal(task),
            rikugun_create_proposal(task)
        )
        
        # キューに保存
        self._save_to_queue("proposal", f"{session_id}_kaigun", kaigun_task)
        self._save_to_queue("proposal", f"{session_id}_rikugun", rikugun_task)
        
        return {
            "kaigun_proposal": kaigun_task,
            "rikugun_proposal": rikugun_task
        }

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
        
        doc = await self.shoki.create_official_document(notification)
        
        # 保存
        self._save_to_queue("decision", f"{session_id}_official", doc)
        return doc

    def _save_to_queue(self, queue_type: str, file_id: str, content: dict[str, Any]) -> None:
        """キューにYAML保存"""
        filepath = self.queue_dir / queue_type / f"{file_id}.yaml"
        with open(filepath, "w", encoding="utf-8") as f:
            yaml.dump(content, f, allow_unicode=True, default_flow_style=False)
