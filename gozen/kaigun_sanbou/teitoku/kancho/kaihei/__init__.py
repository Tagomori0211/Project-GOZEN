"""
海兵（kaihei）- Claude Code 並列

艦長の下で、具体的な実装作業を担当する。
複数の海兵が並列または順次で作業を実行する。
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any


class Kaihei:
    """
    海兵クラス

    役割：
    - 艦長からの作業指示を実行
    - コード実装
    - テスト実行
    """

    def __init__(self, worker_id: int) -> None:
        self.role = "海兵"
        self.worker_id = worker_id
        self.superior = "艦長"

    async def execute(self, work_item: dict[str, Any]) -> dict[str, Any]:
        """作業を実行"""
        from gozen.dashboard import get_dashboard
        dashboard = get_dashboard()
        desc = work_item.get("description", "N/A")

        print(f"[海兵{self.worker_id}] 作業開始: {desc}")
        await dashboard.unit_update("kaigun", "kaihei", str(self.worker_id), "in_progress", desc)

        # 実際の作業をシミュレート
        # 本番ではClaude Code CLIを呼び出す
        await asyncio.sleep(0.1)

        result = {
            "worker_id": self.worker_id,
            "work_item_id": work_item.get("id"),
            "status": "completed",
            "output": f"海兵{self.worker_id}が作業を完了しました",
            "timestamp": datetime.now().isoformat(),
        }

        print(f"[海兵{self.worker_id}] 作業完了")
        await dashboard.unit_update("kaigun", "kaihei", str(self.worker_id), "completed", desc)
        return result


async def execute(worker_id: int, work_item: dict[str, Any]) -> dict[str, Any]:
    """海兵の実行（モジュールレベル関数）"""
    kaihei = Kaihei(worker_id)
    return await kaihei.execute(work_item)
