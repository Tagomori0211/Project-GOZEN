"""
戦況盤（dashboard）- リアルタイムステータス表示

各モジュールの実行状態を status/dashboard.md に書き出す。
人間（国家元首）が cat / watch で戦況を把握できるようにする。

設計原則:
  - dashboard.md は補助UI / 可視化成果物
  - 生成失敗 ≠ システム失敗
  - 意思決定ロジック・裁定フローを絶対に巻き込まない
  - LLM出力にはサロゲート等の不正Unicodeが混入しうるため、
    永続化前に必ずサニタイズを通す
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

_STATUS_ICONS = {
    "waiting": "\u2b1c",       # ⬜
    "in_progress": "\U0001f504",  # 🔄
    "completed": "\u2705",     # ✅
    "failed": "\u274c",        # ❌
}


class DashboardWriter:
    """
    戦況盤ライター

    asyncio.Lock で並列書き込みを排他制御し、
    status/dashboard.md をアトミックに更新する。
    """

    def __init__(self) -> None:
        self._initialized = False
        self._lock: asyncio.Lock = asyncio.Lock()
        self._output_path: Path = (
            Path(__file__).parent.parent / "status" / "dashboard.md"
        )

        # --- 状態 ---
        self._task_id: str = ""
        self._mission: str = ""
        self._council_mode: str = ""
        self._start_time: str = ""
        self._last_update: str = ""
        self._final_status: str = "in_progress"

        self._phase: str = ""
        self._phase_status: str = ""
        self._completed_phases: list[str] = []

        self._proposal_status: str = "waiting"
        self._proposal_summary: str = ""
        self._objection_status: str = "waiting"
        self._objection_summary: str = ""
        self._merged_proposal: str = ""

        self._decision_choice: str = ""
        self._decision_adopted: str = ""

        # units: {(branch, rank, unit_id): {"status": ..., "detail": ...}}
        self._units: dict[tuple[str, str, str], dict[str, str]] = {}

        # 活動ログ（新しいものが先頭）
        self._log: list[str] = []

        # 書記記録（PCAサイクル用）
        self._council_records: list[dict[str, Any]] = []
        self._refinement_records: list[dict[str, Any]] = []
        self._escalation_report: str = ""

    # =================================================================
    # Public API
    # =================================================================

    async def session_start(
        self, task_id: str, mission: str, council_mode: str
    ) -> None:
        """セッション開始時にダッシュボードを初期化"""
        # interactiveモード対策: Lock を再生成
        self._lock = asyncio.Lock()
        self._initialized = True

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._task_id = task_id
        self._mission = mission
        self._council_mode = council_mode
        self._start_time = now
        self._last_update = now
        self._final_status = "in_progress"

        self._phase = "initialization"
        self._phase_status = "completed"
        self._completed_phases = ["initialization"]

        self._proposal_status = "waiting"
        self._proposal_summary = ""
        self._objection_status = "waiting"
        self._objection_summary = ""
        self._merged_proposal = ""
        self._decision_choice = ""
        self._decision_adopted = ""

        self._units = {}
        self._log = []
        self._council_records = []
        self._refinement_records = []
        self._escalation_report = ""

        self._add_log(f"セッション開始: {task_id}")
        await self._write_dashboard()

    async def phase_update(self, phase_name: str, status: str) -> None:
        if not self._initialized:
            return
        async with self._lock:
            if status == "completed" and phase_name not in self._completed_phases:
                self._completed_phases.append(phase_name)
            self._phase = phase_name
            self._phase_status = status
            self._add_log(f"フェーズ: {phase_name} → {status}")
            await self._write_dashboard()

    async def proposal_update(
        self, status: str, summary: Optional[str] = None
    ) -> None:
        if not self._initialized:
            return
        async with self._lock:
            self._proposal_status = status
            if summary:
                # 参謀レベルは提案全文を保存
                self._proposal_summary = summary
            self._add_log(f"海軍提案: {status}")
            await self._write_dashboard()

    async def objection_update(
        self, status: str, summary: Optional[str] = None
    ) -> None:
        if not self._initialized:
            return
        async with self._lock:
            self._objection_status = status
            if summary:
                # 参謀レベルは異議全文を保存
                self._objection_summary = summary
            self._add_log(f"陸軍異議: {status}")
            await self._write_dashboard()

    async def decision_update(self, choice: str, adopted: str) -> None:
        if not self._initialized:
            return
        async with self._lock:
            self._decision_choice = choice
            self._decision_adopted = adopted
            self._add_log(f"裁定: {choice} (採択: {adopted})")
            await self._write_dashboard()

    async def merged_proposal_update(self, content: str) -> None:
        """書記による折衷案をダッシュボードに書き込む"""
        if not self._initialized:
            return
        async with self._lock:
            self._merged_proposal = content
            self._add_log("折衷案: 完了")
            await self._write_dashboard()

    async def unit_update(
        self,
        branch: str,
        rank: str,
        unit_id: str,
        status: str,
        detail: Optional[str] = None,
    ) -> None:
        if not self._initialized:
            return
        async with self._lock:
            self._units[(branch, rank, unit_id)] = {
                "status": status,
                "detail": detail or "",
            }
            label = f"{rank}[{unit_id}]"
            if detail:
                label += f": {detail[:40]}"
            self._add_log(f"{label} → {status}")
            await self._write_dashboard()

    async def session_end(self, final_status: str) -> None:
        if not self._initialized:
            return
        async with self._lock:
            self._final_status = final_status
            self._add_log(f"セッション終了: {final_status}")
            await self._write_dashboard()

    async def write_council_record(
        self,
        iteration: int,
        proposal_summary: str,
        objection_summary: str,
        sticking_points: list[dict[str, Any]],
        decision: Optional[str] = None,
    ) -> None:
        """会議記録を追記（書記から呼ばれる）"""
        if not self._initialized:
            return
        async with self._lock:
            self._council_records.append({
                "iteration": iteration,
                "proposal_summary": proposal_summary,
                "objection_summary": objection_summary,
                "sticking_points": sticking_points,
                "decision": decision,
            })
            self._add_log(f"書記記録: PCA Iteration {iteration}")
            await self._write_dashboard()

    async def write_escalation(self, report: str) -> None:
        """エスカレーションレポートを書き込み"""
        if not self._initialized:
            return
        async with self._lock:
            self._escalation_report = report
            self._add_log("ESCALATION: 膠着レポート記録")
            await self._write_dashboard()

    async def write_refinement(
        self,
        iteration: int,
        refined_content: str,
        review_content: str,
    ) -> None:
        """洗練記録を追記"""
        if not self._initialized:
            return
        async with self._lock:
            self._refinement_records.append({
                "iteration": iteration,
                "refined": refined_content,
                "review": review_content,
            })
            self._add_log(f"洗練記録: Iteration {iteration}")
            await self._write_dashboard()

    # =================================================================
    # Internal
    # =================================================================

    def _add_log(self, message: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        self._last_update = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._log.insert(0, f"- `{ts}` {message}")
        # 最新50件に制限
        self._log = self._log[:50]

    def _icon(self, status: str) -> str:
        return _STATUS_ICONS.get(status, "\u2b1c")

    @staticmethod
    def _sanitize_text(text: str) -> str:
        """UTF-8 でエンコード不可な文字（サロゲート等）を除去する。

        ローカルLLM（Qwen/Ollama）の出力に不正 Unicode が混入する場合の
        安全弁として、永続化直前に必ず通す。
        """
        return text.encode("utf-8", errors="replace").decode("utf-8")

    async def _write_dashboard(self) -> None:
        """dashboard.md を書き出す（best-effort: 失敗しても会議進行に影響しない）"""
        try:
            self._output_path.parent.mkdir(parents=True, exist_ok=True)
            content = self._sanitize_text(self._render())
            self._output_path.write_text(content, encoding="utf-8")
        except Exception as e:
            logger.warning("dashboard.md write skipped: %s", e)

    # =================================================================
    # Render
    # =================================================================

    def _render(self) -> str:
        lines: list[str] = []

        # --- ヘッダー ---
        lines.append("# \U0001f3ef 御前会議 戦況盤")
        lines.append("")
        lines.append("| 項目 | 値 |")
        lines.append("|------|-----|")
        lines.append(f"| Task ID | `{self._task_id}` |")
        lines.append(f"| 任務 | {self._mission} |")
        lines.append(f"| 作戦形式 | {self._council_mode} |")
        lines.append(f"| 開始 | {self._start_time} |")
        lines.append(f"| 更新 | {self._last_update} |")
        lines.append(f"| 最終状態 | **{self._final_status}** |")
        lines.append("")

        # --- フェーズ ---
        lines.append("## 進行フェーズ")
        lines.append("")
        lines.append(
            f"{self._icon(self._phase_status)} **{self._phase}** ({self._phase_status})"
        )
        lines.append("")

        all_phases = ["initialization", "proposal", "objection", "decision", "execution"]
        rendered: list[str] = []
        for p in all_phases:
            if p in self._completed_phases:
                rendered.append(f"~~{p}~~")
            else:
                rendered.append(p)
        lines.append(f"完了済: {' → '.join(rendered)}")
        lines.append("")

        # --- 討議 ---
        lines.append("## 討議")
        lines.append("")
        lines.append("| | 状態 | 概要 |")
        lines.append("|---|------|------|")
        lines.append(
            f"| {self._icon(self._proposal_status)} 海軍提案"
            f" | {self._proposal_status}"
            f" | {self._proposal_summary} |"
        )
        lines.append(
            f"| {self._icon(self._objection_status)} 陸軍異議"
            f" | {self._objection_status}"
            f" | {self._objection_summary} |"
        )
        lines.append("")

        # --- 折衷案 ---
        if self._merged_proposal:
            lines.append("## 折衷案（書記統合）")
            lines.append("")
            lines.append(self._merged_proposal)
            lines.append("")

        # --- 海軍ツリー ---
        lines.append("## 海軍 (Naval Branch)")
        lines.append("")
        lines.append(self._render_unit_line("kaigun", "kaigun_sanbou", "main", "海軍参謀"))
        lines.append(self._render_unit_line("kaigun", "teitoku", "main", "  └─ 提督"))
        lines.append(self._render_unit_line("kaigun", "kancho", "main", "      └─ 艦長"))
        for i in range(8):
            prefix = "          ├─" if i < 7 else "          └─"
            lines.append(
                self._render_unit_line("kaigun", "kaihei", str(i), f"{prefix} 海兵{i}")
            )
        lines.append("")

        # --- 陸軍ツリー ---
        lines.append("## 陸軍 (Army Branch)")
        lines.append("")
        lines.append(self._render_unit_line("rikugun", "rikugun_sanbou", "main", "陸軍参謀"))
        lines.append(self._render_unit_line("rikugun", "shikan", "main", "  └─ 士官"))
        for i in range(4):
            prefix = "      ├─" if i < 3 else "      └─"
            lines.append(
                self._render_unit_line("rikugun", "hohei", str(i), f"{prefix} 歩兵{i}")
            )
        lines.append("")

        # --- 書記記録（PCA） ---
        if self._council_records:
            lines.append("## 書記記録（PCAサイクル）")
            lines.append("")
            lines.append("| Iter | 海軍提案 | 陸軍異議 | 争点数 | 裁定 |")
            lines.append("|------|---------|---------|--------|------|")
            for rec in self._council_records:
                it = rec.get("iteration", "?")
                ps = rec.get("proposal_summary", "")[:40]
                os_ = rec.get("objection_summary", "")[:40]
                sp = len(rec.get("sticking_points", []))
                dec = rec.get("decision", "-") or "-"
                lines.append(f"| {it} | {ps} | {os_} | {sp} | {dec} |")
            lines.append("")

        # --- 洗練記録 ---
        if self._refinement_records:
            lines.append("## 洗練記録")
            lines.append("")
            for rec in self._refinement_records:
                it = rec.get("iteration", "?")
                lines.append(f"### 洗練 Iteration {it}")
                lines.append(f"- 詳細化: {rec.get('refined', 'N/A')[:80]}")
                lines.append(f"- レビュー: {rec.get('review', 'N/A')[:80]}")
                lines.append("")

        # --- エスカレーション ---
        if self._escalation_report:
            lines.append("---")
            lines.append("")
            lines.append(self._escalation_report)
            lines.append("")

        # --- 裁定 ---
        if self._decision_choice or self._decision_adopted:
            lines.append("## 裁定")
            lines.append("")
            lines.append(f"- 選択: {self._decision_choice}")
            lines.append(f"- 採択: {self._decision_adopted}")
            lines.append("")

        # --- ログ ---
        lines.append("## 活動ログ")
        lines.append("")
        for entry in self._log[:20]:
            lines.append(entry)
        lines.append("")

        return "\n".join(lines)

    def _render_unit_line(
        self, branch: str, rank: str, unit_id: str, label: str
    ) -> str:
        key = (branch, rank, unit_id)
        info = self._units.get(key)
        if info is None:
            return f"{label} [{self._icon('waiting')} waiting]"
        status = info["status"]
        detail = info["detail"]
        icon = self._icon(status)
        if detail:
            return f"{label} [{icon} {status}: {detail}]"
        return f"{label} [{icon} {status}]"


# =================================================================
# Singleton
# =================================================================

_instance: Optional[DashboardWriter] = None


def get_dashboard() -> DashboardWriter:
    """DashboardWriter シングルトンを取得"""
    global _instance
    if _instance is None:
        _instance = DashboardWriter()
    return _instance
