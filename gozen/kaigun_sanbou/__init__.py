"""
海軍参謀（kaigun_sanbou）- Claude

理想・論理・スケーラビリティを重視する参謀。
提案を作成し、国家元首に上申する。
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Optional

from gozen.character import get_character


def _safe_truncate(text: str, max_len: int = 30) -> str:
    """文字列を安全に切り詰める（文字単位）"""
    if len(text) <= max_len:
        return text
    return text[:max_len] + "..."


def _parse_json_response(content: str) -> Optional[dict[str, Any]]:
    """LLMレスポンスからJSONを抽出・パースする（共通ユーティリティを使用）"""
    from gozen.utils.json_parser import parse_llm_json
    return parse_llm_json(content)


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

    def __init__(self, security_level: Optional[str] = None) -> None:
        self.role = "海軍参謀"
        self.model = "Claude"
        self.security_level = security_level
        self.philosophy = "理想・論理・スケーラビリティ"
        self._character = get_character("kaigun_sanbou")

    async def create_proposal(self, task: dict[str, Any]) -> dict[str, Any]:
        """タスクに対する提案を作成"""
        from gozen.dashboard import get_dashboard
        dashboard = get_dashboard()
        await dashboard.unit_update("kaigun", "kaigun_sanbou", "main", "in_progress")

        mission = task.get("mission", "")
        requirements = task.get("requirements", [])
        title = f"海軍提案: {_safe_truncate(mission)}"
        return await self._call_api(mission, requirements, task)
        
        # Debug
        # print("⚠️ [海軍参謀] デバッグモード: APIスキップ")
        # return self._fallback_proposal(mission, task.get("requirements", []), f"海軍提案: {_safe_truncate(mission)}")



    async def _call_api(self, mission: str, requirements: list[str], task: dict[str, Any]) -> dict[str, Any]:
        """APIを呼び出して提案を生成"""
        from gozen.api_client import get_client
        from pathlib import Path

        client = get_client("kaigun_sanbou", security_level=self.security_level)

        # ペルソナプロンプトを読み込む
        prompt_file = Path(__file__).parent.parent.parent / "prompts" / "kaigun_sanbou.prompt"
        if prompt_file.exists():
            with open(prompt_file, "r", encoding="utf-8") as f:
                system_prompt = f.read()
        else:
            system_prompt = ""

        req_str = "\n".join(f"- {r}" for r in requirements) if requirements else "- 未指定"

        # 却下履歴の確認
        rejection_context = ""
        rejection_history = task.get("rejection_history", [])
        if rejection_history:
            last_rejection = rejection_history[-1]
            reason = last_rejection.get("reject_reason", "理由不明")
            merged = task.get("last_merged_proposal", {})
            merged_summary = merged.get("summary", "") if merged else ""

            rejection_context = (
                "\n\n## ⚠️ 重要: 前回の提案は却下されました\n"
                f"却下理由: {reason}\n"
            )
            if merged_summary:
                rejection_context += f"却下された折衷案概要: {merged_summary}\n"
            
            rejection_context += (
                "\n【修正指示】\n"
                "前回の却下理由を真摯に受け止め、より現実的でコスト対効果の高い案を再構築してください。\n"
                "理想を追求しつつも、実現可能性と運用コストを十分に考慮した「大人」な提案が求められます。\n"
            )

        user_prompt = (
            f"{system_prompt}\n\n"
            "以下の任務に対する技術提案を作成してください。\n\n"
            f"## 任務\n{mission}\n\n"
            f"## 要件\n{req_str}"
            f"{rejection_context}\n\n"
            "## 出力形式\n"
            "以下のJSON形式で回答してください。"
            "JSONのみを出力し、他のテキストは含めないでください。\n\n"
            "```json\n"
            "{\n"
            '  "summary": "提案の全体概要（海軍参謀の口調で、300-500文字）",\n'
            '  "architecture": {\n'
            '    "type": "アーキテクチャの種類",\n'
            '    "components": [\n'
            '      {"name": "コンポーネント名", "purpose": "目的"}\n'
            "    ],\n"
            '    "scalability": "スケーラビリティ方針",\n'
            '    "automation_level": "自動化レベル"\n'
            "  },\n"
            '  "key_points": ["要点1", "要点2", "要点3", "要点4"],\n'
            '  "timeline": {\n'
            '    "phase1": "フェーズ1の内容",\n'
            '    "phase2": "フェーズ2の内容",\n'
            '    "phase3": "フェーズ3の内容"\n'
            "  },\n"
            '  "benefits": ["利点1", "利点2", "利点3"],\n'
            '  "risks": ["リスク1", "リスク2", "リスク3"]\n'
            "}\n"
            "```"
        )

        result = await client.call(user_prompt)
        content = result.get("content", "")

        # JSONパース試行
        parsed = _parse_json_response(content)
        if parsed:
            # 必須フィールドの補完
            if "title" not in parsed:
                parsed["title"] = f"海軍提案: {_safe_truncate(mission)}"
            parsed["from"] = "kaigun"
            return parsed

        # JSONパース失敗時はテキスト全体をsummaryとして返す
        print("⚠️ [海軍参謀] JSONパース失敗、テキスト応答をsummaryとして使用")
        return {
            "title": f"海軍提案: {_safe_truncate(mission)}",
            "summary": content,
            "from": "kaigun"
        }

    # ===========================================================
    # フォールバック: テンプレート応答
    # ===========================================================

    def _fallback_proposal(
        self, mission: str, requirements: list[str], title: str
    ) -> dict[str, Any]:
        """API失敗時のテンプレート応答"""
        return {
            "type": "proposal",
            "from": "kaigun_sanbou",
            "timestamp": datetime.now().isoformat(),
            "title": title,
            "summary": self._generate_summary_template(mission, requirements),
            "architecture": self._design_architecture_template(),
            "key_points": self._extract_key_points_template(),
            "timeline": self._estimate_timeline_template(),
            "benefits": self._list_benefits_template(),
            "risks": self._identify_risks_template(),
        }

    def _generate_summary_template(self, mission: str, requirements: list[str]) -> str:
        req_str = ", ".join(requirements) if requirements else "未指定"
        return (
            "【海軍参謀の提案】\n\n"
            f"任務「{mission}」に対し、以下のアーキテクチャを提案いたします。\n\n"
            "・スケーラビリティを最優先\n"
            "・将来の拡張を見据えた設計\n"
            "・完全自動化による運用負荷軽減\n\n"
            f"要件: {req_str}"
        )

    def _design_architecture_template(self) -> dict[str, Any]:
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

    def _extract_key_points_template(self) -> list[str]:
        return [
            "完全自動化による運用負荷ゼロ",
            "将来の200ユーザー対応を想定",
            "Infrastructure as Codeで再現可能性確保",
            "GitOpsによる変更管理",
        ]

    def _estimate_timeline_template(self) -> dict[str, str]:
        return {
            "week1-2": "インフラ基盤構築（k3s + MinIO）",
            "week3": "Terraform コード化",
            "week4": "Ansible 自動化",
            "week5": "テスト・ドキュメント",
            "week6": "本運用移行",
        }

    def _list_benefits_template(self) -> list[str]:
        return [
            "スケーラビリティ無制限",
            "自動フェイルオーバー",
            "GitOpsによる管理",
            "将来の拡張に対応",
        ]

    def _identify_risks_template(self) -> list[str]:
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
