"""
海兵（kaihei）- Claude Code CLI 並列

艦長の下で、具体的な実装作業を担当する。
複数の海兵が並列または順次で作業を実行する。
Claude Code CLI（サブスクリプション枠）経由で実行。
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

# CLI同時実行制限用セマフォ（デフォルト4並列）
_cli_semaphore: asyncio.Semaphore | None = None


def _get_semaphore(max_concurrent: int = 4) -> asyncio.Semaphore:
    """CLI同時実行セマフォを取得（遅延初期化）"""
    global _cli_semaphore
    if _cli_semaphore is None:
        _cli_semaphore = asyncio.Semaphore(max_concurrent)
    return _cli_semaphore


class Kaihei:
    """
    海兵クラス

    役割：
    - 艦長からの作業指示を実行
    - コード実装
    - テスト実行

    Claude Code CLI 経由で実際のLLM呼び出しを行う。
    """

    def __init__(self, worker_id: int) -> None:
        self.role = "海兵"
        self.worker_id = worker_id
        self.superior = "艦長"

    async def execute(self, work_item: dict[str, Any]) -> dict[str, Any]:
        """作業を実行（Claude Code CLI経由）"""
        from gozen.dashboard import get_dashboard
        dashboard = get_dashboard()
        desc = work_item.get("description", "N/A")

        print(f"[海兵{self.worker_id}] 作業開始: {desc}")
        await dashboard.unit_update("kaigun", "kaihei", str(self.worker_id), "in_progress", desc)

        output = await self._call_cli(work_item)

        result = {
            "worker_id": self.worker_id,
            "work_item_id": work_item.get("id"),
            "status": "completed",
            "output": output,
            "timestamp": datetime.now().isoformat(),
        }

        print(f"[海兵{self.worker_id}] 作業完了")
        await dashboard.unit_update("kaigun", "kaihei", str(self.worker_id), "completed", desc)
        return result

    async def _call_cli(self, work_item: dict[str, Any]) -> str:
        """Claude Code CLI を呼び出して作業を実行"""
        from gozen.api_client import get_client
        from gozen.character import get_character

        semaphore = _get_semaphore()

        char = get_character("kaihei")
        system_prompt = (
            f"あなたは「{char.name}（#{self.worker_id}）」です。\n"
            f"{char.intro}\n"
            f"哲学: {char.philosophy}\n\n"
            "あなたの役割は、艦長からの作業指示を実行し、結果を報告することです。\n"
            "簡潔かつ正確に作業を遂行してください。"
        )

        desc = work_item.get("description", "")
        details = work_item.get("details", "")
        prompt = f"## 作業指示\n{desc}\n"
        if details:
            prompt += f"\n## 詳細\n{details}\n"
        prompt += "\n作業を実行し、結果を報告してください。"

        try:
            async with semaphore:
                client = get_client("kaihei")
                result = await client.call(prompt, system=system_prompt)
            return result.get("content", f"海兵{self.worker_id}が作業を完了しました")
        except Exception as e:
            print(f"⚠️ [海兵{self.worker_id}] CLI呼び出し失敗: {e}")
            return f"海兵{self.worker_id}: CLI呼び出し失敗のためフォールバック応答。エラー: {e}"


async def execute(worker_id: int, work_item: dict[str, Any]) -> dict[str, Any]:
    """海兵の実行（モジュールレベル関数）"""
    kaihei = Kaihei(worker_id)
    return await kaihei.execute(work_item)
