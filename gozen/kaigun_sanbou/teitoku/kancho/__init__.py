"""
艦長（kancho）- Claude Code

提督の下で、戦術指揮と海兵の統制を担当する。
具体的な作業指示を海兵に与える。
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Literal


class Kancho:
    """
    艦長クラス

    役割：
    - 提督からの指令を具体的作業に変換
    - 海兵への詳細指示
    - 品質管理
    """

    def __init__(self) -> None:
        self.role = "艦長"
        self.superior = "提督"
        self.subordinate = "海兵"

    async def execute(
        self,
        subtask: dict[str, Any],
        mode: Literal["sequential", "parallel"] = "sequential",
    ) -> dict[str, Any]:
        """サブタスクを実行"""
        from gozen.dashboard import get_dashboard
        dashboard = get_dashboard()
        await dashboard.unit_update("kaigun", "kancho", "main", "in_progress", subtask["name"])

        print(f"[艦長] 指令受領: {subtask['name']}")

        work_items = self._create_work_items(subtask)

        from gozen.kaigun_sanbou.teitoku.kancho.kaihei import execute as kaihei_execute

        if mode == "parallel":
            results = await asyncio.gather(*[
                kaihei_execute(i, item)
                for i, item in enumerate(work_items)
            ])
        else:
            results = []
            for i, item in enumerate(work_items):
                result = await kaihei_execute(i, item)
                results.append(result)

        await dashboard.unit_update("kaigun", "kancho", "main", "completed")
        return {
            "subtask_id": subtask["id"],
            "status": "completed",
            "work_items_count": len(work_items),
            "results": list(results),
            "timestamp": datetime.now().isoformat(),
        }

    def _create_work_items(self, subtask: dict[str, Any]) -> list[dict[str, Any]]:
        """作業項目を作成"""
        return [
            {
                "id": f"{subtask['id']}-WORK-001",
                "description": f"{subtask['name']} - 実装",
                "estimated_time": "2h",
            },
            {
                "id": f"{subtask['id']}-WORK-002",
                "description": f"{subtask['name']} - テスト",
                "estimated_time": "1h",
            },
        ]


async def execute(subtask: dict[str, Any], mode: str = "sequential") -> dict[str, Any]:
    """艦長の実行（モジュールレベル関数）"""
    kancho = Kancho()
    return await kancho.execute(subtask, mode=mode)
