"""
Project GOZEN - 御前会議

海軍参謀（Claude）と陸軍参謀（Gemini）の建設的対立を通じて、
最高のエンジニアリング決定を導くマルチエージェントシステム。

「陸軍として海軍の提案に反対である」
"""

# ============================================================
# .env ファイル自動読み込み（最初に実行）
# ============================================================
import os
from pathlib import Path

def _load_dotenv() -> None:
    """プロジェクトルートの .env ファイルを読み込む"""
    try:
        from dotenv import load_dotenv

        # このファイル（__init__.py）の親の親 = プロジェクトルート
        project_root = Path(__file__).parent.parent
        env_path = project_root / ".env"

        if env_path.exists():
            load_dotenv(env_path)
            # デバッグ用（本番では削除可）
            if os.getenv("GOZEN_DEBUG"):
                print(f"[GOZEN] .env loaded from: {env_path}")
        else:
            # .env が見つからない場合、カレントディレクトリも探す
            cwd_env = Path.cwd() / ".env"
            if cwd_env.exists():
                load_dotenv(cwd_env)
                if os.getenv("GOZEN_DEBUG"):
                    print(f"[GOZEN] .env loaded from: {cwd_env}")

    except ImportError:
        # python-dotenv がインストールされていない場合
        # 環境変数が直接設定されていることを期待
        pass

# モジュール読み込み時に自動実行
_load_dotenv()

# ============================================================

__version__ = "2.1.0"
__author__ = "tagomori (田籠)"
__project__ = "Project GOZEN"

from gozen.gozen_orchestrator import GozenOrchestrator

from gozen.config import (
    RANK_CONFIG,
    RANK_CONFIGS,
    DEFAULT_SECURITY_LEVEL,
    InferenceBackend,
    SecurityLevel,
    estimate_cost,
    get_model_for_rank,
    get_rank_config,
)

from gozen.character import (
    ZeroTrustDialogue,
    format_message,
    get_character,
)

from gozen.council_mode import (
    ArbitrationResult,
    CouncilManager,
    CouncilMode,
    PCAState,
    resolve_deadlock,
    run_council,
    run_pca_council,
)

from gozen.api_client import (
    execute_parallel,
    get_client,
    get_cost_tracker,
)

from gozen.audit import (
    AuditManager,
    AuditResult,
    process_remand,
)

from gozen.dashboard import (
    DashboardWriter,
    get_dashboard,
)

__all__ = [
    # orchestrator
    "GozenOrchestrator",
    # config
    "RANK_CONFIG",
    "RANK_CONFIGS",
    "DEFAULT_SECURITY_LEVEL",
    "SecurityLevel",
    "InferenceBackend",
    "get_rank_config",
    "get_model_for_rank",
    "estimate_cost",
    # character
    "get_character",
    "format_message",
    "ZeroTrustDialogue",
    # council_mode
    "ArbitrationResult",
    "CouncilMode",
    "CouncilManager",
    "PCAState",
    "run_council",
    "run_pca_council",
    "resolve_deadlock",
    # api_client
    "get_client",
    "get_cost_tracker",
    "execute_parallel",
    # audit
    "AuditManager",
    "AuditResult",
    "process_remand",
    # dashboard
    "DashboardWriter",
    "get_dashboard",
]
