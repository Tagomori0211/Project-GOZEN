"""
Project GOZEN - 御前会議モード（PCAサイクル）

PCA（Propose-Challenge-Arbitrate）サイクルを実装する。

フロー:
  P: 海軍参謀が提案
  C: 陸軍参謀が異議
  A: 国家元首が裁定（ADOPT/MERGE/REJECT/EXECUTE）
    → ADOPT: 採択（洗練フロー可）
    → MERGE: 折衷（書記がマージ案作成 → 再PCA）
    → REJECT: 却下（再提案 → 再PCA）
    → EXECUTE: 即実行

  デッドロック時（max_iterations到達）→ エスカレーション
"""

from __future__ import annotations

import asyncio
import yaml
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from gozen.character import (
    KAIGUN_SANBOU,
    RIKUGUN_SANBOU,
    format_message,
    get_character,
)


class CouncilMode(Enum):
    """御前会議モード"""
    EXECUTE = "execute"
    COUNCIL = "council"
    DRYRUN = "dryrun"


class DecisionType(Enum):
    """裁定タイプ（後方互換）"""
    ADOPT_KAIGUN = "adopt_kaigun"
    ADOPT_RIKUGUN = "adopt_rikugun"
    INTEGRATE = "integrate"
    REMAND = "remand"
    REJECT = "reject"


class ArbitrationResult(Enum):
    """PCAサイクル裁定結果"""
    ADOPT_KAIGUN = "adopt_kaigun"      # 海軍案採択
    ADOPT_RIKUGUN = "adopt_rikugun"    # 陸軍案採択
    MERGE = "merge"                     # 折衷（書記がマージ案作成）
    REJECT = "reject"                   # 却下（再提案へ）
    EXECUTE_IMMEDIATE = "execute"       # 即実行


@dataclass
class Decision:
    """裁定データ"""
    result: ArbitrationResult
    adopted_proposal: Optional[dict[str, Any]] = None
    refine_requested: bool = False
    merge_instruction: str = ""
    reject_reason: str = ""
    reason: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class PCAState:
    """PCAサイクル状態"""
    iteration: int = 1
    max_iterations: int = 5
    phase: str = "PROPOSE"  # PROPOSE, CHALLENGE, ARBITRATE, REFINE, SYNTHESIZE, REPROPOSE

    # 却下時の累積コンテキスト
    rejection_history: list[dict[str, Any]] = field(default_factory=list)

    # 採択・洗練時の履歴
    refinement_history: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class CouncilRound:
    """会議ラウンド"""
    round_number: int
    kaigun_statement: str
    rikugun_statement: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    evidence_requested: bool = False
    evidence_provided: dict[str, Any] = field(default_factory=dict)


@dataclass
class CouncilSession:
    """御前会議セッション"""
    task_id: str
    task: dict[str, Any]
    mode: CouncilMode
    max_rounds: int = 3

    rounds: list[CouncilRound] = field(default_factory=list)
    current_round: int = 0

    proposal: Optional[dict[str, Any]] = None
    objection: Optional[dict[str, Any]] = None
    decision: Optional[dict[str, Any]] = None

    status: str = "initialized"
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    ended_at: Optional[str] = None


class CouncilManager:
    """御前会議管理クラス（PCAサイクル対応）"""

    def __init__(
        self,
        mode: CouncilMode = CouncilMode.COUNCIL,
        max_rounds: int = 3,
        auto_approve: bool = False,
        max_pca_iterations: int = 5,
    ) -> None:
        self.mode = mode
        self.max_rounds = max_rounds
        self.auto_approve = auto_approve
        self.queue_dir = Path(__file__).parent.parent / "queue"
        self.state = PCAState(max_iterations=max_pca_iterations)
        self.shoki: Optional[Any] = None  # Task 3 で型を Shoki に変更

    def _init_shoki(self) -> None:
        """書記を初期化（遅延ロード）"""
        if self.shoki is None:
            try:
                from gozen.shoki import Shoki, ShokiConfig
                from gozen.config import get_rank_config
                config = get_rank_config("shoki")
                self.shoki = Shoki(ShokiConfig(
                    model=config.model,
                    backend=config.backend.value,
                ))
            except ImportError:
                self.shoki = None

    async def start_council(self, task: dict[str, Any]) -> CouncilSession:
        """御前会議を開始"""
        task_id = task.get("task_id", f"COUNCIL-{datetime.now().strftime('%Y%m%d%H%M%S')}")

        session = CouncilSession(
            task_id=task_id,
            task=task,
            mode=self.mode,
            max_rounds=self.max_rounds,
        )

        self._print_banner(session)
        self._init_shoki()

        if self.mode == CouncilMode.EXECUTE:
            print("【即実行モード】会議をスキップして実行します。")
            session.status = "executing"
            return session

        session.proposal = await self._get_proposal(task)
        self._save_to_queue("proposal", task_id, session.proposal)

        session.objection = await self._get_objection(task, session.proposal)
        self._save_to_queue("objection", task_id, session.objection)

        if self.mode == CouncilMode.COUNCIL:
            await self._run_council_loop(session)

        session.status = "awaiting_decision"
        return session

    async def run_pca_cycle(self, task: dict[str, Any]) -> dict[str, Any]:
        """PCAサイクルを実行（メインループ）"""
        task_id = task.get("task_id", f"PCA-{datetime.now().strftime('%Y%m%d%H%M%S')}")
        self._init_shoki()

        print("\n" + "=" * 60)
        print("  PCAサイクル開始")
        print("=" * 60)

        context = task

        while self.state.iteration <= self.state.max_iterations:
            print(f"\n--- PCA Iteration {self.state.iteration}/{self.state.max_iterations} ---")

            # P: Propose
            self.state.phase = "PROPOSE"
            proposal = await self._kaigun_propose(context)
            self._save_to_queue("proposal", f"{task_id}_iter{self.state.iteration}", proposal)

            # C: Challenge
            self.state.phase = "CHALLENGE"
            objection = await self._rikugun_challenge(proposal)
            self._save_to_queue("objection", f"{task_id}_iter{self.state.iteration}", objection)

            # 書記が記録
            if self.shoki is not None:
                await self.shoki.record(proposal, objection, self.state.iteration)

            # A: Arbitrate
            self.state.phase = "ARBITRATE"
            decision = await self._present_to_shogun(proposal, objection)

            # 分岐処理
            match decision.result:
                case ArbitrationResult.EXECUTE_IMMEDIATE:
                    print("\n⚔️ 即実行が裁定されました。")
                    return {
                        "status": "execute",
                        "task_id": task_id,
                        "proposal": decision.adopted_proposal or proposal,
                        "iterations": self.state.iteration,
                    }

                case ArbitrationResult.ADOPT_KAIGUN | ArbitrationResult.ADOPT_RIKUGUN:
                    adopted = proposal if decision.result == ArbitrationResult.ADOPT_KAIGUN else objection
                    decision.adopted_proposal = adopted

                    if decision.refine_requested:
                        print("\n🔧 洗練フロー開始...")
                        await self._refine_cycle(decision)

                    self._save_to_queue("decision", task_id, {
                        "result": decision.result.value,
                        "adopted": decision.adopted_proposal,
                        "reason": decision.reason,
                        "iterations": self.state.iteration,
                    })
                    return {
                        "status": "adopted",
                        "result": decision.result.value,
                        "task_id": task_id,
                        "proposal": decision.adopted_proposal,
                        "iterations": self.state.iteration,
                    }

                case ArbitrationResult.MERGE:
                    print("\n🔀 折衷（MERGE）が裁定されました。書記がマージ案を作成します。")
                    if self.shoki is not None:
                        merged = await self.shoki.synthesize(
                            proposal, objection, decision.merge_instruction
                        )
                        context = {"merged_proposal": merged, **task}
                    else:
                        context = {
                            "merged_proposal": self._simple_merge(proposal, objection),
                            **task,
                        }
                    self.state.phase = "PROPOSE"
                    self.state.iteration += 1

                case ArbitrationResult.REJECT:
                    print(f"\n❌ 却下: {decision.reject_reason}")
                    self.state.rejection_history.append({
                        "iteration": self.state.iteration,
                        "kaigun_proposal": proposal,
                        "rikugun_objection": objection,
                        "reject_reason": decision.reject_reason,
                    })
                    self.state.phase = "REPROPOSE"
                    self.state.iteration += 1
                    context = {
                        "rejection_history": self.state.rejection_history,
                        **task,
                    }

        # max_iterations到達 → エスカレーション
        return await self._escalate(task_id)

    async def _kaigun_propose(self, context: dict[str, Any]) -> dict[str, Any]:
        """海軍参謀の提案"""
        print(f"\n{format_message('kaigun_sanbou', KAIGUN_SANBOU.get_proposal_phrase())}")

        from gozen.kaigun_sanbou import create_proposal
        return await create_proposal(context)

    async def _rikugun_challenge(self, proposal: dict[str, Any]) -> dict[str, Any]:
        """陸軍参謀の異議"""
        print(f"\n{format_message('rikugun_sanbou', RIKUGUN_SANBOU.get_objection_phrase())}")

        from gozen.rikugun_sanbou import create_objection
        return await create_objection({}, proposal)

    async def _present_to_shogun(
        self,
        proposal: dict[str, Any],
        objection: dict[str, Any],
    ) -> Decision:
        """国家元首に裁定を求める"""
        print("\n" + "=" * 60)
        print("👑 国家元首に裁定を求めます")
        print("=" * 60)

        print("\n【海軍提案】")
        print(f"  {proposal.get('summary', proposal.get('title', 'N/A'))}")
        print("\n【陸軍異議】")
        print(f"  {objection.get('summary', objection.get('title', 'N/A'))}")

        print("\n選択肢:")
        print("  [1] 海軍案を採択（ADOPT_KAIGUN）")
        print("  [2] 陸軍案を採択（ADOPT_RIKUGUN）")
        print("  [3] 折衷案を作成（MERGE）")
        print("  [4] 却下・再提案（REJECT）")
        print("  [5] 即実行（EXECUTE）")
        print("  [6] 海軍案を採択 + 洗練要求")
        print("  [7] 陸軍案を採択 + 洗練要求")

        try:
            choice = input("\n👑 裁定を入力 (1-7): ").strip()
        except EOFError:
            choice = "4"

        match choice:
            case "1":
                reason = self._get_reason()
                return Decision(
                    result=ArbitrationResult.ADOPT_KAIGUN,
                    adopted_proposal=proposal,
                    reason=reason,
                )
            case "2":
                reason = self._get_reason()
                return Decision(
                    result=ArbitrationResult.ADOPT_RIKUGUN,
                    adopted_proposal=objection,
                    reason=reason,
                )
            case "3":
                instruction = self._get_input("マージ指示: ")
                return Decision(
                    result=ArbitrationResult.MERGE,
                    merge_instruction=instruction,
                )
            case "4":
                reject_reason = self._get_input("却下理由: ")
                return Decision(
                    result=ArbitrationResult.REJECT,
                    reject_reason=reject_reason,
                )
            case "5":
                return Decision(
                    result=ArbitrationResult.EXECUTE_IMMEDIATE,
                    adopted_proposal=proposal,
                )
            case "6":
                reason = self._get_reason()
                return Decision(
                    result=ArbitrationResult.ADOPT_KAIGUN,
                    adopted_proposal=proposal,
                    refine_requested=True,
                    reason=reason,
                )
            case "7":
                reason = self._get_reason()
                return Decision(
                    result=ArbitrationResult.ADOPT_RIKUGUN,
                    adopted_proposal=objection,
                    refine_requested=True,
                    reason=reason,
                )
            case _:
                return Decision(
                    result=ArbitrationResult.REJECT,
                    reject_reason="不正な入力のため却下",
                )

    async def _refine_cycle(self, decision: Decision) -> None:
        """
        採択後の洗練サイクル
        元首判断で実行するかどうか決定。
        元首が「完了」と言うまで継続可能。
        """
        iteration = 0
        while True:
            iteration += 1
            print(f"\n--- 洗練 Iteration {iteration} ---")

            if decision.result == ArbitrationResult.ADOPT_KAIGUN:
                # 海軍が詳細化、陸軍がレビュー
                refined = await self._kaigun_refine(decision.adopted_proposal or {})
                review = await self._rikugun_review(refined)
            else:
                # 陸軍が詳細化、海軍がレビュー
                refined = await self._rikugun_refine(decision.adopted_proposal or {})
                review = await self._kaigun_review(refined)

            # 書記が記録
            if self.shoki is not None:
                await self.shoki.record_refinement(refined, review)

            self.state.refinement_history.append({
                "iteration": iteration,
                "refined": refined,
                "review": review,
            })

            # 元首に確認
            print("\n洗練結果:")
            print(f"  詳細化: {refined.get('summary', 'N/A')}")
            print(f"  レビュー: {review.get('summary', 'N/A')}")

            try:
                cont = input("\n👑 洗練を継続しますか？ (y=継続 / n=完了): ").strip().lower()
            except EOFError:
                cont = "n"

            if cont != "y":
                decision.adopted_proposal = refined
                break

    async def _kaigun_refine(self, proposal: dict[str, Any]) -> dict[str, Any]:
        """海軍が提案を洗練"""
        print(f"\n{format_message('kaigun_sanbou', '提案を洗練いたします。')}")
        from gozen.kaigun_sanbou import create_proposal
        return await create_proposal({"refine": True, "base_proposal": proposal})

    async def _rikugun_refine(self, proposal: dict[str, Any]) -> dict[str, Any]:
        """陸軍が提案を洗練"""
        print(f"\n{format_message('rikugun_sanbou', '提案を洗練するであります。')}")
        from gozen.rikugun_sanbou import create_objection
        return await create_objection({"refine": True}, proposal)

    async def _kaigun_review(self, refined: dict[str, Any]) -> dict[str, Any]:
        """海軍がレビュー"""
        print(f"\n{format_message('kaigun_sanbou', '陸軍の洗練案をレビューいたします。')}")
        from gozen.kaigun_sanbou import create_proposal
        return await create_proposal({"review": True, "refined_proposal": refined})

    async def _rikugun_review(self, refined: dict[str, Any]) -> dict[str, Any]:
        """陸軍がレビュー"""
        print(f"\n{format_message('rikugun_sanbou', '海軍の洗練案をレビューするであります。')}")
        from gozen.rikugun_sanbou import create_objection
        return await create_objection({"review": True}, refined)

    async def _escalate(self, task_id: str) -> dict[str, Any]:
        """デッドロック時のエスカレーション処理"""
        report = ""
        if self.shoki is not None:
            report = await self.shoki.generate_escalation_report(
                self.state.rejection_history,
                self.state.refinement_history,
            )
        else:
            report = self._generate_simple_escalation_report()

        # dashboard.md に書き込み
        try:
            from gozen.dashboard import get_dashboard
            dashboard = get_dashboard()
            await dashboard.write_escalation(report)
        except Exception:
            pass

        # ファイルに保存
        escalation_path = self.queue_dir / "escalation"
        escalation_path.mkdir(parents=True, exist_ok=True)
        (escalation_path / f"{task_id}_escalation.md").write_text(
            report, encoding="utf-8"
        )

        # ターミナル通知
        self._notify_escalation(task_id)

        return {
            "status": "escalated",
            "task_id": task_id,
            "report": report,
            "iterations": self.state.iteration - 1,
            "options": [
                "force-kaigun",
                "force-rikugun",
                "manual-merge",
                "split",
                "abort",
            ],
        }

    def _notify_escalation(self, task_id: str) -> None:
        """エスカレーション通知"""
        print("\a")  # ベル音
        print(f"""
    ╔══════════════════════════════════════════╗
    ║  ESCALATION: 御前会議が膠着しました      ║
    ╚══════════════════════════════════════════╝

    タスクID: {task_id}
    PCA反復: {self.state.iteration - 1}/{self.state.max_iterations}
    却下回数: {len(self.state.rejection_history)}

    詳細: status/dashboard.md
    対応: gozen decide --task {task_id} --action <ACTION>

    選択肢:
      force-kaigun  : 海軍案を強制採択
      force-rikugun : 陸軍案を強制採択
      manual-merge  : 統合案を手動記述
      split         : タスク分割
      abort         : 本タスク中止
        """)

    def _generate_simple_escalation_report(self) -> str:
        """書記なしの簡易エスカレーションレポート"""
        history_lines = []
        for entry in self.state.rejection_history:
            history_lines.append(
                f"- Iteration {entry['iteration']}: {entry.get('reject_reason', 'N/A')}"
            )

        return f"""# ESCALATION - 御前会議膠着

## Status: DEADLOCK (iteration {self.state.iteration - 1})

### 却下履歴
{chr(10).join(history_lines) if history_lines else '(なし)'}

### 元首選択肢

| ACTION | 説明 |
|--------|------|
| `force-kaigun` | 海軍案を強制採択 |
| `force-rikugun` | 陸軍案を強制採択 |
| `manual-merge` | 統合案を手動記述 |
| `split` | タスク分割 |
| `abort` | 本タスク中止 |
"""

    def _simple_merge(
        self, proposal: dict[str, Any], objection: dict[str, Any]
    ) -> dict[str, Any]:
        """書記なしの簡易マージ"""
        return {
            "title": "折衷案",
            "kaigun_elements": proposal.get("key_points", []),
            "rikugun_elements": objection.get("key_points", []),
            "summary": "海軍の理想と陸軍の現実を統合した折衷案",
        }

    @staticmethod
    def _get_reason() -> str:
        """理由入力ヘルパー"""
        try:
            return input("理由（任意）: ").strip()
        except EOFError:
            return ""

    @staticmethod
    def _get_input(prompt: str) -> str:
        """入力ヘルパー"""
        try:
            return input(prompt).strip()
        except EOFError:
            return ""

    # =================================================================
    # 既存互換メソッド
    # =================================================================

    async def _get_proposal(self, task: dict[str, Any]) -> dict[str, Any]:
        """海軍参謀の提案を取得"""
        print("\n" + "=" * 60)
        print(format_message("kaigun_sanbou", KAIGUN_SANBOU.get_proposal_phrase()))
        print("=" * 60)

        from gozen.kaigun_sanbou import create_proposal
        return await create_proposal(task)

    async def _get_objection(self, task: dict[str, Any], proposal: dict[str, Any]) -> dict[str, Any]:
        """陸軍参謀の異議を取得"""
        print("\n" + "=" * 60)
        print(format_message("rikugun_sanbou", RIKUGUN_SANBOU.get_objection_phrase()))
        print("=" * 60)

        from gozen.rikugun_sanbou import create_objection
        return await create_objection(task, proposal)

    async def _run_council_loop(self, session: CouncilSession) -> None:
        """会議ループを実行"""
        print("\n" + "=" * 60)
        print("  御前会議ループ開始")
        print("=" * 60)

        for round_num in range(1, self.max_rounds + 1):
            session.current_round = round_num
            print(f"\n--- 第{round_num}ラウンド ---")

            kaigun_statement = self._get_kaigun_response(session, round_num)
            rikugun_statement = self._get_rikugun_response(session, round_num)

            evidence_requested = self._check_evidence_request(kaigun_statement, rikugun_statement)

            round_record = CouncilRound(
                round_number=round_num,
                kaigun_statement=kaigun_statement,
                rikugun_statement=rikugun_statement,
                evidence_requested=evidence_requested,
            )
            session.rounds.append(round_record)

            if self._check_consensus(session):
                print("\n両参謀の合意が得られました。")
                break

            if round_num < self.max_rounds and self._should_intervene():
                print("\n👑 国家元首: 「決着！」")
                break

        print("\n" + "=" * 60)
        print("  御前会議ループ終了")
        print("=" * 60)

    def _get_kaigun_response(self, session: CouncilSession, round_num: int) -> str:
        char = get_character("kaigun_sanbou")

        if round_num == 1:
            response = f"陸軍の異議に対し、以下の反論を申し上げます。\n{char.get_verification_phrase()}"
        else:
            response = f"第{round_num}回目の反論であります。{char.get_verification_phrase()}"

        print(format_message("kaigun_sanbou", response))
        return response

    def _get_rikugun_response(self, session: CouncilSession, round_num: int) -> str:
        char = get_character("rikugun_sanbou")

        if round_num == 1:
            response = f"海軍の反論に対し、再度異議を申し立てるであります。\n{char.get_verification_phrase()}"
        else:
            response = f"第{round_num}回目の再異議であります。{char.get_verification_phrase()}"

        print(format_message("rikugun_sanbou", response))
        return response

    def _check_evidence_request(self, kaigun_statement: str, rikugun_statement: str) -> bool:
        evidence_keywords = ["証拠", "証跡", "検証", "データ", "根拠"]
        combined = kaigun_statement + rikugun_statement
        return any(kw in combined for kw in evidence_keywords)

    def _check_consensus(self, session: CouncilSession) -> bool:
        return False

    def _should_intervene(self) -> bool:
        try:
            response = input("\n👑 [国家元首] 会議を継続しますか？ (y=継続 / n=決着): ").strip().lower()
            return response != "y"
        except EOFError:
            return True

    async def make_decision(
        self,
        session: CouncilSession,
        decision_type: DecisionType,
        reason: str = "",
    ) -> dict[str, Any]:
        """国家元首の裁定を下す"""
        decision: dict[str, Any] = {
            "task_id": session.task_id,
            "type": decision_type.value,
            "reason": reason,
            "timestamp": datetime.now().isoformat(),
            "rounds_taken": session.current_round,
            "proposal_summary": session.proposal.get("summary", "") if session.proposal else "",
            "objection_summary": session.objection.get("summary", "") if session.objection else "",
        }

        if decision_type in [DecisionType.ADOPT_KAIGUN, DecisionType.ADOPT_RIKUGUN, DecisionType.INTEGRATE]:
            decision["approved"] = True
            decision["adopted"] = decision_type.value.replace("adopt_", "")
        elif decision_type == DecisionType.REMAND:
            decision["approved"] = False
            decision["remanded"] = True
        else:
            decision["approved"] = False

        session.decision = decision
        session.status = "decided"
        session.ended_at = datetime.now().isoformat()

        self._save_to_queue("decision", session.task_id, decision)
        self._print_decision(decision)

        return decision

    def _print_decision(self, decision: dict[str, Any]) -> None:
        print("\n" + "=" * 60)
        print("  国家元首の裁定")
        print("=" * 60)

        decision_type = decision.get("type", "unknown")
        reason = decision.get("reason", "")

        print(f"\n裁定: {decision_type}")
        if reason:
            print(f"理由: {reason}")

        if decision.get("approved"):
            print("\n承認されました。実行フェーズに移行します。")
        elif decision.get("remanded"):
            print("\n差し戻しとなりました。再検討を求めます。")
        else:
            print("\n却下されました。")

    def _print_banner(self, session: CouncilSession) -> None:
        mode_str = {
            CouncilMode.EXECUTE: "即実行",
            CouncilMode.COUNCIL: "会議",
            CouncilMode.DRYRUN: "ドライラン",
        }

        print("\n" + "=" * 60)
        print(f"  御前会議 - {mode_str[session.mode]}モード")
        print(f"  タスクID: {session.task_id}")
        print(f"  最大ラウンド: {session.max_rounds}")
        print(f"  PCA最大反復: {self.state.max_iterations}")
        print("=" * 60)

    def _save_to_queue(self, queue_type: str, task_id: str, content: dict[str, Any]) -> None:
        queue_path = self.queue_dir / queue_type
        queue_path.mkdir(parents=True, exist_ok=True)

        filepath = queue_path / f"{task_id}.yaml"
        with open(filepath, "w", encoding="utf-8") as f:
            yaml.dump(content, f, allow_unicode=True, default_flow_style=False)


# ============================================================
# インタラクティブ裁定UI
# ============================================================

async def interactive_decision(session: CouncilSession, manager: CouncilManager) -> dict[str, Any]:
    """インタラクティブに国家元首の裁定を取得"""
    print("\n" + "=" * 60)
    print("【国家元首】裁定をお願いします。")
    print("=" * 60)

    print("\n【海軍の主張】")
    if session.proposal:
        print(session.proposal.get("summary", "N/A"))

    print("\n【陸軍の異議】")
    if session.objection:
        print(session.objection.get("summary", "N/A"))

    print("\n選択肢:")
    print("  [1] 海軍案を採択")
    print("  [2] 陸軍案を採択")
    print("  [3] 統合案を作成")
    print("  [4] 差し戻し（再検討）")
    print("  [5] 却下")

    try:
        choice = input("\n裁定を入力 (1-5): ").strip()
    except EOFError:
        choice = "5"

    decision_map = {
        "1": DecisionType.ADOPT_KAIGUN,
        "2": DecisionType.ADOPT_RIKUGUN,
        "3": DecisionType.INTEGRATE,
        "4": DecisionType.REMAND,
        "5": DecisionType.REJECT,
    }

    decision_type = decision_map.get(choice, DecisionType.REJECT)

    try:
        reason = input("理由（任意）: ").strip()
    except EOFError:
        reason = ""

    return await manager.make_decision(session, decision_type, reason)


# ============================================================
# メイン実行
# ============================================================

async def run_council(
    task: dict[str, Any],
    mode: str = "council",
    max_rounds: int = 3,
) -> dict[str, Any]:
    """御前会議を実行"""
    council_mode = CouncilMode(mode)
    manager = CouncilManager(mode=council_mode, max_rounds=max_rounds)

    session = await manager.start_council(task)

    if council_mode == CouncilMode.DRYRUN:
        print("\n[DRYRUN] 会議完了。実行はスキップされました。")
        return {"status": "dryrun", "session": session}

    decision = await interactive_decision(session, manager)

    if decision.get("approved"):
        print("\n実行フェーズに移行...")
        return {"status": "approved", "decision": decision, "session": session}
    elif decision.get("remanded"):
        return {"status": "remanded", "decision": decision, "session": session}
    return {"status": "rejected", "decision": decision, "session": session}


async def run_pca_council(
    task: dict[str, Any],
    max_iterations: int = 5,
) -> dict[str, Any]:
    """PCAサイクルベースの御前会議を実行"""
    manager = CouncilManager(
        mode=CouncilMode.COUNCIL,
        max_pca_iterations=max_iterations,
    )
    return await manager.run_pca_cycle(task)


# ============================================================
# デッドロック解決
# ============================================================

def resolve_deadlock(
    task_id: str,
    adopted: str,
    merge_file: Optional[str] = None,
) -> dict[str, Any]:
    """エスカレーション後のデッドロック解決"""
    queue_dir = Path(__file__).parent.parent / "queue"

    resolution = {
        "task_id": task_id,
        "adopted": adopted,
        "timestamp": datetime.now().isoformat(),
        "type": "deadlock_resolution",
    }

    if merge_file:
        merge_path = Path(merge_file)
        if merge_path.exists():
            with open(merge_path, "r", encoding="utf-8") as f:
                resolution["merge_content"] = yaml.safe_load(f)

    resolution_path = queue_dir / "decision"
    resolution_path.mkdir(parents=True, exist_ok=True)
    filepath = resolution_path / f"{task_id}_resolution.yaml"
    with open(filepath, "w", encoding="utf-8") as f:
        yaml.dump(resolution, f, allow_unicode=True, default_flow_style=False)

    return resolution


if __name__ == "__main__":
    test_task = {
        "task_id": "COUNCIL-TEST-001",
        "mission": "Minecraftサーバーのインフラ構築",
        "requirements": ["k3s", "MinIO", "自動化"],
    }

    result = asyncio.run(run_council(test_task, mode="council", max_rounds=2))
    print(f"\n最終結果: {result['status']}")
