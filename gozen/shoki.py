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

    def __init__(self, config: ShokiConfig, security_level: Optional[str] = None) -> None:
        self.config = config
        self.security_level = security_level
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

    def _extract_json_robust(self, text: str) -> Optional[dict[str, Any]]:
        """
        LLMの出力からJSONまたはYAMLを極めて堅牢に抽出する。
        1. Markdownコードブロックを探す (json, yaml, 無し)
        2. 最初の { と 最後の } を探して抽出を試みる
        3. YAMLとしてパースを試みる
        """
        import json
        import re
        import yaml

        # 1. Markdownブロック抽出
        for lang in ['json', 'yaml', '']:
            pattern = rf"```{lang}\s*(.*?)\s*```"
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if match:
                content = match.group(1).strip()
                # 試しにJSONパース
                try:
                    return json.loads(content)
                except:
                    pass
                # 試しにYAMLパース
                try:
                    y = yaml.safe_load(content)
                    if isinstance(y, dict): return y
                except:
                    pass

        # 2. ブレースマッチングによる抽出
        brace_match = re.search(r"(\{.*\})", text, re.DOTALL)
        if brace_match:
            try:
                return json.loads(brace_match.group(1).strip())
            except:
                pass

        # 3. 全体をYAMLとしてパース（最も寛容）
        try:
            # 極端に汚い入力を考慮して不要なプレフィックスを除去
            cleaned = text.strip()
            if cleaned.lower().startswith("json"): cleaned = cleaned[4:].strip()
            if cleaned.lower().startswith("yaml"): cleaned = cleaned[4:].strip()
            
            y = yaml.safe_load(cleaned)
            if isinstance(y, dict): return y
        except:
            pass

        return None

    async def create_official_document(
        self,
        notification: dict[str, Any],
    ) -> dict[str, Any]:
        """公文書を作成"""
        try:
            from gozen.api_client import get_client
            client = get_client("shoki", security_level=self.security_level)
            
            adopted = notification.get("adopted", {})
            session_id = notification.get("session_id", "UNKNOWN")
            
            prompt = f"""
あなたは御前会議の書記官です。
以下の決定事項に基づき、正式な「御前会議決定公文書」を作成してください。
フォーマットはMarkdownとYAMLのハイブリッド形式とします。
絶対に日本語で出力してください。英語は禁止です。

【決定事項】
セッションID: {session_id}
採択案: {adopted.get('title', 'N/A')}
概要: {adopted.get('summary', 'N/A')}
要点: {', '.join(adopted.get('key_points') or (['. '.join(c.get('detail', '') for c in adopted.get('concerns', []))] if 'concerns' in adopted else []))}
決定日時: {notification.get('notified_at', datetime.now().isoformat())}

【出力形式】
JSON形式で出力してください:
{{
  "markdown_content": "# 御前会議 決定公文書\\n\\n...",
  "yaml_content": {{ ...構造化データ... }},
  "filename": "{session_id}_decision.md"
}}
"""
            result = await client.call(prompt)
            content = result.get("content", "")
            
            parsed = self._extract_json_robust(content)
            if parsed and isinstance(parsed, dict) and "markdown_content" in parsed:
                return parsed

            # フォールバック
            return {
                "markdown_content": f"# 御前会議 決定公文書\n\nパース失敗。以下に未加工の出力を記録する。\n\n---\n\n{content}",
                "yaml_content": notification,
                "filename": f"{session_id}_decision_fallback.md"
            }
                
        except Exception as e:
            logger.error(f"公文書作成失敗: {e}")
            return {
                "markdown_content": f"# 御前会議 決定公文書 (System Error)\n\nError: {str(e)}",
                "yaml_content": notification,
                "filename": f"{session_id}_error.md"
            }

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
            client = get_client("shoki", security_level=self.security_level)

            prompt = f"""以下の海軍提案と陸軍異議を統合し、折衷案を作成せよ。
            出力は必ず日本語で行うこと。英語は禁止する。

【元首指示】
{merge_instruction}

【海軍提案】
{proposal}

【陸軍異議】
{objection}

【出力形式】
以下のキーを含むJSONまたはYAML形式で出力せよ:
- title: 統合案のタイトル
- summary: 概要（1-2文）
- key_points: 統合されたポイントのリスト
- kaigun_adopted: 海軍案から採用した要素
- rikugun_adopted: 陸軍案から採用した要素
"""
            result = await client.call(prompt)
            content = result.get("content", "")

            parsed = self._extract_json_robust(content)
            if parsed and isinstance(parsed, dict):
                return parsed

            # パースに失敗した場合、テキストとして返す
            return {
                "title": "統合案（書記起草・パース予備）",
                "summary": content[:200],
                "content": content,
                "key_points": [f"パース失敗、原文を参照してください: {content[:100]}..."],
                "kaigun_adopted": proposal.get("key_points", []),
                "rikugun_adopted": objection.get("key_points", []),
            }

        except Exception as e:
            logger.warning("LLM統合に失敗、簡易マージにフォールバック: %s", e)
            return {
                "title": "折衷案（簡易マージ）",
                "summary": f"元首指示: {merge_instruction}",
                "key_points": proposal.get("key_points", []) + objection.get("key_points", []),
            }

    async def summarize_decision(self, decision: dict[str, Any]) -> dict[str, Any]:
        """裁定結果を構造化データとして返却"""
        try:
            from gozen.api_client import get_client
            client = get_client("shoki", security_level=self.security_level)

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
出力は必ず日本語で行うこと。英語は禁止する。

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

            parsed = self._extract_json_robust(content)
            data = parsed if (parsed and isinstance(parsed, dict)) else {
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
            
            # 参加者スタンプ状態
            seal_status = {
                "kaigun": True,
                "rikugun": True,
                "shogun": False
            }
            
            # デバッグ用のダミー通達
            adopted_type = decision.get("adopted", "unknown") # Ensure adopted_type is defined for fallback
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
