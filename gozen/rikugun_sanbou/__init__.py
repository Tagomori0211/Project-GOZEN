"""
陸軍参謀（rikugun_sanbou）- Gemini

現実・運用・制約適応を重視する参謀。
海軍の提案に対して異議を申し立て、現実的な代替案を提示する。
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
    """LLMレスポンスからJSONを抽出・パースする（強化版）"""
    import re
    text = content.strip()

    # 1. マークダウンコードブロックの抽出
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        text = match.group(1)
    else:
        # 2. 最初と最後の波括弧を探す
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            text = text[start : end + 1]

    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return None


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
        self._character = get_character("rikugun_sanbou")

    async def create_proposal(self, task: dict[str, Any]) -> dict[str, Any]:
        """陸軍独自の提案を作成（海軍提案とは独立）"""
        sanbou = get_instance()
        return await sanbou.create_own_proposal(task)

    async def create_own_proposal(self, task: dict[str, Any]) -> dict[str, Any]:
        """海軍とは独立した陸軍独自の提案"""
        from gozen.dashboard import get_dashboard
        dashboard = get_dashboard()
        await dashboard.unit_update("rikugun", "rikugun_sanbou", "main", "in_progress")

        mission = task.get("mission", "")
        return await self._call_proposal_api(mission, task)


    async def create_objection(self, task: dict[str, Any], proposal: dict[str, Any]) -> dict[str, Any]:
        """海軍提案に対する異議を作成（後方互換用）"""
        from gozen.dashboard import get_dashboard
        dashboard = get_dashboard()
        # ... (既存の処理)
        return await self._call_api(task.get("mission", ""), task, proposal)


    async def _call_proposal_api(self, mission: str, task: dict[str, Any]) -> dict[str, Any]:
        """APIを呼び出して独自提案を生成"""
        from gozen.api_client import get_client
        client = get_client("rikugun_sanbou", security_level=task.get("security_level"))
        
        # 必要な情報を抽出
        requirements = task.get("requirements", [])
        req_str = "\n".join(f"- {r}" for r in requirements) if requirements else "- 未指定"

        # ペルソナプロンプト読み込み
        from pathlib import Path
        prompt_file = Path(__file__).parent.parent.parent / "prompts" / "rikugun_sanbou.prompt"
        if prompt_file.exists():
            with open(prompt_file, "r", encoding="utf-8") as f:
                persona_prompt = f.read()
        else:
            persona_prompt = ""

        prompt = (
            f"{persona_prompt}\n\n"
            "# 任務情報\n\n"
            f"## 任務\n{mission}\n\n"
            f"## 要件\n{req_str}\n\n"
            "# 指示\n"
            "上記の任務に対し、陸軍参謀として独自の作戦提案を作成してください。\n"
            "海軍のような理想主義ではなく、現実性、コスト効率、運用負荷の低減を最優先した提案としてください。\n\n"
            "## 出力形式\n"
            "以下のJSON形式で回答してください。\n"
            "JSONのみを出力し、他のテキストは含めないでください。\n\n"
            "```json\n"
            "{\n"
            '  "title": "提案タイトル（陸軍流）",\n'
            '  "summary": "提案の全体概要（陸軍参謀の口調で、300-500文字）",\n'
            '  "approach": "アプローチ手法（Ansible/Docker Composeなど枯れた技術中心）",\n'
            '  "cost_analysis": "概算コスト分析（具体的金額）",\n'
            '  "key_points": ["要点1", "要点2", "要点3", "要点4"],\n'
            '  "risk_assessment": "リスク評価と対策"\n'
            "}\n"
            "```"
        )
        
        result = await client.call(prompt)
        content = result.get("content", "")
        
        parsed = _parse_json_response(content)
        if parsed:
            # 必須フィールドの補完
            parsed["from"] = "rikugun"
            return parsed
            
        print("⚠️ [陸軍参謀] JSONパース失敗、テキスト応答をsummaryとして使用")
        return {"summary": content, "from": "rikugun", "title": "陸軍提案（パース失敗）"}

    async def _call_api(
    # ... (既存のメソッド名変更なし)
        self, mission: str, task: dict[str, Any], proposal: dict[str, Any]
    ) -> dict[str, Any]:
        """APIを呼び出して異議を生成"""
        from gozen.api_client import get_client
        
        security_level = task.get("security_level")
        client = get_client("rikugun_sanbou", security_level)

        char = self._character
        requirements = task.get("requirements", [])
        req_str = "\n".join(f"- {r}" for r in requirements) if requirements else "- 未指定"

        # 海軍提案の要約を構築
        proposal_summary = proposal.get("summary", "不明")
        proposal_key_points = proposal.get("key_points", [])
        proposal_points_str = "\n".join(
            f"- {p}" for p in proposal_key_points
        ) if proposal_key_points else "- 不明"

        # Gemini は system パラメータ未対応のため、プロンプトに統合
        # ペルソナプロンプトを読み込む
        from pathlib import Path
        prompt_file = Path(__file__).parent.parent.parent / "prompts" / "rikugun_sanbou.prompt"
        if prompt_file.exists():
            with open(prompt_file, "r", encoding="utf-8") as f:
                persona_prompt = f.read()
        else:
            persona_prompt = ""

        # ペルソナプロンプト + 議題を組み合わせる
        prompt = (
            f"{persona_prompt}\n\n"
            "# 任務情報\n\n"
            f"## 任務\n{mission}\n\n"
            f"## 要件\n{req_str}\n\n"
            "## 海軍参謀の提案\n"
            f"タイトル: {proposal.get('title', 'N/A')}\n\n"
            f"概要:\n{proposal_summary}\n\n"
            f"要点:\n{proposal_points_str}\n\n"
            "# 指示\n"
            "上記の海軍提案に対する異議と代替案を作成してください。\n\n"
            "## 出力形式\n"
            "以下のJSON形式で回答してください。"
            "JSONのみを出力し、他のテキストは含めないでください。\n\n"
            "```json\n"
            "{\n"
            '  "summary": "異議の全体概要（陸軍参謀の口調で、300-500文字）",\n'
            '  "concerns": [\n'
            '    {"category": "懸念カテゴリ", "detail": "詳細", "severity": "high/medium/low"}\n'
            "  ],\n"
            '  "alternative": {\n'
            '    "title": "代替案のタイトル",\n'
            '    "phase1": {"name": "初期段階", "approach": "手法", "cost": "概算コスト", "complexity": "高/中/低"},\n'
            '    "phase2": {"name": "成長段階", "approach": "手法", "trigger": "移行トリガー"},\n'
            '    "phase3": {"name": "拡大段階", "approach": "手法", "trigger": "移行トリガー"}\n'
            "  },\n"
            '  "key_points": ["要点1", "要点2", "要点3", "要点4"],\n'
            '  "compromise": {\n'
            '    "accept_from_kaigun": ["海軍案から受け入れる点"],\n'
            '    "modify": ["修正を求める点"],\n'
            '    "defer": ["延期を提案する点"]\n'
            "  }\n"
            "}\n"
            "```"
        )

        result = await client.call(prompt)
        content = result.get("content", "")

        # JSONパース試行
        parsed = _parse_json_response(content)
        if parsed:
            return parsed

        # JSONパース失敗時はテキスト全体をsummaryとして返す
        print("⚠️ [陸軍参謀] JSONパース失敗、テキスト応答をsummaryとして使用")
        return {"summary": content}

    # ===========================================================
    # フォールバック: テンプレート応答
    # ===========================================================

    def _fallback_objection(
        self,
        mission: str,
        task: dict[str, Any],
        proposal: dict[str, Any],
        title: str,
    ) -> dict[str, Any]:
        """API失敗時のテンプレート応答"""
        return {
            "type": "objection",
            "from": "rikugun_sanbou",
            "regarding": proposal.get("title", ""),
            "timestamp": datetime.now().isoformat(),
            "title": title,
            "summary": self._generate_objection_summary_template(proposal),
            "concerns": self._identify_concerns_template(),
            "alternative": self._propose_alternative_template(),
            "key_points": self._extract_key_points_template(),
            "compromise": self._suggest_compromise_template(),
        }

    def _generate_objection_summary_template(self, proposal: dict[str, Any]) -> str:
        return (
            "【陸軍参謀の異議】\n\n"
            f"海軍参謀の提案「{proposal.get('title', 'N/A')}」に対し、\n"
            "以下の懸念を表明するであります。\n\n"
            "・現在の要件に対して過剰設計の可能性\n"
            "・初期構築コストが高すぎる\n"
            "・運用負荷が1人体制では厳しい\n\n"
            "「陸軍として海軍の提案に反対であります」\n\n"
            "ただし、段階的アプローチによる折衷案を提案するであります。"
        )

    def _identify_concerns_template(self) -> list[dict[str, Any]]:
        return [
            {"category": "過剰設計", "detail": "現在50ユーザーに対してk3sクラスタは過剰", "severity": "high"},
            {"category": "コスト", "detail": "初期構築コスト¥20,000超過の見込み", "severity": "medium"},
            {"category": "運用負荷", "detail": "1人での管理は学習曲線的に困難", "severity": "high"},
            {"category": "複雑性", "detail": "トラブルシューティングが困難", "severity": "medium"},
        ]

    def _propose_alternative_template(self) -> dict[str, Any]:
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

    def _extract_key_points_template(self) -> list[str]:
        return [
            "現状の要件をまず満たす",
            "段階的な投資でリスク分散",
            "学習曲線を緩やかに",
            "成長に合わせた拡張",
        ]

    def _suggest_compromise_template(self) -> dict[str, Any]:
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


async def create_proposal(task: dict[str, Any]) -> dict[str, Any]:
    """提案を作成（モジュールレベル関数）"""
    sanbou = get_instance()
    return await sanbou.create_proposal(task)


async def create_objection(task: dict[str, Any], proposal: dict[str, Any]) -> dict[str, Any]:
    """異議を作成（モジュールレベル関数）"""
    sanbou = get_instance()
    return await sanbou.create_objection(task, proposal)
