"""
Project GOZEN - 御前会議

海軍参謀（Claude）と陸軍参謀（Gemini）の建設的対立を通じて、
最高のエンジニアリング決定を導くマルチエージェントシステム。

「陸軍として海軍の提案に反対である」
"""

__version__ = '2.0.0'
__author__ = 'tagomori (田籠)'
__project__ = 'Project GOZEN'

from gozen.gozen_orchestrator import GozenOrchestrator

from gozen.config import (
    RANK_CONFIG,
    get_rank_config,
    get_model_for_rank,
    estimate_cost,
)

from gozen.character import (
    get_character,
    format_message,
    ZeroTrustDialogue,
)

from gozen.council_mode import (
    CouncilMode,
    CouncilManager,
    run_council,
)

from gozen.api_client import (
    get_client,
    get_cost_tracker,
    execute_parallel,
)

from gozen.audit import (
    AuditManager,
    AuditResult,
    process_remand,
)

__all__ = [
    # orchestrator
    "GozenOrchestrator",
    # config
    "RANK_CONFIG",
    "get_rank_config",
    "get_model_for_rank",
    "estimate_cost",
    # character
    "get_character",
    "format_message",
    "ZeroTrustDialogue",
    # council_mode
    "CouncilMode",
    "CouncilManager",
    "run_council",
    # api_client
    "get_client",
    "get_cost_tracker",
    "execute_parallel",
    # audit
    "AuditManager",
    "AuditResult",
    "process_remand",
]
