"""
Project GOZEN - 監査モジュール

ゼロトラスト原則に基づく相互監査システム。
海軍成果物 → 陸軍監査
陸軍成果物 → 海軍監査
不合格時は差し戻し

「検証なき信頼は敗北への道」
「信用するな、検証せよ」
"""

import asyncio
import yaml
import hashlib
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Literal
from enum import Enum

from gozen.config import get_rank_config, Branch
from gozen.character import ZeroTrustDialogue, get_character


class AuditResult(Enum):
    """監査結果"""
    PASS = "pass"  # 合格
    FAIL = "fail"  # 不合格
    CONDITIONAL = "conditional"  # 条件付き合格
    PENDING = "pending"  # 保留


class AuditSeverity(Enum):
    """指摘の重大度"""
    CRITICAL = "critical"  # 致命的（即時差し戻し）
    MAJOR = "major"  # 重大（要修正）
    MINOR = "minor"  # 軽微（推奨修正）
    INFO = "info"  # 情報（参考）


@dataclass
class AuditFinding:
    """監査指摘事項"""
    severity: AuditSeverity
    category: str
    description: str
    evidence: str = ""
    recommendation: str = ""


@dataclass
class AuditReport:
    """監査レポート"""
    artifact_id: str
    artifact_type: str
    artifact_hash: str
    
    auditor_branch: str  # 監査者の所属（kaigun/rikugun）
    auditor_rank: str  # 監査者の階級
    
    result: AuditResult
    findings: list[AuditFinding] = field(default_factory=list)
    
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    
    summary: str = ""
    
    def add_finding(self, finding: AuditFinding):
        """指摘事項を追加"""
        self.findings.append(finding)
    
    @property
    def critical_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == AuditSeverity.CRITICAL)
    
    @property
    def major_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == AuditSeverity.MAJOR)
    
    @property
    def minor_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == AuditSeverity.MINOR)
    
    def to_dict(self) -> dict:
        """辞書に変換"""
        return {
            "artifact_id": self.artifact_id,
            "artifact_type": self.artifact_type,
            "artifact_hash": self.artifact_hash,
            "auditor_branch": self.auditor_branch,
            "auditor_rank": self.auditor_rank,
            "result": self.result.value,
            "findings": [
                {
                    "severity": f.severity.value,
                    "category": f.category,
                    "description": f.description,
                    "evidence": f.evidence,
                    "recommendation": f.recommendation,
                }
                for f in self.findings
            ],
            "summary": self.summary,
            "critical_count": self.critical_count,
            "major_count": self.major_count,
            "minor_count": self.minor_count,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


# ============================================================
# 監査チェックリスト
# ============================================================

@dataclass
class AuditChecklist:
    """監査チェックリスト"""
    name: str
    items: list[dict] = field(default_factory=list)


# 海軍が陸軍を監査する際のチェックリスト
KAIGUN_AUDIT_CHECKLIST = AuditChecklist(
    name="海軍監査チェックリスト（陸軍成果物向け）",
    items=[
        {"category": "スケーラビリティ", "check": "将来の拡張性が考慮されているか"},
        {"category": "アーキテクチャ", "check": "設計原則に従っているか"},
        {"category": "自動化", "check": "手動作業が最小化されているか"},
        {"category": "ドキュメント", "check": "十分な文書化がされているか"},
        {"category": "再現性", "check": "Infrastructure as Code で再現可能か"},
        {"category": "セキュリティ", "check": "セキュリティベストプラクティスに従っているか"},
    ]
)

# 陸軍が海軍を監査する際のチェックリスト
RIKUGUN_AUDIT_CHECKLIST = AuditChecklist(
    name="陸軍監査チェックリスト（海軍成果物向け）",
    items=[
        {"category": "現実性", "check": "現在の制約条件で実装可能か"},
        {"category": "コスト", "check": "予算内に収まるか（月$60目安）"},
        {"category": "運用負荷", "check": "1人で運用可能か"},
        {"category": "複雑性", "check": "過剰に複雑ではないか"},
        {"category": "即時性", "check": "現在の要件を満たせるか"},
        {"category": "リスク", "check": "リスクが適切に評価されているか"},
    ]
)


# ============================================================
# 監査マネージャー
# ============================================================

class AuditManager:
    """
    監査マネージャー
    
    ゼロトラスト原則に基づき、相互監査を実行する。
    """
    
    def __init__(self, audit_dir: Optional[Path] = None):
        self.audit_dir = audit_dir or Path(__file__).parent.parent / "audit"
        self.audit_dir.mkdir(parents=True, exist_ok=True)
    
    def determine_auditor(self, artifact_branch: str) -> tuple[str, str]:
        """
        成果物の作成元から監査者を決定
        
        海軍成果物 → 陸軍が監査
        陸軍成果物 → 海軍が監査
        
        Returns:
            (auditor_branch, auditor_rank)
        """
        if artifact_branch == "kaigun":
            return ("rikugun", "rikugun_sanbou")
        else:
            return ("kaigun", "kaigun_sanbou")
    
    def compute_hash(self, content: str) -> str:
        """成果物のハッシュを計算"""
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    async def audit(
        self,
        artifact_id: str,
        artifact_type: str,
        artifact_content: str,
        artifact_branch: str,
    ) -> AuditReport:
        """
        成果物を監査
        
        Args:
            artifact_id: 成果物ID
            artifact_type: 成果物タイプ（proposal/implementation/etc）
            artifact_content: 成果物の内容
            artifact_branch: 作成元の所属（kaigun/rikugun）
            
        Returns:
            監査レポート
        """
        auditor_branch, auditor_rank = self.determine_auditor(artifact_branch)
        artifact_hash = self.compute_hash(artifact_content)
        
        print("\n" + "🔍" * 25)
        print(f"  相互監査開始")
        print(f"  成果物: {artifact_id} ({artifact_type})")
        print(f"  作成元: {artifact_branch}")
        print(f"  監査者: {auditor_branch}")
        print("🔍" * 25)
        
        # 監査レポート初期化
        report = AuditReport(
            artifact_id=artifact_id,
            artifact_type=artifact_type,
            artifact_hash=artifact_hash,
            auditor_branch=auditor_branch,
            auditor_rank=auditor_rank,
            result=AuditResult.PENDING,
        )
        
        # ゼロトラスト宣言
        char = get_character(auditor_rank)
        print(f"\n【{char.name}】{char.get_verification_phrase()}")
        
        # チェックリスト実行
        checklist = KAIGUN_AUDIT_CHECKLIST if auditor_branch == "kaigun" else RIKUGUN_AUDIT_CHECKLIST
        await self._execute_checklist(report, checklist, artifact_content)
        
        # 結果判定
        report.result = self._determine_result(report)
        report.completed_at = datetime.now().isoformat()
        report.summary = self._generate_summary(report)
        
        # レポート保存
        self._save_report(report)
        
        # 結果表示
        self._print_result(report)
        
        return report
    
    async def _execute_checklist(
        self,
        report: AuditReport,
        checklist: AuditChecklist,
        content: str,
    ):
        """チェックリストを実行"""
        print(f"\n📋 {checklist.name}")
        print("-" * 50)
        
        for item in checklist.items:
            category = item["category"]
            check = item["check"]
            
            # 実際の実装ではLLMで判定
            # ここではデモ用にランダムまたは固定判定
            finding = await self._evaluate_item(category, check, content, report.auditor_branch)
            
            if finding:
                report.add_finding(finding)
                severity_icon = {
                    AuditSeverity.CRITICAL: "🔴",
                    AuditSeverity.MAJOR: "🟠",
                    AuditSeverity.MINOR: "🟡",
                    AuditSeverity.INFO: "🔵",
                }
                print(f"  {severity_icon[finding.severity]} [{category}] {finding.description}")
            else:
                print(f"  ✅ [{category}] OK")
    
    async def _evaluate_item(
        self,
        category: str,
        check: str,
        content: str,
        auditor_branch: str,
    ) -> Optional[AuditFinding]:
        """
        チェック項目を評価
        
        実際の実装ではLLMで判定する。
        ここではデモ用のダミー実装。
        """
        # デモ: 特定のキーワードで指摘を生成
        if auditor_branch == "rikugun":
            # 陸軍が海軍を監査: 過剰設計チェック
            if category == "現実性" and "k3s" in content.lower():
                return AuditFinding(
                    severity=AuditSeverity.MAJOR,
                    category=category,
                    description="k3s は現在の50ユーザー規模には過剰設計であります",
                    evidence="要件: 50ユーザー、提案: k3sクラスタ",
                    recommendation="Docker Compose から段階的に導入すべきであります",
                )
            if category == "コスト" and "terraform" in content.lower():
                return AuditFinding(
                    severity=AuditSeverity.MINOR,
                    category=category,
                    description="Terraform の学習コストが予算を圧迫する可能性であります",
                    evidence="月額予算: $60",
                    recommendation="Ansible 単体での運用を推奨であります",
                )
        else:
            # 海軍が陸軍を監査: スケーラビリティチェック
            if category == "スケーラビリティ" and "docker-compose" in content.lower():
                return AuditFinding(
                    severity=AuditSeverity.MAJOR,
                    category=category,
                    description="Docker Compose はスケーラビリティに限界がございます",
                    evidence="将来要件: 200ユーザー対応",
                    recommendation="k3s 移行計画を策定いただきたい",
                )
            if category == "自動化" and "manual" in content.lower():
                return AuditFinding(
                    severity=AuditSeverity.MINOR,
                    category=category,
                    description="手動作業が残存しております",
                    evidence="マニュアル手順の存在",
                    recommendation="Ansible で自動化を推奨いたします",
                )
        
        return None
    
    def _determine_result(self, report: AuditReport) -> AuditResult:
        """監査結果を判定"""
        if report.critical_count > 0:
            return AuditResult.FAIL
        elif report.major_count >= 2:
            return AuditResult.FAIL
        elif report.major_count == 1:
            return AuditResult.CONDITIONAL
        else:
            return AuditResult.PASS
    
    def _generate_summary(self, report: AuditReport) -> str:
        """監査サマリーを生成"""
        result_text = {
            AuditResult.PASS: "合格",
            AuditResult.FAIL: "不合格（差し戻し）",
            AuditResult.CONDITIONAL: "条件付き合格",
            AuditResult.PENDING: "保留",
        }
        
        char = get_character(report.auditor_rank)
        
        if report.result == AuditResult.PASS:
            return ZeroTrustDialogue.audit_pass(report.artifact_id, char.name)
        elif report.result == AuditResult.FAIL:
            reasons = [f.description for f in report.findings if f.severity in [AuditSeverity.CRITICAL, AuditSeverity.MAJOR]]
            return ZeroTrustDialogue.audit_fail(report.artifact_id, char.name, "; ".join(reasons[:2]))
        else:
            return f"成果物「{report.artifact_id}」は条件付きで承認。指摘事項への対応を求めます。"
    
    def _save_report(self, report: AuditReport):
        """監査レポートを保存"""
        filepath = self.audit_dir / f"{report.artifact_id}_audit.yaml"
        with open(filepath, "w", encoding="utf-8") as f:
            yaml.dump(report.to_dict(), f, allow_unicode=True, default_flow_style=False)
    
    def _print_result(self, report: AuditReport):
        """監査結果を表示"""
        result_icon = {
            AuditResult.PASS: "✅",
            AuditResult.FAIL: "❌",
            AuditResult.CONDITIONAL: "⚠️",
            AuditResult.PENDING: "⏳",
        }
        
        print("\n" + "=" * 50)
        print(f"監査結果: {result_icon[report.result]} {report.result.value.upper()}")
        print(f"指摘: 🔴{report.critical_count} 🟠{report.major_count} 🟡{report.minor_count}")
        print("-" * 50)
        print(report.summary)
        print("=" * 50)


# ============================================================
# 差し戻しフロー
# ============================================================

@dataclass
class RemandRequest:
    """差し戻し要求"""
    artifact_id: str
    audit_report: AuditReport
    requested_changes: list[str] = field(default_factory=list)
    deadline: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "artifact_id": self.artifact_id,
            "audit_result": self.audit_report.result.value,
            "requested_changes": self.requested_changes,
            "deadline": self.deadline,
            "findings_count": len(self.audit_report.findings),
        }


async def process_remand(report: AuditReport) -> Optional[RemandRequest]:
    """
    差し戻し処理
    
    監査不合格の場合、差し戻し要求を生成
    """
    if report.result not in [AuditResult.FAIL, AuditResult.CONDITIONAL]:
        return None
    
    requested_changes = []
    for finding in report.findings:
        if finding.severity in [AuditSeverity.CRITICAL, AuditSeverity.MAJOR]:
            requested_changes.append(f"[{finding.category}] {finding.recommendation}")
    
    remand = RemandRequest(
        artifact_id=report.artifact_id,
        audit_report=report,
        requested_changes=requested_changes,
    )
    
    print("\n" + "🔄" * 25)
    print("  差し戻し要求")
    print("🔄" * 25)
    print(f"\n成果物: {remand.artifact_id}")
    print("\n修正要求:")
    for i, change in enumerate(remand.requested_changes, 1):
        print(f"  {i}. {change}")
    
    return remand


# ============================================================
# デモ・テスト
# ============================================================

async def demo():
    """監査デモ"""
    print("\n" + "=" * 60)
    print("🔍 監査モジュール デモ")
    print("=" * 60)
    
    manager = AuditManager()
    
    # 海軍成果物を陸軍が監査
    kaigun_artifact = """
    提案: k3s クラスタによるMinecraftサーバー基盤
    
    コンポーネント:
    - k3s クラスタ（3ノード）
    - Terraform による IaC
    - Prometheus/Grafana 監視
    - GitHub Actions CI/CD
    
    対象ユーザー: 50名（将来200名対応）
    """
    
    report = await manager.audit(
        artifact_id="PROPOSAL-001",
        artifact_type="proposal",
        artifact_content=kaigun_artifact,
        artifact_branch="kaigun",
    )
    
    # 不合格の場合は差し戻し
    if report.result == AuditResult.FAIL:
        await process_remand(report)


if __name__ == "__main__":
    asyncio.run(demo())
