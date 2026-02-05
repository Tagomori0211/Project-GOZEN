"""
Project GOZEN - 御前会議オーケストレーター

海軍参謀（Claude）と陸軍参謀（Gemini）の建設的対立を通じて、
最高のエンジニアリング決定を導くマルチエージェントシステム。
"""

from __future__ import annotations

import asyncio
import yaml
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from gozen.dashboard import get_dashboard
from gozen.kaigun_sanbou import create_proposal as kaigun_create_proposal
from gozen.rikugun_sanbou import create_objection as rikugun_create_objection


class GozenOrchestrator:
    """
    御前会議統括クラス

    国家元首（人間）の裁定の下、
    海軍参謀と陸軍参謀の対立を調停する。
    """

    def __init__(
        self,
        default_mode: Literal["sequential", "parallel"] = "sequential",
        plan: Literal["pro", "max5x", "max20x"] = "pro",
        council_mode: Literal["council", "execute"] = "council",
    ) -> None:
        self.mode = default_mode
        self.plan = plan
        self.council_mode = council_mode
        self.queue_dir = Path(__file__).parent.parent / "queue"
        self.status_dir = Path(__file__).parent.parent / "status"

        for subdir in ["proposal", "objection", "decision", "execution"]:
            (self.queue_dir / subdir).mkdir(parents=True, exist_ok=True)

    async def execute_full_cycle(self, task: dict[str, Any]) -> dict[str, Any]:
        """御前会議の完全サイクルを実行"""
        task_id = task.get("task_id", f"TASK-{datetime.now().strftime('%Y%m%d%H%M%S')}")
        dashboard = get_dashboard()
        mission = task.get("mission", "")

        await dashboard.session_start(task_id, mission, self.council_mode)

        print(f"\n🏯 御前会議開始: {task_id}")
        print("=" * 60)

        # --- 海軍提案 ---
        await dashboard.phase_update("proposal", "in_progress")
        print("\n🌊 [海軍参謀] 提案作成中...")
        proposal = await kaigun_create_proposal(task)
        self._save_to_queue("proposal", task_id, proposal)
        print(f"   提案完了: {proposal.get('title', 'N/A')}")
        # 参謀レベルは提案全文を dashboard に記録
        proposal_text = self._format_proposal(proposal)
        await dashboard.proposal_update("completed", proposal_text)
        await dashboard.phase_update("proposal", "completed")

        # --- 陸軍異議 ---
        await dashboard.phase_update("objection", "in_progress")
        print("\n🪖 [陸軍参謀] 異議検討中...")
        objection = await rikugun_create_objection(task, proposal)
        self._save_to_queue("objection", task_id, objection)
        print(f"   異議完了: {objection.get('title', 'N/A')}")
        # 参謀レベルは異議全文を dashboard に記録
        objection_text = self._format_proposal(objection)
        await dashboard.objection_update("completed", objection_text)
        await dashboard.phase_update("objection", "completed")

        # --- 裁定 ---
        await dashboard.phase_update("decision", "in_progress")
        print("\n👑 [国家元首] 裁定をお待ちしています...")
        print("-" * 60)
        print("【海軍の主張】")
        print(f"  {proposal.get('summary', 'N/A')}")
        print("\n【陸軍の異議】")
        print(f"  {objection.get('summary', 'N/A')}")
        print("-" * 60)

        decision = await self._wait_for_decision(task_id, proposal, objection)
        self._save_to_queue("decision", task_id, decision)

        adopted = decision.get("adopted", "")
        choice_labels = {
            "kaigun": "海軍案を採択",
            "rikugun": "陸軍案を採択",
            "integrated": "統合案を作成",
        }
        await dashboard.decision_update(
            choice_labels.get(adopted, "却下"), adopted or "none"
        )
        await dashboard.phase_update("decision", "completed")

        if decision.get("approved"):
            if self.council_mode == "execute":
                await dashboard.phase_update("execution", "in_progress")
                print("\n⚔️ [実行部隊] 指令開始...")
                execution_result = await self._execute_orders(decision, task)
                self._save_to_queue("execution", task_id, execution_result)
                await dashboard.phase_update("execution", "completed")
                await dashboard.session_end("completed")
                return {
                    "status": "completed",
                    "mode": "execute",
                    "task_id": task_id,
                    "decision": decision,
                    "result": execution_result,
                }
            else:
                print("\n📜 裁定完了。実行部隊の展開はありません。")
                await dashboard.session_end("decided")
                return {
                    "status": "decided",
                    "mode": "council",
                    "task_id": task_id,
                    "decision": decision,
                    "result": None,
                }

        await dashboard.session_end("rejected")
        return {
            "status": "rejected",
            "mode": self.council_mode,
            "task_id": task_id,
            "decision": decision,
            "result": None,
        }

    async def _wait_for_decision(
        self,
        task_id: str,
        proposal: dict[str, Any],
        objection: dict[str, Any],
    ) -> dict[str, Any]:
        """国家元首の裁定を待つ"""
        current_proposal = proposal
        current_objection = objection
        loop_count = 0
        max_loops = 5  # 無限ループ防止

        while loop_count < max_loops:
            loop_count += 1

            print("\n選択肢:")
            print("  [1] 海軍案を採択")
            print("  [2] 陸軍案を採択")
            print("  [3] 統合案を作成（書記が起草）")
            print("  [4] 却下")

            try:
                choice = input("\n裁定を入力 (1-4): ").strip()
            except EOFError:
                choice = "4"

            if choice == "1":
                decision = {"approved": True, "adopted": "kaigun", "content": current_proposal}
                break
            elif choice == "2":
                decision = {"approved": True, "adopted": "rikugun", "content": current_objection}
                break
            elif choice == "3":
                # 統合案作成
                integrated_content = await self._integrate(current_proposal, current_objection)

                print("\n" + "=" * 60)
                print("📜 【折衷案】")
                print(f"  {integrated_content.get('summary', 'N/A')}")
                print("=" * 60)

                # 折衷案の採用/却下を選択
                print("\n折衷案の裁定:")
                print("  [1] 採用（承認）")
                print("  [2] 却下（妥当性検証へ）")

                try:
                    merge_choice = input("\n裁定を入力 (1-2): ").strip()
                except EOFError:
                    merge_choice = "2"

                if merge_choice == "1":
                    # 採用 - 承認スタンプ
                    print("\n" + "=" * 60)
                    print("　　　┏━━━━━━━━━━━━━━━━━━┓")
                    print("　　　┃　　　　　　　　　　　　　　　　┃")
                    print("　　　┃　　　　承　　認　　　　┃")
                    print("　　　┃　　　　　　　　　　　　　　　　┃")
                    print("　　　┗━━━━━━━━━━━━━━━━━━┛")
                    print("=" * 60)
                    decision = {"approved": True, "adopted": "integrated", "content": integrated_content}
                    break
                else:
                    # 却下 - 妥当性検証ループ
                    print("\n⚓ [海軍参謀] 折衷案の妥当性を検証中...")
                    validation_result = await self._validate_merged_proposal(
                        integrated_content, current_proposal, current_objection
                    )

                    print(f"\n🌊 [海軍参謀] 妥当性検証結果:")
                    print(f"  {validation_result.get('summary', 'N/A')}")

                    # 検証結果を新たな提案として会議を継続
                    current_proposal = validation_result
                    print("\n🪖 [陸軍参謀] 再検討中...")
                    current_objection = await rikugun_create_objection(
                        {"mission": validation_result.get("summary", ""), "requirements": []},
                        validation_result
                    )
                    print(f"  {current_objection.get('summary', 'N/A')}")

                    print("\n👑 [国家元首] 再度裁定をお待ちしています...")
                    print("-" * 60)
                    print("【海軍の主張（修正案）】")
                    print(f"  {current_proposal.get('summary', 'N/A')}")
                    print("\n【陸軍の異議】")
                    print(f"  {current_objection.get('summary', 'N/A')}")
                    print("-" * 60)
                    continue

            else:  # choice == "4" or invalid
                decision = {"approved": False, "adopted": None, "content": None}
                break

        decision["task_id"] = task_id
        decision["timestamp"] = datetime.now().isoformat()
        decision["loop_count"] = loop_count

        return decision

    async def _validate_merged_proposal(
        self,
        merged: dict[str, Any],
        original_proposal: dict[str, Any],
        objection: dict[str, Any],
    ) -> dict[str, Any]:
        """海軍参謀による折衷案の妥当性検証"""
        try:
            from gozen.api_client import get_client
            from pathlib import Path

            client = get_client("kaigun_sanbou")

            # ペルソナプロンプトを読み込む
            prompt_file = Path(__file__).parent / "prompts" / "kaigun_sanbou.prompt"
            if prompt_file.exists():
                with open(prompt_file, "r", encoding="utf-8") as f:
                    persona_prompt = f.read()
            else:
                persona_prompt = ""

            prompt = (
                f"{persona_prompt}\n\n"
                "# 折衷案の妥当性検証\n\n"
                "国家元首より折衷案の妥当性検証を命じられました。\n"
                "海軍参謀として、以下の折衷案を検証し、改善提案を行ってください。\n\n"
                f"## 当初の海軍提案\n{original_proposal.get('summary', 'N/A')}\n\n"
                f"## 陸軍の異議\n{objection.get('summary', 'N/A')}\n\n"
                f"## 書記の折衷案\n{merged.get('summary', 'N/A')}\n\n"
                "## 指示\n"
                "折衷案の問題点を指摘し、改善案を提示してください。\n"
                "海軍の理想を維持しつつ、陸軍の懸念に応える修正案を作成してください。\n\n"
                "## 出力形式\n"
                "以下のJSON形式で回答してください。\n\n"
                "```json\n"
                "{\n"
                '  "summary": "修正提案の概要（300-500文字）",\n'
                '  "validation": {"issues": ["問題点1", "問題点2"], "improvements": ["改善点1", "改善点2"]},\n'
                '  "key_points": ["要点1", "要点2", "要点3"]\n'
                "}\n"
                "```"
            )

            result = await client.call(prompt)
            content = result.get("content", "")

            # JSONパース
            import json
            text = content.strip()
            if "```json" in text:
                start = text.index("```json") + 7
                end = text.index("```", start)
                text = text[start:end].strip()
            elif "```" in text:
                start = text.index("```") + 3
                end = text.index("```", start)
                text = text[start:end].strip()

            try:
                parsed = json.loads(text)
                return {
                    "type": "validation",
                    "from": "kaigun_sanbou",
                    "title": "折衷案妥当性検証",
                    **parsed,
                }
            except (json.JSONDecodeError, ValueError):
                return {
                    "type": "validation",
                    "from": "kaigun_sanbou",
                    "title": "折衷案妥当性検証",
                    "summary": content,
                    "key_points": [],
                }

        except Exception as e:
            print(f"⚠️ [海軍参謀] 妥当性検証失敗: {e}")
            return {
                "type": "validation",
                "from": "kaigun_sanbou",
                "title": "折衷案妥当性検証（フォールバック）",
                "summary": "折衷案には改善の余地があります。海軍の理想と陸軍の現実のバランスを再検討する必要があります。",
                "key_points": ["理想と現実のバランス", "段階的実装の検討", "コスト効率の改善"],
            }

    async def _integrate(self, proposal: dict[str, Any], objection: dict[str, Any]) -> dict[str, Any]:
        """海軍案と陸軍案の統合（書記による折衷案作成）"""
        try:
            from gozen.shoki import Shoki, ShokiConfig
            from gozen.config import get_rank_config

            config = get_rank_config("shoki")
            shoki = Shoki(ShokiConfig(
                model=config.model,
                backend=config.backend.value,
            ))

            print("📜 [書記] 折衷案を起草中...")

            # 書記に折衷案作成を依頼
            merged = await shoki.synthesize(
                proposal,
                objection,
                merge_instruction="海軍の理想と陸軍の現実を統合した折衷案を作成せよ"
            )

            print("📜 [書記] 折衷案起草完了")

            # ダッシュボードに折衷案を書き込む
            dashboard = get_dashboard()
            merged_text = self._format_proposal(merged)
            await dashboard.merged_proposal_update(merged_text)

            return merged

        except Exception as e:
            print(f"⚠️ [書記] 統合失敗、簡易マージにフォールバック: {e}")
            # フォールバック: 従来の簡易マージ
            return {
                "title": "統合案（簡易マージ）",
                "kaigun_elements": proposal.get("key_points", []),
                "rikugun_elements": objection.get("key_points", []),
                "summary": "海軍の理想と陸軍の現実を統合した折衷案",
            }

    async def _execute_orders(self, decision: dict[str, Any], task: dict[str, Any]) -> dict[str, Any]:
        """実行部隊への指令"""
        adopted = decision.get("adopted")

        if adopted == "kaigun":
            from gozen.kaigun_sanbou.teitoku import execute as teitoku_execute
            return await teitoku_execute(decision, task, mode=self.mode)

        elif adopted == "rikugun":
            from gozen.rikugun_sanbou.shikan import execute as shikan_execute
            return await shikan_execute(decision, task, mode=self.mode)

        else:
            from gozen.kaigun_sanbou.teitoku import execute as teitoku_execute
            from gozen.rikugun_sanbou.shikan import execute as shikan_execute

            kaigun_result, rikugun_result = await asyncio.gather(
                teitoku_execute(decision, task, mode=self.mode),
                shikan_execute(decision, task, mode=self.mode),
            )

            return {
                "kaigun_result": kaigun_result,
                "rikugun_result": rikugun_result,
            }

    def _format_proposal(self, proposal: dict[str, Any]) -> str:
        """提案オブジェクトをマークダウン形式でフォーマット"""
        lines = []

        # タイトル
        if "title" in proposal:
            lines.append(f"### {proposal['title']}")
            lines.append("")

        # サマリー
        if "summary" in proposal:
            lines.append(proposal["summary"])
            lines.append("")

        # 主要ポイント
        if "key_points" in proposal and proposal["key_points"]:
            lines.append("#### 主要ポイント")
            for point in proposal["key_points"]:
                lines.append(f"- {point}")
            lines.append("")

        # 詳細な根拠
        if "reasoning" in proposal:
            lines.append("#### 根拠")
            lines.append(proposal["reasoning"])
            lines.append("")

        # その他のフィールド
        for key, value in proposal.items():
            if key not in ("title", "summary", "key_points", "reasoning"):
                if isinstance(value, str):
                    lines.append(f"**{key}**: {value}")
                elif isinstance(value, list):
                    lines.append(f"**{key}**: {', '.join(map(str, value))}")
                else:
                    lines.append(f"**{key}**: {value}")

        return "\n".join(lines) if lines else str(proposal)

    def _save_to_queue(self, queue_type: str, task_id: str, content: dict[str, Any]) -> None:
        """キューにYAMLで保存"""
        filepath = self.queue_dir / queue_type / f"{task_id}.yaml"
        with open(filepath, "w", encoding="utf-8") as f:
            yaml.dump(content, f, allow_unicode=True, default_flow_style=False)


# === 順次実行と並列実行 ===

async def execute_kaihei_sequential(tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """海兵の順次実行（Pro推奨）"""
    from gozen.kaigun_sanbou.teitoku.kancho.kaihei import execute as kaihei_execute

    results = []
    for i, task in enumerate(tasks):
        print(f"[順次] 海兵{i + 1} 実行中...")
        result = await kaihei_execute(i, task)
        results.append(result)
    return results


async def execute_hohei_parallel(tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """歩兵の並列実行（Max 5x推奨）"""
    from gozen.rikugun_sanbou.shikan.hohei import execute as hohei_execute

    print(f"[並列] 歩兵×{len(tasks)} 同時実行（Gemini API）...")
    coros = [hohei_execute(i, task) for i, task in enumerate(tasks)]
    return await asyncio.gather(*coros)


if __name__ == "__main__":
    orchestrator = GozenOrchestrator()

    test_task = {
        "task_id": "TEST-001",
        "mission": "Minecraftサーバーのインフラ構築",
        "requirements": ["k3s", "MinIO", "自動化"],
    }

    asyncio.run(orchestrator.execute_full_cycle(test_task))
