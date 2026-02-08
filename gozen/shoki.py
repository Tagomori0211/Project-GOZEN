"""
Project GOZEN - 書記（SHOKI）モジュール

職務:
  - 提案・異議を dashboard.md に構造化記録
  - 両軍の主張を中立的に要約
  - MERGE裁定時に折衷案を起草
  - 却下理由・洗練履歴の追記
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class ShokiConfig:
    """書記設定"""
    model: str
    backend: str
    output_path: Path = field(default_factory=lambda: Path("status/dashboard.md"))


class Shoki:
    """書記クラス - 中立の記録・要約・統合"""

    def __init__(self, config: ShokiConfig) -> None:
        self.config = config
        self.records: list[dict[str, Any]] = []
        self._refinement_records: list[dict[str, Any]] = []

    async def record(
        self,
        proposal: dict[str, Any],
        objection: dict[str, Any],
        iteration: int,
    ) -> None:
        """提案・異議を記録"""
        record = {
            "iteration": iteration,
            "timestamp": datetime.now().isoformat(),
            "proposal_summary": await self._summarize(proposal),
            "objection_summary": await self._summarize(objection),
            "sticking_points": await self._extract_sticking_points(proposal, objection),
        }
        self.records.append(record)
        await self._update_dashboard()

        logger.info(
            "書記記録: iteration=%d, 争点数=%d",
            iteration,
            len(record["sticking_points"]),
        )

    async def record_refinement(
        self,
        refined: dict[str, Any],
        review: dict[str, Any],
    ) -> None:
        """洗練記録を追記"""
        record = {
            "timestamp": datetime.now().isoformat(),
            "refined_summary": await self._summarize(refined),
            "review_summary": await self._summarize(review),
        }
        self._refinement_records.append(record)
        await self._update_dashboard()

    async def synthesize(
        self,
        proposal: dict[str, Any],
        objection: dict[str, Any],
        merge_instruction: str,
    ) -> dict[str, Any]:
        """折衷案を作成"""
        merged = await self._call_llm_synthesize(proposal, objection, merge_instruction)
        return merged

    async def generate_escalation_report(
        self,
        rejection_history: list[dict[str, Any]],
        refinement_history: list[dict[str, Any]],
    ) -> str:
        """エスカレーションレポート生成"""
        sticking_analysis = await self._analyze_sticking_points(rejection_history)
        formatted_history = self._format_rejection_history(rejection_history)

        report = f"""# ESCALATION - 御前会議膠着

## Status: DEADLOCK (iteration {len(rejection_history) + 1})

---

### 膠着原因分析（書記）

本会議は{len(rejection_history)}回のPCAサイクルを経ても合意に至らず。

**収束しなかった争点:**
{sticking_analysis}

**書記所見:**
両軍とも技術的には正当な主張。トレードオフの価値判断が必要であり、
これは国家元首の専権事項と判断。

---

### 却下履歴

{formatted_history}

---

### 元首選択肢

| ACTION | 説明 |
|--------|------|
| `force-kaigun` | 海軍案を強制採択 |
| `force-rikugun` | 陸軍案を強制採択 |
| `manual-merge` | 統合案を手動記述 |
| `split` | タスク分割 |
| `abort` | 本タスク中止 |

```bash
gozen decide --task <TASK_ID> --action <ACTION>
```
"""
        return report

    # =================================================================
    # 内部メソッド
    # =================================================================

    async def _summarize(self, content: dict[str, Any]) -> str:
        """3行要約を生成"""
        # LLMが利用可能な場合はLLMで要約
        # フォールバック: dictの主要フィールドから要約を構成
        if "summary" in content:
            return str(content["summary"])[:200]

        parts = []
        for key in ("title", "description", "key_points", "mission"):
            if key in content:
                val = content[key]
                if isinstance(val, list):
                    parts.append(", ".join(str(v) for v in val[:3]))
                else:
                    parts.append(str(val)[:100])

        return " / ".join(parts) if parts else "(要約なし)"

    async def _extract_sticking_points(
        self,
        proposal: dict[str, Any],
        objection: dict[str, Any],
    ) -> list[dict[str, str]]:
        """争点を抽出"""
        points: list[dict[str, str]] = []

        # 提案のキーポイントと異議のキーポイントを比較
        proposal_points = proposal.get("key_points", [])
        objection_points = objection.get("key_points", objection.get("objections", []))

        if isinstance(proposal_points, list) and isinstance(objection_points, list):
            for i, (pp, op) in enumerate(
                zip(proposal_points, objection_points)
            ):
                points.append({
                    "id": f"SP-{i+1}",
                    "kaigun": str(pp),
                    "rikugun": str(op),
                })

        # LLMで争点を抽出（将来実装）
        if not points:
            points.append({
                "id": "SP-1",
                "kaigun": await self._summarize(proposal),
                "rikugun": await self._summarize(objection),
            })

        return points

    async def _analyze_sticking_points(
        self,
        rejection_history: list[dict[str, Any]],
    ) -> str:
        """却下履歴から争点パターンを分析"""
        if not rejection_history:
            return "(却下履歴なし)"

        lines = []
        for i, entry in enumerate(rejection_history, 1):
            reason = entry.get("reject_reason", "理由不明")
            lines.append(f"{i}. Iteration {entry.get('iteration', '?')}: {reason}")

        return "\n".join(lines)

    def _format_rejection_history(
        self,
        rejection_history: list[dict[str, Any]],
    ) -> str:
        """却下履歴をMarkdownテーブルに整形"""
        if not rejection_history:
            return "(却下履歴なし)"

        lines = [
            "| Iteration | 却下理由 | 海軍提案概要 | 陸軍異議概要 |",
            "|-----------|----------|------------|------------|",
        ]

        for entry in rejection_history:
            it = entry.get("iteration", "?")
            reason = entry.get("reject_reason", "N/A")[:60]

            kaigun = entry.get("kaigun_proposal", {})
            kaigun_summary = kaigun.get("summary", kaigun.get("title", "N/A"))[:40] if isinstance(kaigun, dict) else "N/A"

            rikugun = entry.get("rikugun_objection", {})
            rikugun_summary = rikugun.get("summary", rikugun.get("title", "N/A"))[:40] if isinstance(rikugun, dict) else "N/A"

            lines.append(f"| {it} | {reason} | {kaigun_summary} | {rikugun_summary} |")

        return "\n".join(lines)

    async def _call_llm_synthesize(
        self,
        proposal: dict[str, Any],
        objection: dict[str, Any],
        merge_instruction: str,
    ) -> dict[str, Any]:
        """LLMを使用して統合案を生成"""
        try:
            from gozen.api_client import get_client
            client = get_client("shoki")

            prompt = f"""以下の海軍提案と陸軍異議を統合し、折衷案を作成せよ。

【元首指示】
{merge_instruction}

【海軍提案】
{proposal}

【陸軍異議】
{objection}

【出力形式】
以下のキーを含むYAML形式で出力せよ:
- title: 統合案のタイトル
- summary: 概要（1-2文）
- key_points: 統合されたポイントのリスト
- kaigun_adopted: 海軍案から採用した要素
- rikugun_adopted: 陸軍案から採用した要素
"""
            result = await client.call(prompt)
            content = result.get("content", "")

            # Markdownコードブロックの除去
            cleaned_content = content.replace("```yaml", "").replace("```", "").strip()

            # YAML パース試行
            import yaml
            try:
                parsed = yaml.safe_load(cleaned_content)
                if isinstance(parsed, dict):
                    return parsed
            except yaml.YAMLError:
                pass

            # パースに失敗した場合、テキストとして返す
            return {
                "title": "折衷案（書記起草）",
                "summary": content[:200],
                "raw_content": content,
                "kaigun_elements": proposal.get("key_points", []),
                "rikugun_elements": objection.get("key_points", []),
            }

        except Exception as e:
            logger.warning("LLM統合に失敗、簡易マージにフォールバック: %s", e)
            return {
                "title": "折衷案（簡易マージ）",
                "summary": f"元首指示: {merge_instruction}",
                "kaigun_elements": proposal.get("key_points", []),
                "rikugun_elements": objection.get("key_points", []),
            }

    async def summarize_decision(self, decision: dict[str, Any]) -> dict[str, Any]:
        """裁定結果を構造化データとして返却"""
        try:
            from gozen.api_client import get_client
            client = get_client("shoki")

            adopted_content = decision.get("content", {})
            adopted_type = decision.get("adopted", "unknown")
            reason = decision.get("reason", "")

            # 印鑑ステータスの決定
            seal_status = {
                "kaigun": True,   # 参加済み
                "rikugun": True,  # 参加済み
                "shogun": False   # 元首（これから押印）
            }

            prompt = f"""
あなたは御前会議の書記です。
国家元首の裁定により、以下の案が採択されました。
「裁定通達書」を作成するために必要な情報をJSON形式で出力してください。

【裁定結果】
・採択: {adopted_type}（{'海軍案' if adopted_type == 'kaigun' else '陸軍案' if adopted_type == 'rikugun' else '統合案'}）
・元首コメント: {reason}

【決定内容詳細】
{adopted_content}

【出力JSON形式】
{{
  "decree_text": "決定事項の核心を記述した、感情を排した厳格な『書記官の文体』の文章（3〜5行）。文末は『以上において最終の決を与える。』で締めくくること。",
  "criteria": ["争点1への判断基準", "争点2への判断基準", "コスト対効果の評価"],
  "date": "{datetime.now().strftime('%Y年%m月%d日')}"
}}
"""
            result = await client.call(prompt)
            content = result.get("content", "")

            # JSONパース試行
            import json
            import re
            
            json_str = content
            # コードブロック除去
            if "```json" in content:
                match = re.search(r"```json(.*?)```", content, re.DOTALL)
                if match:
                    json_str = match.group(1)
            elif "```" in content:
                match = re.search(r"```(.*?)```", content, re.DOTALL)
                if match:
                    json_str = match.group(1)

            try:
                data = json.loads(json_str.strip())
            except json.JSONDecodeError:
                # フォールバック
                data = {
                    "decree_text": "決定事項の要約生成に失敗しました。以上において最終の決を与える。",
                    "criteria": ["詳細不明"],
                    "date": datetime.now().strftime('%Y年%m月%d日')
                }

            return {
                "type": "decree",
                "decree_text": data.get("decree_text", ""),
                "criteria": data.get("criteria", []),
                "signatories": seal_status,
                "timestamp": data.get("date", datetime.now().strftime('%Y年%m月%d日')),
                "adopted_type": adopted_type
            }

        except Exception as e:
            logger.error("書記要約失敗（フォールバック）: %s", e)
            print("⚠️ [書記] デバッグモード: APIスキップ - テンプレート裁定を返却")
            
            # 参加者スタンプ状態
            seal_status = {
                "kaigun": True,
                "rikugun": True,
                "shogun": False
            }
            
            # デバッグ用のダミー通達
            is_kaigun = adopted_type == "kaigun"
            return {
                "type": "decree",
                "decree_text": (
                    f"本会議における審議の結果、{'海軍参謀の提案' if is_kaigun else '陸軍参謀の提案' if adopted_type == 'rikugun' else '統合案'}を採用するものとする。\n"
                    "各員においては、直ちに本決定に基づき実行計画を策定し、迅速なる遂行を命じる。\n"
                    "以上において最終の決を与える。"
                ),
                "criteria": [
                    "コスト対効果の最大化",
                    "迅速な展開可能性",
                    "将来の拡張性の確保"
                ],
                "signatories": seal_status,
                "timestamp": datetime.now().strftime('%Y年%m月%d日'),
                "adopted_type": adopted_type
            }

    async def _update_dashboard(self) -> None:
        """dashboard.md に書記記録セクションを更新"""
        try:
            from gozen.dashboard import get_dashboard
            dashboard = get_dashboard()

            for record in self.records[-1:]:  # 最新のみ
                await dashboard.write_council_record(
                    iteration=record["iteration"],
                    proposal_summary=record["proposal_summary"],
                    objection_summary=record["objection_summary"],
                    sticking_points=record["sticking_points"],
                )

            for record in self._refinement_records[-1:]:  # 最新のみ
                await dashboard.write_refinement(
                    iteration=len(self._refinement_records),
                    refined_content=record["refined_summary"],
                    review_content=record["review_summary"],
                )

        except Exception:
            logger.debug("dashboard更新スキップ", exc_info=True)
