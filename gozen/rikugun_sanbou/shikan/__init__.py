"""
士官（shikan）- Gemini API

陸軍参謀の下で、監査とリスク分析を担当する。
歩兵に指令を下し、検証作業を統括する。
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Literal


class Shikan:
    """
    士官クラス

    役割：
    - 陸軍参謀の決定を検証タスクに分解
    - 歩兵への指令書作成
    - リスク分析の監督
    """

    def __init__(self) -> None:
        self.role = "士官"
        self.superior = "陸軍参謀"
        self.subordinate = "歩兵"

    async def execute(
        self,
        decision: dict[str, Any],
        task: dict[str, Any],
        mode: Literal["sequential", "parallel"] = "sequential",
    ) -> dict[str, Any]:
        """決定を検証・実行"""
        from gozen.dashboard import get_dashboard
        dashboard = get_dashboard()
        await dashboard.unit_update("rikugun", "shikan", "main", "in_progress")

        print(f"[士官] 指令受領。検証タスク開始...")

        verification_tasks = self._create_verification_tasks(decision, task)

        from gozen.rikugun_sanbou.shikan.hohei import execute as hohei_execute

        if mode == "parallel":
            results = await asyncio.gather(*[
                hohei_execute(i, vtask)
                for i, vtask in enumerate(verification_tasks)
            ])
        else:
            results = []
            for i, vtask in enumerate(verification_tasks):
                result = await hohei_execute(i, vtask)
                results.append(result)

        await dashboard.unit_update("rikugun", "shikan", "main", "completed")
        return {
            "status": "completed",
            "verification_count": len(verification_tasks),
            "results": list(results),
            "timestamp": datetime.now().isoformat(),
        }

    def _create_verification_tasks(self, decision: dict[str, Any], task: dict[str, Any]) -> list[dict[str, Any]]:
        """検証タスクを作成"""
        return [
            {"id": "VERIFY-001", "name": "コスト検証", "type": "cost_analysis"},
            {"id": "VERIFY-002", "name": "運用負荷検証", "type": "operational_load"},
            {"id": "VERIFY-003", "name": "リスク分析", "type": "risk_analysis"},
            {"id": "VERIFY-004", "name": "代替案評価", "type": "alternative_evaluation"},
        ]


async def execute(
    decision: dict[str, Any],
    task: dict[str, Any],
    mode: str = "sequential",
) -> dict[str, Any]:
    """士官の実行（モジュールレベル関数）"""
    shikan = Shikan()
    return await shikan.execute(decision, task, mode=mode)
