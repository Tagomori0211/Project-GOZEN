"""
Project GOZEN - 御前会議モード

会議ループ、承認フロー、裁定システムを実装する。

モード:
  --mode execute   即実行（従来）
  --mode council   会議ループ→承認後に実行
  --mode dryrun    会議のみ（実行なし）

フロー:
  提案 → 異議 → (反論 → 再異議)×N → 国家元首「決着」 → 裁定 → 実行 → 相互監査
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
    """裁定タイプ"""
    ADOPT_KAIGUN = "adopt_kaigun"
    ADOPT_RIKUGUN = "adopt_rikugun"
    INTEGRATE = "integrate"
    REMAND = "remand"
    REJECT = "reject"


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
    """御前会議管理クラス"""

    def __init__(
        self,
        mode: CouncilMode = CouncilMode.COUNCIL,
        max_rounds: int = 3,
        auto_approve: bool = False,
    ) -> None:
        self.mode = mode
        self.max_rounds = max_rounds
        self.auto_approve = auto_approve
        self.queue_dir = Path(__file__).parent.parent / "queue"

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
        print("\n" + "🔄" * 30)
        print("  御前会議ループ開始")
        print("🔄" * 30)

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
                print("\n✅ 両参謀の合意が得られました。")
                break

            if round_num < self.max_rounds and self._should_intervene():
                print("\n👑 国家元首: 「決着！」")
                break

        print("\n" + "🔄" * 30)
        print("  御前会議ループ終了")
        print("🔄" * 30)

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
        print("\n" + "👑" * 30)
        print("  国家元首の裁定")
        print("👑" * 30)

        decision_type = decision.get("type", "unknown")
        reason = decision.get("reason", "")

        print(f"\n裁定: {decision_type}")
        if reason:
            print(f"理由: {reason}")

        if decision.get("approved"):
            print("\n✅ 承認されました。実行フェーズに移行します。")
        elif decision.get("remanded"):
            print("\n🔄 差し戻しとなりました。再検討を求めます。")
        else:
            print("\n❌ 却下されました。")

    def _print_banner(self, session: CouncilSession) -> None:
        mode_str = {
            CouncilMode.EXECUTE: "即実行",
            CouncilMode.COUNCIL: "会議",
            CouncilMode.DRYRUN: "ドライラン",
        }

        print("\n" + "🏯" * 30)
        print(f"  御前会議 - {mode_str[session.mode]}モード")
        print(f"  タスクID: {session.task_id}")
        print(f"  最大ラウンド: {session.max_rounds}")
        print("🏯" * 30)

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
        print(session.proposal.get("summary", "N/A")[:200])

    print("\n【陸軍の異議】")
    if session.objection:
        print(session.objection.get("summary", "N/A")[:200])

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
        print("\n⚔️ 実行フェーズに移行...")
        return {"status": "approved", "decision": decision, "session": session}
    elif decision.get("remanded"):
        return {"status": "remanded", "decision": decision, "session": session}
    return {"status": "rejected", "decision": decision, "session": session}


if __name__ == "__main__":
    test_task = {
        "task_id": "COUNCIL-TEST-001",
        "mission": "Minecraftサーバーのインフラ構築",
        "requirements": ["k3s", "MinIO", "自動化"],
    }

    result = asyncio.run(run_council(test_task, mode="council", max_rounds=2))
    print(f"\n最終結果: {result['status']}")
