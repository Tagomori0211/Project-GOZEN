"""
陸軍参謀（rikugun_sanbou）- Gemini

現実・運用・制約適応を重視する参謀。
海軍の提案に対して異議を申し立て、現実的な代替案を提示する。
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Optional


class RikugunSanbou:
    """
    陸軍参謀クラス

    役割：
    - 海軍提案の現実性を検証
    - 運用負荷を考慮した代替案を提示
    - 制約条件（コスト、リソース）を重視

    哲学：
    「泥を啜り、鉄屑を拾い集め、
     海軍の理想を『現実』という地面に杭打ちする。」
    """

    def __init__(self) -> None:
        self.role = "陸軍参謀"
        self.model = "Gemini"
        self.philosophy = "現実・運用・制約適応"
        self.gemini_enabled = bool(os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"))

    async def create_objection(self, task: dict[str, Any], proposal: dict[str, Any]) -> dict[str, Any]:
        """海軍提案に対する異議を作成"""
        mission = task.get("mission", "")

        return {
            "type": "objection",
            "from": "rikugun_sanbou",
            "regarding": proposal.get("title", ""),
            "timestamp": datetime.now().isoformat(),
            "title": f"陸軍異議: {mission[:30]}...",
            "summary": self._generate_objection_summary(task, proposal),
            "concerns": self._identify_concerns(proposal),
            "alternative": self._propose_alternative(task, proposal),
            "key_points": self._extract_key_points(proposal),
            "compromise": self._suggest_compromise(proposal),
        }

    def _generate_objection_summary(self, task: dict[str, Any], proposal: dict[str, Any]) -> str:
        return f"""
【陸軍参謀の異議】

海軍参謀の提案「{proposal.get('title', 'N/A')}」に対し、
以下の懸念を表明する。

・現在の要件に対して過剰設計の可能性
・初期構築コストが高すぎる
・運用負荷が1人体制では厳しい

「陸軍として海軍の提案に反対である」

ただし、段階的アプローチによる折衷案を提案する。
"""

    def _identify_concerns(self, proposal: dict[str, Any]) -> list[dict[str, Any]]:
        return [
            {"category": "過剰設計", "detail": "現在50ユーザーに対してk3sクラスタは過剰", "severity": "high"},
            {"category": "コスト", "detail": "初期構築コスト¥20,000超過の見込み", "severity": "medium"},
            {"category": "運用負荷", "detail": "1人での管理は学習曲線的に困難", "severity": "high"},
            {"category": "複雑性", "detail": "トラブルシューティングが困難", "severity": "medium"},
        ]

    def _propose_alternative(self, task: dict[str, Any], proposal: dict[str, Any]) -> dict[str, Any]:
        return {
            "title": "段階的アプローチ",
            "phase1": {
                "name": "初期段階（現在〜3ヶ月）",
                "approach": "Docker Compose + Ansible",
                "cost": "¥7,000程度",
                "complexity": "低",
            },
            "phase2": {
                "name": "成長段階（3〜6ヶ月）",
                "approach": "k3s移行計画策定",
                "trigger": "ユーザー100人到達時",
            },
            "phase3": {
                "name": "拡大段階（6ヶ月〜）",
                "approach": "海軍案のk3s完全導入",
                "trigger": "ユーザー200人到達時",
            },
        }

    def _extract_key_points(self, proposal: dict[str, Any]) -> list[str]:
        return [
            "現状の要件をまず満たす",
            "段階的な投資でリスク分散",
            "学習曲線を緩やかに",
            "成長に合わせた拡張",
        ]

    def _suggest_compromise(self, proposal: dict[str, Any]) -> dict[str, Any]:
        return {
            "accept_from_kaigun": [
                "Ansibleによる自動化",
                "監視・アラートの完全実装",
                "CI/CDパイプライン",
            ],
            "modify": [
                "k3s → Docker Compose（初期）",
                "Terraform → Ansible単体（初期）",
                "複数ノード → シングルノード（初期）",
            ],
            "defer": [
                "k3sへの移行（3ヶ月後に再検討）",
                "分散MinIO（ユーザー増加時）",
            ],
        }


_instance: Optional[RikugunSanbou] = None


def get_instance() -> RikugunSanbou:
    """陸軍参謀インスタンスを取得"""
    global _instance
    if _instance is None:
        _instance = RikugunSanbou()
    return _instance


async def create_objection(task: dict[str, Any], proposal: dict[str, Any]) -> dict[str, Any]:
    """異議を作成（モジュールレベル関数）"""
    sanbou = get_instance()
    return await sanbou.create_objection(task, proposal)
