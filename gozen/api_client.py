"""
Project GOZEN - API クライアントモジュール

Anthropic API と Gemini API のラッパー。
指数バックオフ、リトライ、コスト追跡を実装。
"""

from __future__ import annotations

import asyncio
import json
import os
import random
import shutil
import time
import warnings
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from gozen.config import (
    BillingType,
    InvocationMethod,
    RankConfig,
    estimate_cost,
    get_rank_config,
)


# ============================================================
# カスタム例外
# ============================================================

class APIError(Exception):
    """API エラー基底クラス"""
    pass


class RateLimitError(APIError):
    """レート制限エラー"""
    pass


class AuthenticationError(APIError):
    """認証エラー"""
    pass


# ============================================================
# コスト追跡
# ============================================================

@dataclass
class APICallRecord:
    """API呼び出し記録"""
    rank: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    success: bool = True
    error: Optional[str] = None
    latency_ms: int = 0


class CostTracker:
    """コスト追跡クラス"""

    def __init__(self) -> None:
        self._records: list[APICallRecord] = []
        self._session_start = datetime.now()

    def record(self, record: APICallRecord) -> None:
        """記録を追加"""
        self._records.append(record)

    @property
    def records(self) -> list[APICallRecord]:
        return list(self._records)

    @property
    def total_cost(self) -> float:
        return sum(r.cost_usd for r in self._records if r.success)

    @property
    def total_input_tokens(self) -> int:
        return sum(r.input_tokens for r in self._records if r.success)

    @property
    def total_output_tokens(self) -> int:
        return sum(r.output_tokens for r in self._records if r.success)

    @property
    def call_count(self) -> int:
        return len(self._records)

    @property
    def error_count(self) -> int:
        return sum(1 for r in self._records if not r.success)

    def get_summary(self) -> dict[str, Any]:
        return {
            "session_start": self._session_start.isoformat(),
            "total_calls": self.call_count,
            "errors": self.error_count,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_cost_usd": round(self.total_cost, 4),
            "total_cost_jpy": round(self.total_cost * 150, 0),
        }

    def print_summary(self) -> None:
        summary = self.get_summary()
        print("\n" + "=" * 50)
        print("💰 コスト追跡サマリー")
        print("=" * 50)
        print(f"セッション開始: {summary['session_start']}")
        print(f"総呼び出し: {summary['total_calls']} (エラー: {summary['errors']})")
        print(f"入力トークン: {summary['total_input_tokens']:,}")
        print(f"出力トークン: {summary['total_output_tokens']:,}")
        print(f"累計コスト: ${summary['total_cost_usd']:.4f} (¥{summary['total_cost_jpy']:.0f})")
        print("=" * 50)

    def clear(self) -> None:
        """記録をクリア"""
        self._records.clear()
        self._session_start = datetime.now()


# グローバルコストトラッカー
_cost_tracker: Optional[CostTracker] = None


def get_cost_tracker() -> CostTracker:
    """コストトラッカーを取得（シングルトン）"""
    global _cost_tracker
    if _cost_tracker is None:
        _cost_tracker = CostTracker()
    return _cost_tracker


# ============================================================
# リトライ設定
# ============================================================

@dataclass(frozen=True)
class RetryConfig:
    """リトライ設定"""
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True


def calculate_delay(retry_count: int, config: RetryConfig) -> float:
    """指数バックオフでリトライ間隔を計算"""
    delay = config.base_delay * (config.exponential_base ** retry_count)
    delay = min(delay, config.max_delay)

    if config.jitter:
        delay *= (0.5 + random.random())

    return delay


# ============================================================
# 抽象基底クラス
# ============================================================

from gozen.config import SecurityLevel

class BaseAPIClient(ABC):
    """API クライアント基底クラス"""

    def __init__(
        self,
        rank: str,
        security_level: Optional[SecurityLevel] = None,
        retry_config: Optional[RetryConfig] = None
    ) -> None:
        self.rank = rank
        self.config: RankConfig = get_rank_config(rank, security_level)
        self.retry_config = retry_config or RetryConfig()
        self.tracker = get_cost_tracker()

    @abstractmethod
    async def _call_api(self, prompt: str, **kwargs: Any) -> dict[str, Any]:
        """実際のAPI呼び出し（サブクラスで実装）"""
        pass

    async def call(self, prompt: str, **kwargs: Any) -> dict[str, Any]:
        """リトライ付きAPI呼び出し"""
        last_error: Optional[Exception] = None
        start_time = time.time()

        for retry in range(self.retry_config.max_retries + 1):
            try:
                result = await self._call_api(prompt, **kwargs)
                latency = int((time.time() - start_time) * 1000)
                self._record_success(result, latency)
                return result

            except AuthenticationError:
                # 認証・課金エラーはリトライしても無意味
                raise

            except RateLimitError as e:
                last_error = e
                if retry < self.retry_config.max_retries:
                    delay = calculate_delay(retry, self.retry_config)
                    print(f"⚠️ レート制限。{delay:.1f}秒後にリトライ... ({retry + 1}/{self.retry_config.max_retries})")
                    await asyncio.sleep(delay)

            except APIError as e:
                last_error = e
                self._record_error(str(e))
                if retry < self.retry_config.max_retries:
                    delay = calculate_delay(retry, self.retry_config)
                    print(f"⚠️ APIエラー: {e}。{delay:.1f}秒後にリトライ...")
                    await asyncio.sleep(delay)

        raise last_error or APIError("Unknown error after retries")

    def _record_success(self, result: dict[str, Any], latency_ms: int) -> None:
        usage = result.get("usage", {})
        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)

        record = APICallRecord(
            rank=self.rank,
            model=self.config.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=estimate_cost(input_tokens, output_tokens, self.rank),
            latency_ms=latency_ms,
            success=True,
        )
        self.tracker.record(record)

    def _record_error(self, error: str) -> None:
        record = APICallRecord(
            rank=self.rank,
            model=self.config.model,
            input_tokens=0,
            output_tokens=0,
            cost_usd=0.0,
            success=False,
            error=error,
        )
        self.tracker.record(record)


# ============================================================
# Anthropic API クライアント
# ============================================================

class AnthropicClient(BaseAPIClient):
    """Anthropic API クライアント（海兵、提督、艦長用）"""

    def __init__(self, rank: str, security_level: Optional[SecurityLevel] = None, retry_config: Optional[RetryConfig] = None) -> None:
        super().__init__(rank, security_level, retry_config)
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                from anthropic import AsyncAnthropic
                self._client = AsyncAnthropic(api_key=self.api_key)
            except ImportError:
                raise APIError("anthropic パッケージがインストールされていません: pip install anthropic")
        return self._client

    async def _call_api(self, prompt: str, **kwargs: Any) -> dict[str, Any]:
        if not self.api_key:
            raise AuthenticationError("ANTHROPIC_API_KEY が設定されていません")

        client = self._get_client()

        try:
            response = await client.messages.create(
                model=self.config.model,
                max_tokens=kwargs.get("max_tokens", 4096),
                messages=[{"role": "user", "content": prompt}],
                system=kwargs.get("system", ""),
            )

            return {
                "content": response.content[0].text if response.content else "",
                "usage": {
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                },
                "model": response.model,
                "stop_reason": response.stop_reason,
            }

        except Exception as e:
            error_str = str(e).lower()
            if "rate" in error_str or "429" in error_str:
                raise RateLimitError(str(e))
            elif "auth" in error_str or "401" in error_str or "403" in error_str:
                raise AuthenticationError(str(e))
            elif "credit" in error_str or "balance" in error_str or "billing" in error_str:
                raise AuthenticationError(
                    f"Anthropic APIクレジット不足: {e}\n"
                    "ヒント: このランクはCLAUDE_CODE_CLI（サブスク）を使用すべきです。"
                    "config.pyのmethod設定を確認してください。"
                )
            else:
                raise APIError(str(e))


# ============================================================
# Gemini API クライアント
# ============================================================

class GeminiClient(BaseAPIClient):
    """Gemini API クライアント（士官、歩兵、陸軍参謀用）"""

    def __init__(self, rank: str, security_level: Optional[SecurityLevel] = None, retry_config: Optional[RetryConfig] = None) -> None:
        super().__init__(rank, security_level, retry_config)
        self.api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                with warnings.catch_warnings():
                    warnings.filterwarnings("ignore", category=FutureWarning)
                    import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self._client = genai.GenerativeModel(self.config.model)
            except ImportError:
                raise APIError("google-generativeai パッケージがインストールされていません: pip install google-generativeai")
        return self._client

    async def _call_api(self, prompt: str, **kwargs: Any) -> dict[str, Any]:
        if not self.api_key:
            raise AuthenticationError("GOOGLE_API_KEY または GEMINI_API_KEY が設定されていません")

        client = self._get_client()

        try:
            loop = asyncio.get_event_loop()
            # タイムアウトを設定（デフォルト60秒）
            timeout = kwargs.get("timeout", 60)
            
            response = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: client.generate_content(prompt)
                ),
                timeout=timeout
            )

            if not response or not hasattr(response, "text"):
                raise APIError("Gemini API から空の応答が返されました。")

            usage_metadata = getattr(response, "usage_metadata", None)
            input_tokens = getattr(usage_metadata, "prompt_token_count", 0) if usage_metadata else 0
            output_tokens = getattr(usage_metadata, "candidates_token_count", 0) if usage_metadata else 0

            return {
                "content": response.text if response.text else "",
                "usage": {
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                },
                "model": self.config.model,
            }

        except asyncio.TimeoutError:
            raise APIError(f"Gemini API 呼び出しがタイムアウトしました（{timeout}秒）。")
        except Exception as e:
            error_str = str(e).lower()
            if "rate" in error_str or "429" in error_str or "quota" in error_str:
                raise RateLimitError(str(e))
            elif "auth" in error_str or "api key" in error_str:
                raise AuthenticationError(str(e))
            elif "billing" in error_str or "payment" in error_str:
                raise AuthenticationError(str(e))
            else:
                raise APIError(str(e))


# ============================================================
# Claude Code CLI クライアント
# ============================================================

class ClaudeCodeClient(BaseAPIClient):
    """Claude Code CLI クライアント（サブスクリプション枠使用）"""

    DEFAULT_TIMEOUT = 300  # 秒

    def __init__(self, rank: str, security_level: Optional[SecurityLevel] = None, retry_config: Optional[RetryConfig] = None) -> None:
        super().__init__(rank, security_level, retry_config)
        self._claude_bin: Optional[str] = None

    def _find_claude_binary(self) -> str:
        """claude CLI バイナリのパスを検出"""
        if self._claude_bin is None:
            path = shutil.which("claude")
            if path is None:
                raise APIError(
                    "claude CLI が見つかりません。"
                    "Claude Code をインストールしてください: https://docs.anthropic.com/en/docs/claude-code"
                )
            self._claude_bin = path
        return self._claude_bin

    async def _call_api(self, prompt: str, **kwargs: Any) -> dict[str, Any]:
        claude_bin = self._find_claude_binary()
        timeout = kwargs.get("timeout", self.DEFAULT_TIMEOUT)

        cmd = [
            claude_bin,
            "--print",
            "--output-format", "json",
            "--model", self.config.model,
        ]

        system_prompt = kwargs.get("system", "")
        if system_prompt:
            cmd.extend(["--append-system-prompt", system_prompt])

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                proc.communicate(input=prompt.encode("utf-8")),
                timeout=timeout,
            )

        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            raise APIError(f"Claude CLI がタイムアウトしました（{timeout}秒）")

        stdout_text = stdout.decode("utf-8", errors="replace").strip()
        stderr_text = stderr.decode("utf-8", errors="replace").strip()

        # Claude CLI はエラー時も stdout に JSON を返す（stderr は空のことがある）
        if proc.returncode != 0:
            err_msg = stderr_text
            if not err_msg and stdout_text:
                try:
                    data = json.loads(stdout_text)
                    err_msg = data.get("result", stdout_text)
                except json.JSONDecodeError:
                    err_msg = stdout_text
            self._classify_and_raise(err_msg, proc.returncode)

        return self._parse_output(stdout_text)

    def _classify_and_raise(self, stderr_text: str, returncode: int) -> None:
        """stderrからエラーを分類して適切な例外を送出"""
        lower = stderr_text.lower()
        if "rate" in lower or "429" in lower or "too many" in lower:
            raise RateLimitError(f"Claude CLI レート制限: {stderr_text}")
        elif "auth" in lower or "401" in lower or "403" in lower or "unauthorized" in lower:
            raise AuthenticationError(f"Claude CLI 認証エラー: {stderr_text}")
        elif "credit" in lower or "balance" in lower or "billing" in lower:
            raise AuthenticationError(f"Claude CLI クレジット不足: {stderr_text}")
        else:
            raise APIError(f"Claude CLI エラー (code={returncode}): {stderr_text}")

    def _parse_output(self, stdout_text: str) -> dict[str, Any]:
        """CLI JSON出力をパース

        Claude Code の --output-format json 出力形式:
        {
          "type": "result",
          "is_error": false,
          "result": "応答テキスト",
          "total_cost_usd": 0.025,
          "usage": {
            "input_tokens": 100,
            "output_tokens": 200,
            ...
          }
        }
        """
        if not stdout_text:
            raise APIError("Claude CLI から空の出力")

        try:
            data = json.loads(stdout_text)
        except json.JSONDecodeError:
            return {
                "content": stdout_text,
                "usage": {"input_tokens": 0, "output_tokens": 0},
                "model": self.config.model,
                "cost_usd": 0.0,
            }

        # is_error チェック
        if data.get("is_error"):
            error_msg = data.get("result", "不明なCLIエラー")
            self._classify_and_raise(error_msg, 1)

        content = data.get("result", "")
        cost_usd = data.get("total_cost_usd", 0.0)
        usage = data.get("usage", {})

        return {
            "content": content,
            "usage": {
                "input_tokens": usage.get("input_tokens", 0),
                "output_tokens": usage.get("output_tokens", 0),
            },
            "model": self.config.model,
            "cost_usd": cost_usd,
        }

    def _record_success(self, result: dict[str, Any], latency_ms: int) -> None:
        """CLI出力の cost_usd とトークン数を記録"""
        usage = result.get("usage", {})
        record = APICallRecord(
            rank=self.rank,
            model=self.config.model,
            input_tokens=usage.get("input_tokens", 0),
            output_tokens=usage.get("output_tokens", 0),
            cost_usd=result.get("cost_usd", 0.0),
            latency_ms=latency_ms,
            success=True,
        )
        self.tracker.record(record)


# ============================================================
# Ollama (ローカルLLM) クライアント
# ============================================================

class OllamaClient(BaseAPIClient):
    """Ollama ローカルLLM クライアント（全階級共通）"""

    def __init__(self, rank: str, security_level: Optional[SecurityLevel] = None, retry_config: Optional[RetryConfig] = None) -> None:
        super().__init__(rank, security_level, retry_config)
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.num_threads = int(os.getenv("OLLAMA_NUM_THREADS", "16"))
        self._session: Any = None
        self._owns_session: bool = False  # セッション所有権フラグ

    async def __aenter__(self) -> "OllamaClient":
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.close()

    async def _get_session(self) -> Any:
        if self._session is None:
            try:
                import aiohttp
                self._session = aiohttp.ClientSession()
                self._owns_session = True  # 自分で作成したセッション
            except ImportError:
                raise APIError("aiohttp パッケージがインストールされていません: pip install aiohttp")
        return self._session

    @staticmethod
    def _sanitize_llm_output(text: str) -> str:
        """LLM出力のサロゲート等不正Unicodeを除去する"""
        return text.encode("utf-8", errors="replace").decode("utf-8")

    async def _call_api(self, prompt: str, **kwargs: Any) -> dict[str, Any]:
        session = await self._get_session()
        url = f"{self.base_url}/api/generate"

        payload: dict[str, Any] = {
            "model": self.config.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_thread": self.num_threads,
            },
        }

        system_prompt = kwargs.get("system", "")
        if system_prompt:
            payload["system"] = system_prompt

        try:
            import aiohttp
            async with session.post(url, json=payload) as resp:
                if resp.status == 404:
                    raise APIError(
                        f"Ollama モデル未取得: {self.config.model}\n"
                        f"ヒント: ollama pull {self.config.model} を実行してください。"
                    )
                if resp.status != 200:
                    body = await resp.text()
                    raise APIError(f"Ollama エラー (HTTP {resp.status}): {body}")

                data = await resp.json()

        except aiohttp.ClientConnectorError as e:
            raise APIError(
                f"Ollama に接続できません ({self.base_url}): {e}\n"
                "ヒント: ollama serve が起動しているか確認してください。"
            )

        # LLM出力はサロゲート等の不正Unicodeを含みうるため即座にサニタイズ
        content = self._sanitize_llm_output(data.get("response", ""))
        eval_count = data.get("eval_count", 0)
        prompt_eval_count = data.get("prompt_eval_count", 0)

        return {
            "content": content,
            "usage": {
                "input_tokens": prompt_eval_count,
                "output_tokens": eval_count,
            },
            "model": data.get("model", self.config.model),
        }

    async def close(self) -> None:
        """セッションを閉じる"""
        if self._session is not None and self._owns_session:
            await self._session.close()
            self._session = None
            self._owns_session = False

    async def call(self, prompt: str, **kwargs: Any) -> dict[str, Any]:
        """リトライ付きAPI呼び出し（セッション自動クローズ）"""
        try:
            return await super().call(prompt, **kwargs)
        finally:
            await self.close()


# ============================================================
# Mock クライアント (検証用)
# ============================================================

class MockClient(BaseAPIClient):
    """Mock クライアント（検証用）"""
    
    def __init__(self, rank: str, security_level: Optional[SecurityLevel] = None, retry_config: Optional[RetryConfig] = None) -> None:
        super().__init__(rank, security_level, retry_config)

    async def _call_api(self, prompt: str, **kwargs: Any) -> dict[str, Any]:
        # プロンプトの内容に応じて構造化データを生成
        await asyncio.sleep(1.0) # 擬似レイテンシ
        
        lower_prompt = prompt.lower()
        
        if "提案" in prompt or "proposal" in lower_prompt:
            content = json.dumps({
                "title": "【Mock】次世代システム基盤の構築",
                "summary": "クラウドネイティブな構成を採用し、スケーラビリティと保守性を極限まで高めます。k8sとArgoCDを主軸に据えます。",
                "key_points": ["Kubernetesによる自動復旧", "GitOpsによる完全自動デプロイ", "マイクロサービスアーキテクチャ"]
            }, ensure_ascii=False)
        elif "異議" in prompt or "objection" in lower_prompt:
             content = json.dumps({
                "title": "【Mock】コストと運用の懸念",
                "summary": "k8sはオーバーエンジニアリングです。現在の要員スキルと予算を考慮すると、VMベースのシンプルな構成が現実的です。",
                "key_points": ["学習コストの高さ", "クラウド破産の回避", "既存資産の有効活用"]
            }, ensure_ascii=False)
        elif "統合" in prompt or "synthesize" in lower_prompt or "integrated" in lower_prompt:
            content = json.dumps({
                "title": "【Mock】段階的近代化案",
                "summary": "海軍の理想（k8s）を認めつつも、陸軍の懸念を考慮し、まずは一部の主要機能をマネージドk8sで先行実装し、残りをVMで維持する段階的移行を提案します。",
                "key_points": ["マネージドサービスの活用", "ハイブリッド構成", "段階的なスキル転換"]
            }, ensure_ascii=False)
        elif "公文書" in prompt or "official" in lower_prompt:
            content = json.dumps({
                "markdown_content": "機密第一〇二四号\n令和六年二月十一日\n全軍将兵 殿\n\n【御前会議決定公文書】\n\n一、本件、天憲ノ裁可に基き「段階的近代化案」を正式に採択ス。\n二、各兵団は速やかに実行準備を整ふべし。\n\n以上",
                "yaml_content": {"status": "approved", "session_id": "MOCK-SESSION"},
                "filename": "mock_decision.md"
            }, ensure_ascii=False)
        else:
            content = "モックの自由記述応答ナリ。任務成功を祈ル。"

        return {
            "content": content,
            "usage": {"input_tokens": 100, "output_tokens": 100},
            "model": "mock-model",
        }


# ============================================================
# クライアントファクトリ
# ============================================================

    Any

def get_client(
    rank: str,
    security_level: Optional[str] = None,
    retry_config: Optional[RetryConfig] = None,
) -> BaseAPIClient:
    """階級に応じたAPIクライアントを取得"""
    from gozen.config import SecurityLevel
    
    sl_enum = None
    if security_level:
        try:
            if isinstance(security_level, SecurityLevel):
                sl_enum = security_level
            else:
                sl_enum = SecurityLevel(security_level)
        except ValueError:
            pass

    config = get_rank_config(rank, sl_enum)

    client_map: dict[InvocationMethod, type[BaseAPIClient]] = {
        InvocationMethod.CLAUDE_CODE_CLI: ClaudeCodeClient,
        InvocationMethod.ANTHROPIC_API: AnthropicClient,
        InvocationMethod.GEMINI_API: GeminiClient,
        InvocationMethod.LOCAL_LLM: OllamaClient,
        InvocationMethod.MOCK: MockClient,
    }

    client_cls = client_map.get(config.method)
    if client_cls is None:
        raise ValueError(f"Unknown method: {config.method}")

    print(f"  [{rank}] {client_cls.__name__} (model={config.model}, method={config.method.value})")
    return client_cls(rank, sl_enum, retry_config)


# ============================================================
# 並列実行ヘルパー
# ============================================================

async def execute_parallel(
    rank: str,
    prompts: list[str],
    max_concurrency: Optional[int] = None,
    **kwargs: Any
) -> list[dict[str, Any]]:
    """並列でAPI呼び出しを実行"""
    config = get_rank_config(rank)
    concurrency = max_concurrency or config.parallel

    semaphore = asyncio.Semaphore(concurrency)
    client = get_client(rank)

    async def call_with_semaphore(prompt: str, index: int) -> dict[str, Any]:
        async with semaphore:
            print(f"  [{rank}#{index + 1}] 実行中...")
            result = await client.call(prompt, **kwargs)
            result["index"] = index
            return result

    print(f"🚀 {rank} ×{len(prompts)} 並列実行（最大同時: {concurrency}）")

    try:
        tasks = [call_with_semaphore(prompt, i) for i, prompt in enumerate(prompts)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        final_results: list[dict[str, Any]] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"  ❌ [{rank}#{i + 1}] エラー: {result}")
                final_results.append({"index": i, "error": str(result)})
            else:
                final_results.append(result)

        return final_results
    finally:
        if hasattr(client, "close"):
            await client.close()


# ============================================================
# デモ
# ============================================================

async def demo() -> None:
    """デモ実行"""
    print("\n" + "=" * 60)
    print("🔧 API クライアント デモ")
    print("=" * 60)

    from gozen.config import print_rank_table
    print_rank_table()

    tracker = get_cost_tracker()
    tracker.print_summary()


if __name__ == "__main__":
    asyncio.run(demo())
