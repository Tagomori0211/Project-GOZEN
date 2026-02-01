"""
Project GOZEN - 設定モジュール

階級体系、モデル設定、課金方式を一元管理する。
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class Branch(Enum):
    """軍種"""
    KAIGUN = "kaigun"   # 海軍（Claude系）
    RIKUGUN = "rikugun"  # 陸軍（Gemini系）


class BillingType(Enum):
    """課金方式"""
    SUBSCRIPTION = "subscription"  # サブスク（Pro/Max）
    API = "api"                    # API従量課金
    GCP_FREE = "gcp_free"          # GCP無料枠


class InvocationMethod(Enum):
    """呼び出し方法"""
    CLAUDE_CODE_CLI = "claude_code_cli"
    ANTHROPIC_API = "anthropic_api"
    GEMINI_API = "gemini_api"


@dataclass(frozen=True)
class RankConfig:
    """階級ごとの設定（イミュータブル）"""
    name_ja: str
    name_en: str
    branch: Branch
    model: str
    billing: BillingType
    method: InvocationMethod
    parallel: int = 1
    cost_per_mtok_input: float = 0.0
    cost_per_mtok_output: float = 0.0


# ============================================================
# 階級×モデル×課金方式 マッピング
# ============================================================

RANK_CONFIG: dict[str, RankConfig] = {
    # === 海軍系統（Claude） ===
    "kaigun_sanbou": RankConfig(
        name_ja="海軍参謀",
        name_en="Naval Staff",
        branch=Branch.KAIGUN,
        model="claude-opus-4-5-20250514",
        billing=BillingType.SUBSCRIPTION,
        method=InvocationMethod.CLAUDE_CODE_CLI,
        parallel=1,
        cost_per_mtok_input=0.0,
        cost_per_mtok_output=0.0,
    ),
    "teitoku": RankConfig(
        name_ja="提督",
        name_en="Admiral",
        branch=Branch.KAIGUN,
        model="claude-sonnet-4-5-20250514",
        billing=BillingType.SUBSCRIPTION,
        method=InvocationMethod.CLAUDE_CODE_CLI,
        parallel=1,
        cost_per_mtok_input=0.0,
        cost_per_mtok_output=0.0,
    ),
    "kancho": RankConfig(
        name_ja="艦長",
        name_en="Captain",
        branch=Branch.KAIGUN,
        model="claude-sonnet-4-5-20250514",
        billing=BillingType.SUBSCRIPTION,
        method=InvocationMethod.CLAUDE_CODE_CLI,
        parallel=1,
        cost_per_mtok_input=0.0,
        cost_per_mtok_output=0.0,
    ),
    "kaihei": RankConfig(
        name_ja="海兵",
        name_en="Marine",
        branch=Branch.KAIGUN,
        model="claude-haiku-4-5-20251001",
        billing=BillingType.SUBSCRIPTION,
        method=InvocationMethod.CLAUDE_CODE_CLI,
        parallel=8,
        cost_per_mtok_input=0.0,
        cost_per_mtok_output=0.0,
    ),

    # === 陸軍系統（Gemini） ===
    "rikugun_sanbou": RankConfig(
        name_ja="陸軍参謀",
        name_en="Army Staff",
        branch=Branch.RIKUGUN,
        model="gemini-2.5-pro",
        billing=BillingType.GCP_FREE,
        method=InvocationMethod.GEMINI_API,
        parallel=1,
        cost_per_mtok_input=0.0,
        cost_per_mtok_output=0.0,
    ),
    "shikan": RankConfig(
        name_ja="士官",
        name_en="Officer",
        branch=Branch.RIKUGUN,
        model="gemini-2.5-flash",
        billing=BillingType.API,
        method=InvocationMethod.GEMINI_API,
        parallel=1,
        cost_per_mtok_input=0.15,
        cost_per_mtok_output=0.60,
    ),
    "hohei": RankConfig(
        name_ja="歩兵",
        name_en="Infantry",
        branch=Branch.RIKUGUN,
        model="gemini-2.5-flash",
        billing=BillingType.API,
        method=InvocationMethod.GEMINI_API,
        parallel=4,
        cost_per_mtok_input=0.15,
        cost_per_mtok_output=0.60,
    ),
}


# ============================================================
# API Tier設定（Anthropic）
# ============================================================

@dataclass(frozen=True)
class TierConfig:
    """APIティア設定"""
    name: str
    deposit_usd: float
    rpm: int
    tpm: int


API_TIERS: dict[int, TierConfig] = {
    1: TierConfig("Tier 1", 5.0, 50, 40_000),
    2: TierConfig("Tier 2", 40.0, 1_000, 80_000),
    3: TierConfig("Tier 3", 200.0, 2_000, 160_000),
    4: TierConfig("Tier 4", 400.0, 4_000, 400_000),
}


# ============================================================
# 月額コスト試算
# ============================================================

@dataclass
class CostEstimate:
    """月額コスト見積もり"""
    subscription: float = 20.0
    teitoku_kancho: float = 0.0
    kaihei: float = 0.0
    hohei: float = 7.5
    exchange_rate: float = 150.0

    @property
    def total(self) -> float:
        return self.subscription + self.teitoku_kancho + self.kaihei + self.hohei

    @property
    def total_jpy(self) -> float:
        return self.total * self.exchange_rate


DEFAULT_COST_ESTIMATE = CostEstimate()


# ============================================================
# ユーティリティ関数
# ============================================================

def get_rank_config(rank: str) -> RankConfig:
    """階級設定を取得"""
    if rank not in RANK_CONFIG:
        raise ValueError(f"Unknown rank: {rank}. Valid ranks: {list(RANK_CONFIG.keys())}")
    return RANK_CONFIG[rank]


def get_model_for_rank(rank: str) -> str:
    """階級に対応するモデル名を取得"""
    return get_rank_config(rank).model


def get_parallel_count(rank: str) -> int:
    """階級の並列数を取得"""
    return get_rank_config(rank).parallel


def estimate_cost(input_tokens: int, output_tokens: int, rank: str) -> float:
    """API呼び出しのコスト見積もり（USD）"""
    config = get_rank_config(rank)

    if config.billing == BillingType.SUBSCRIPTION:
        return 0.0
    if config.billing == BillingType.GCP_FREE:
        return 0.0

    input_cost = (input_tokens / 1_000_000) * config.cost_per_mtok_input
    output_cost = (output_tokens / 1_000_000) * config.cost_per_mtok_output
    return input_cost + output_cost


def get_ranks_by_branch(branch: Branch) -> list[str]:
    """軍種別の階級一覧を取得"""
    return [rank for rank, cfg in RANK_CONFIG.items() if cfg.branch == branch]


def print_rank_table() -> None:
    """階級表を表示（デバッグ用）"""
    print("\n" + "=" * 80)
    print("階級体系 × モデル × 課金方式")
    print("=" * 80)
    print(f"{'階級':<12} {'モデル':<35} {'課金':<12} {'並列':<6}")
    print("-" * 80)

    for rank, config in RANK_CONFIG.items():
        print(f"{config.name_ja:<10} {config.model:<35} {config.billing.value:<12} ×{config.parallel}")

    print("-" * 80)
    print(f"月額見込み: ${DEFAULT_COST_ESTIMATE.total:.0f} (¥{DEFAULT_COST_ESTIMATE.total_jpy:,.0f})")
    print("=" * 80)


if __name__ == "__main__":
    print_rank_table()
