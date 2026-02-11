"""
Project GOZEN - 御前会議モード（PCAサイクル）

PCA（Propose-Challenge-Arbitrate）サイクルを実装する。

フロー:
  P: 海軍参謀が提案
  C: 陸軍参謀が異議
  A: 国家元首が裁定
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional, Literal

class CouncilMode(Enum):
    """御前会議モード"""
    COUNCIL = "council"
    DRYRUN = "dryrun"

@dataclass
class AdoptionJudgment:
    """採択判断"""
    result: Literal["adopt", "reject", "reconsider"]
    comment: str = ""

@dataclass
class CouncilSessionState:
    """御前会議セッション状態"""
    session_id: str
    mission: str
    round: int = 1
    max_rounds: int = 5
    status: str = "initialized"
    history: list[dict] = field(default_factory=list)

class ArbitrationResult(Enum):
    """裁定結果"""
    ADOPT_KAIGUN = "adopt_kaigun"      # 海軍案採用
    ADOPT_RIKUGUN = "adopt_rikugun"    # 陸軍案採用
    INTEGRATE = "integrate"             # 統合指示（書記起草へ）
    REJECT = "reject"                   # 却下・終了
