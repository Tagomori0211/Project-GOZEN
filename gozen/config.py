"""
Project GOZEN - 設定モジュール

階級体系、モデル設定、セキュリティレベル別構成、課金方式を一元管理する。

SecurityLevel:
  PUBLIC       - API利用可（Claude API / Gemini API）
  CONFIDENTIAL - オンプレ必須（Ollama / Qwen）
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
    LOCAL = "local"                # ローカルLLM（コスト0）


class InvocationMethod(Enum):
    """呼び出し方法"""
    CLAUDE_CODE_CLI = "claude_code_cli"
    ANTHROPIC_API = "anthropic_api"
    GEMINI_API = "gemini_api"
    LOCAL_LLM = "local_llm"
    MOCK = "mock"


class SecurityLevel(Enum):
    """セキュリティレベル"""
    PUBLIC = "public"              # API許可
    CONFIDENTIAL = "confidential"  # オンプレ必須
    MOCK = "mock"                  # モック（検証用）


class InferenceBackend(Enum):
    """推論バックエンド"""
    CLAUDE_API = "claude_api"
    GEMINI_API = "gemini_api"
    OLLAMA_LOCAL = "ollama_local"
    MOCK = "mock"


# ============================================================
# InferenceBackend → 既存Enum マッピング（後方互換用）
# ============================================================

_BACKEND_TO_METHOD: dict[InferenceBackend, InvocationMethod] = {
    InferenceBackend.CLAUDE_API: InvocationMethod.ANTHROPIC_API,
    InferenceBackend.GEMINI_API: InvocationMethod.GEMINI_API,
    InferenceBackend.OLLAMA_LOCAL: InvocationMethod.LOCAL_LLM,
    InferenceBackend.MOCK: InvocationMethod.MOCK,
}

_BACKEND_TO_BILLING: dict[InferenceBackend, BillingType] = {
    InferenceBackend.CLAUDE_API: BillingType.API,
    InferenceBackend.GEMINI_API: BillingType.API,
    InferenceBackend.OLLAMA_LOCAL: BillingType.LOCAL,
    InferenceBackend.MOCK: BillingType.LOCAL,
}


@dataclass(frozen=True)
class RankConfig:
    """階級ごとの設定（イミュータブル）"""
    name_ja: str
    name_en: str
    branch: Branch
    model: str
    billing: BillingType
    method: InvocationMethod
    backend: InferenceBackend = InferenceBackend.OLLAMA_LOCAL
    parallel: int = 1
    cost_per_mtok_input: float = 0.0
    cost_per_mtok_output: float = 0.0


def _rc(
    name_ja: str,
    name_en: str,
    branch: Branch,
    model: str,
    backend: InferenceBackend,
    parallel: int = 1,
    cost_per_mtok_input: float = 0.0,
    cost_per_mtok_output: float = 0.0,
) -> RankConfig:
    """RankConfig生成ヘルパー（backendからmethod/billingを自動導出）"""
    return RankConfig(
        name_ja=name_ja,
        name_en=name_en,
        branch=branch,
        model=model,
        billing=_BACKEND_TO_BILLING[backend],
        method=_BACKEND_TO_METHOD[backend],
        backend=backend,
        parallel=parallel,
        cost_per_mtok_input=cost_per_mtok_input,
        cost_per_mtok_output=cost_per_mtok_output,
    )


# ============================================================
# セキュリティレベル別 階級×モデル×課金方式 マッピング
#
# 設計思想:
#   - 参謀層は最上位モデルで本気の議論
#   - 実行層は軽量モデルでコスト効率重視
#   - CONFIDENTIALは逐次ロード前提で32B/14B/7Bの階層化
# ============================================================

RANK_CONFIGS: dict[SecurityLevel, dict[str, RankConfig]] = {
    SecurityLevel.PUBLIC: {
        # === 参謀層（最上位モデル・高度な推論） ===
        # NOTE: Claude API 一時停止中のため Gemini Pro を使用
        "kaigun_sanbou": _rc(
            name_ja="海軍参謀", name_en="Naval Staff",
            branch=Branch.KAIGUN,
            model="gemini-1.5-pro",
            backend=InferenceBackend.GEMINI_API,
        ),
        "rikugun_sanbou": _rc(
            name_ja="陸軍参謀", name_en="Army Staff",
            branch=Branch.RIKUGUN,
            model="gemini-1.5-pro",
            backend=InferenceBackend.GEMINI_API,
        ),

        # === 書記（軽量・高速） ===
        # NOTE: Claude API 一時停止中のため Gemini Flash を使用
        "shoki": _rc(
            name_ja="書記", name_en="Clerk",
            branch=Branch.KAIGUN,
            model="gemini-1.5-flash",
            backend=InferenceBackend.GEMINI_API,
        ),
    },
    SecurityLevel.CONFIDENTIAL: {
        # === 参謀層（32B・逐次ロード） ===
        "kaigun_sanbou": _rc(
            name_ja="海軍参謀", name_en="Naval Staff",
            branch=Branch.KAIGUN,
            model="qwen2.5:32b-instruct-q4_K_M",
            backend=InferenceBackend.OLLAMA_LOCAL,
        ),
        "rikugun_sanbou": _rc(
            name_ja="陸軍参謀", name_en="Army Staff",
            branch=Branch.RIKUGUN,
            model="qwen2.5:32b-instruct-q4_K_M",
            backend=InferenceBackend.OLLAMA_LOCAL,
        ),

        # === 書記（7B・高速） ===
        "shoki": _rc(
            name_ja="書記", name_en="Clerk",
            branch=Branch.KAIGUN,
            model="qwen2.5:7b-instruct-q8_0",
            backend=InferenceBackend.OLLAMA_LOCAL,
        ),
    },
    SecurityLevel.MOCK: {
        "kaigun_sanbou": _rc("海軍参謀", "Naval Staff", Branch.KAIGUN, "mock-model", InferenceBackend.MOCK),
        "rikugun_sanbou": _rc("陸軍参謀", "Army Staff", Branch.RIKUGUN, "mock-model", InferenceBackend.MOCK),
        "shoki": _rc("書記", "Clerk", Branch.KAIGUN, "mock-model", InferenceBackend.MOCK),
    },
}


# ============================================================
# 後方互換: デフォルトセキュリティレベル
# ============================================================

DEFAULT_SECURITY_LEVEL: SecurityLevel = SecurityLevel.PUBLIC

# 既存コード互換: RANK_CONFIG (singular) → PUBLIC設定
RANK_CONFIG: dict[str, RankConfig] = {
    **RANK_CONFIGS[DEFAULT_SECURITY_LEVEL],
}

# 階級名エイリアス（将来の名称変更対応用）
_RANK_ALIASES: dict[str, str] = {}


# ============================================================
# Server Configuration
# ============================================================

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 9000


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
    exchange_rate: float = 150.0

    @property
    def total(self) -> float:
        return self.subscription

    @property
    def total_jpy(self) -> float:
        return self.total * self.exchange_rate


DEFAULT_COST_ESTIMATE = CostEstimate()


# ============================================================
# ユーティリティ関数
# ============================================================

def _resolve_rank(rank: str) -> str:
    """階級名のエイリアスを解決する"""
    return _RANK_ALIASES.get(rank, rank)


def get_rank_config(
    rank: str,
    security_level: Optional[SecurityLevel] = None,
) -> RankConfig:
    """セキュリティレベルに応じた階級設定を取得"""
    level = security_level or DEFAULT_SECURITY_LEVEL
    rank = _resolve_rank(rank)

    configs = RANK_CONFIGS[level]
    if rank not in configs:
        raise ValueError(
            f"Unknown rank: {rank}. "
            f"Valid ranks for {level.value}: {list(configs.keys())}"
        )
    return configs[rank]


def get_model_for_rank(
    rank: str,
    security_level: Optional[SecurityLevel] = None,
) -> str:
    """階級に対応するモデル名を取得"""
    return get_rank_config(rank, security_level).model


def get_parallel_count(
    rank: str,
    security_level: Optional[SecurityLevel] = None,
) -> int:
    """階級の並列数を取得"""
    return get_rank_config(rank, security_level).parallel


def estimate_cost(
    input_tokens: int,
    output_tokens: int,
    rank: str,
    security_level: Optional[SecurityLevel] = None,
) -> float:
    """API呼び出しのコスト見積もり（USD）"""
    config = get_rank_config(rank, security_level)

    if config.billing in (BillingType.SUBSCRIPTION, BillingType.GCP_FREE, BillingType.LOCAL):
        return 0.0

    input_cost = (input_tokens / 1_000_000) * config.cost_per_mtok_input
    output_cost = (output_tokens / 1_000_000) * config.cost_per_mtok_output
    return input_cost + output_cost


def get_ranks_by_branch(
    branch: Branch,
    security_level: Optional[SecurityLevel] = None,
) -> list[str]:
    """軍種別の階級一覧を取得"""
    level = security_level or DEFAULT_SECURITY_LEVEL
    configs = RANK_CONFIGS[level]
    return [rank for rank, cfg in configs.items() if cfg.branch == branch]


def get_all_ranks(
    security_level: Optional[SecurityLevel] = None,
) -> list[str]:
    """全階級名を取得"""
    level = security_level or DEFAULT_SECURITY_LEVEL
    return list(RANK_CONFIGS[level].keys())


def print_rank_table(security_level: Optional[SecurityLevel] = None) -> None:
    """階級表を表示（デバッグ用）"""
    level = security_level or DEFAULT_SECURITY_LEVEL
    configs = RANK_CONFIGS[level]

    print(f"\n{'=' * 90}")
    print(f"階級体系 × モデル × 課金方式  [SecurityLevel: {level.value}]")
    print("=" * 90)
    print(f"{'階級':<12} {'モデル':<40} {'バックエンド':<16} {'並列':<6}")
    print("-" * 90)

    for rank, config in configs.items():
        print(
            f"{config.name_ja:<10} "
            f"{config.model:<40} "
            f"{config.backend.value:<16} "
            f"x{config.parallel}"
        )

    print("-" * 90)
    if level == SecurityLevel.PUBLIC:
        print(f"月額見込み: ${DEFAULT_COST_ESTIMATE.total:.0f} (¥{DEFAULT_COST_ESTIMATE.total_jpy:,.0f})")
    else:
        print("月額見込み: $0 (ローカル推論)")
    print("=" * 90)


if __name__ == "__main__":
    print_rank_table(SecurityLevel.PUBLIC)
    print()
    print_rank_table(SecurityLevel.CONFIDENTIAL)
