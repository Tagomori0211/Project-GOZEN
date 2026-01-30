"""
海軍参謀（kaigun_sanbou）- Claude

理想・論理・スケーラビリティを重視する参謀。
提案を作成し、国家元首に上申する。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional


class KaigunSanbou:
    """
    海軍参謀クラス

    役割：
    - 理想的なシステム設計を提案
    - スケーラビリティを重視
    - 論理的な根拠を提示

    哲学：
    「美しく壮大な設計図を描く。
     それが実装できるかは陸軍に託す。」
    """

    def __init__(self) -> None:
        self.role = "海軍参謀"
        self.model = "Claude"
        self.philosophy = "理想・論理・スケーラビリティ"

    async def create_proposal(self, task: dict[str, Any]) -> dict[str, Any]:
        """タスクに対する提案を作成"""
        mission = task.get("mission", "")
        requirements = task.get("requirements", [])

        return {
            "type": "proposal",
            "from": "kaigun_sanbou",
            "timestamp": datetime.now().isoformat(),
            "title": f"海軍提案: {mission[:30]}...",
            "summary": self._generate_summary(mission, requirements),
            "architecture": self._design_architecture(mission, requirements),
            "key_points": self._extract_key_points(requirements),
            "timeline": self._estimate_timeline(requirements),
            "benefits": self._list_benefits(),
            "risks": self._identify_risks(),
        }

    def _generate_summary(self, mission: str, requirements: list[str]) -> str:
        req_str = ", ".join(requirements) if requirements else "未指定"
        return f"""
【海軍参謀の提案】

任務「{mission}」に対し、以下のアーキテクチャを提案する。

・スケーラビリティを最優先
・将来の拡張を見据えた設計
・完全自動化による運用負荷軽減

要件: {req_str}
"""

    def _design_architecture(self, mission: str, requirements: list[str]) -> dict[str, Any]:
        return {
            "type": "ideal",
            "components": [
                {"name": "k3s cluster", "purpose": "コンテナオーケストレーション"},
                {"name": "Terraform", "purpose": "Infrastructure as Code"},
                {"name": "Ansible", "purpose": "構成管理・自動化"},
                {"name": "Prometheus/Grafana", "purpose": "監視・可視化"},
                {"name": "GitHub Actions", "purpose": "CI/CD"},
            ],
            "scalability": "horizontal",
            "automation_level": "full",
        }

    def _extract_key_points(self, requirements: list[str]) -> list[str]:
        return [
            "完全自動化による運用負荷ゼロ",
            "将来の200ユーザー対応を想定",
            "Infrastructure as Codeで再現可能性確保",
            "GitOpsによる変更管理",
        ]

    def _estimate_timeline(self, requirements: list[str]) -> dict[str, str]:
        return {
            "week1-2": "インフラ基盤構築（k3s + MinIO）",
            "week3": "Terraform コード化",
            "week4": "Ansible 自動化",
            "week5": "テスト・ドキュメント",
            "week6": "本運用移行",
        }

    def _list_benefits(self) -> list[str]:
        return [
            "スケーラビリティ無制限",
            "自動フェイルオーバー",
            "GitOpsによる管理",
            "将来の拡張に対応",
        ]

    def _identify_risks(self) -> list[str]:
        return [
            "初期構築コストが高い",
            "運用学習曲線が急",
            "過剰設計の可能性",
        ]


_instance: Optional[KaigunSanbou] = None


def get_instance() -> KaigunSanbou:
    """海軍参謀インスタンスを取得"""
    global _instance
    if _instance is None:
        _instance = KaigunSanbou()
    return _instance


async def create_proposal(task: dict[str, Any]) -> dict[str, Any]:
    """提案を作成（モジュールレベル関数）"""
    sanbou = get_instance()
    return await sanbou.create_proposal(task)
