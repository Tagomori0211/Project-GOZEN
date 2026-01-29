"""
Project GOZEN - API クライアントモジュール

Anthropic API と Gemini API のラッパー。
指数バックオフ、リトライ、コスト追跡を実装。
"""

import asyncio
import time
import os
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, AsyncGenerator, Any
from enum import Enum

from gozen.config import (
    get_rank_config,
    estimate_cost,
    RankConfig,
    BillingType,
)


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
    
    def __init__(self):
        self.records: list[APICallRecord] = []
        self._session_start = datetime.now()
    
    def record(self, record: APICallRecord):
        """記録を追加"""
        self.records.append(record)
    
    @property
    def total_cost(self) -> float:
        """累計コスト"""
        return sum(r.cost_usd for r in self.records if r.success)
    
    @property
    def total_input_tokens(self) -> int:
        """累計入力トークン"""
        return sum(r.input_tokens for r in self.records if r.success)
    
    @property
    def total_output_tokens(self) -> int:
        """累計出力トークン"""
        return sum(r.output_tokens for r in self.records if r.success)
    
    @property
    def call_count(self) -> int:
        """呼び出し回数"""
        return len(self.records)
    
    @property
    def error_count(self) -> int:
        """エラー回数"""
        return sum(1 for r in self.records if not r.success)
    
    def get_summary(self) -> dict:
        """サマリーを取得"""
        return {
            "session_start": self._session_start.isoformat(),
            "total_calls": self.call_count,
            "errors": self.error_count,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_cost_usd": round(self.total_cost, 4),
            "total_cost_jpy": round(self.total_cost * 150, 0),  # 1$ = 150円
        }
    
    def print_summary(self):
        """サマリーを表示"""
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


# グローバルコストトラッカー
_cost_tracker: Optional[CostTracker] = None


def get_cost_tracker() -> CostTracker:
    """コストトラッカーを取得"""
    global _cost_tracker
    if _cost_tracker is None:
        _cost_tracker = CostTracker()
    return _cost_tracker


# ============================================================
# リトライ設定
# ============================================================

@dataclass
class RetryConfig:
    """リトライ設定"""
    max_retries: int = 3
    base_delay: float = 1.0  # 秒
    max_delay: float = 60.0  # 秒
    exponential_base: float = 2.0
    jitter: bool = True


def calculate_delay(retry_count: int, config: RetryConfig) -> float:
    """
    指数バックオフでリトライ間隔を計算
    """
    delay = config.base_delay * (config.exponential_base ** retry_count)
    delay = min(delay, config.max_delay)
    
    if config.jitter:
        import random
        delay *= (0.5 + random.random())
    
    return delay


# ============================================================
# 抽象基底クラス
# ============================================================

class BaseAPIClient(ABC):
    """API クライアント基底クラス"""
    
    def __init__(self, rank: str, retry_config: Optional[RetryConfig] = None):
        self.rank = rank
        self.config = get_rank_config(rank)
        self.retry_config = retry_config or RetryConfig()
        self.tracker = get_cost_tracker()
    
    @abstractmethod
    async def _call_api(self, prompt: str, **kwargs) -> dict:
        """実際のAPI呼び出し（サブクラスで実装）"""
        pass
    
    async def call(self, prompt: str, **kwargs) -> dict:
        """
        リトライ付きAPI呼び出し
        """
        last_error = None
        start_time = time.time()
        
        for retry in range(self.retry_config.max_retries + 1):
            try:
                result = await self._call_api(prompt, **kwargs)
                
                # コスト記録
                latency = int((time.time() - start_time) * 1000)
                self._record_success(result, latency)
                
                return result
                
            except RateLimitError as e:
                last_error = e
                if retry < self.retry_config.max_retries:
                    delay = calculate_delay(retry, self.retry_config)
                    print(f"⚠️ レート制限。{delay:.1f}秒後にリトライ... ({retry+1}/{self.retry_config.max_retries})")
                    await asyncio.sleep(delay)
                    
            except APIError as e:
                last_error = e
                self._record_error(str(e))
                if retry < self.retry_config.max_retries:
                    delay = calculate_delay(retry, self.retry_config)
                    print(f"⚠️ APIエラー: {e}。{delay:.1f}秒後にリトライ...")
                    await asyncio.sleep(delay)
        
        # 全リトライ失敗
        raise last_error or APIError("Unknown error after retries")
    
    def _record_success(self, result: dict, latency_ms: int):
        """成功記録"""
        record = APICallRecord(
            rank=self.rank,
            model=self.config.model,
            input_tokens=result.get("usage", {}).get("input_tokens", 0),
            output_tokens=result.get("usage", {}).get("output_tokens", 0),
            cost_usd=estimate_cost(
                result.get("usage", {}).get("input_tokens", 0),
                result.get("usage", {}).get("output_tokens", 0),
                self.rank,
            ),
            latency_ms=latency_ms,
            success=True,
        )
        self.tracker.record(record)
    
    def _record_error(self, error: str):
        """エラー記録"""
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
# Anthropic API クライアント
# ============================================================

class AnthropicClient(BaseAPIClient):
    """
    Anthropic API クライアント
    
    水兵（Haiku）、提督・艦長（Sonnet）用
    """
    
    def __init__(self, rank: str, retry_config: Optional[RetryConfig] = None):
        super().__init__(rank, retry_config)
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        self._client = None
    
    def _get_client(self):
        """クライアント取得（遅延初期化）"""
        if self._client is None:
            try:
                from anthropic import AsyncAnthropic
                self._client = AsyncAnthropic(api_key=self.api_key)
            except ImportError:
                raise APIError("anthropic パッケージがインストールされていません")
        return self._client
    
    async def _call_api(self, prompt: str, **kwargs) -> dict:
        """Anthropic API 呼び出し"""
        if not self.api_key:
            raise AuthenticationError("ANTHROPIC_API_KEY が設定されていません")
        
        client = self._get_client()
        
        try:
            response = await client.messages.create(
                model=self.config.model,
                max_tokens=kwargs.get("max_tokens", 4096),
                messages=[
                    {"role": "user", "content": prompt}
                ],
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
            else:
                raise APIError(str(e))


# ============================================================
# Gemini API クライアント
# ============================================================

class GeminiClient(BaseAPIClient):
    """
    Gemini API クライアント
    
    士官・歩兵（Flash）、陸軍参謀（Pro）用
    """
    
    def __init__(self, rank: str, retry_config: Optional[RetryConfig] = None):
        super().__init__(rank, retry_config)
        self.api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        self._client = None
    
    def _get_client(self):
        """クライアント取得（遅延初期化）"""
        if self._client is None:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self._client = genai.GenerativeModel(self.config.model)
            except ImportError:
                raise APIError("google-generativeai パッケージがインストールされていません")
        return self._client
    
    async def _call_api(self, prompt: str, **kwargs) -> dict:
        """Gemini API 呼び出し"""
        if not self.api_key:
            raise AuthenticationError("GOOGLE_API_KEY が設定されていません")
        
        client = self._get_client()
        
        try:
            # Geminiは同期APIなのでrun_in_executorで非同期化
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: client.generate_content(prompt)
            )
            
            # トークン数の取得（Geminiの仕様に依存）
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
            
        except Exception as e:
            error_str = str(e).lower()
            if "rate" in error_str or "429" in error_str or "quota" in error_str:
                raise RateLimitError(str(e))
            elif "auth" in error_str or "api key" in error_str:
                raise AuthenticationError(str(e))
            else:
                raise APIError(str(e))


# ============================================================
# クライアントファクトリ
# ============================================================

def get_client(rank: str, retry_config: Optional[RetryConfig] = None) -> BaseAPIClient:
    """
    階級に応じたAPIクライアントを取得
    
    Args:
        rank: 階級名
        retry_config: リトライ設定
        
    Returns:
        適切なAPIクライアント
    """
    config = get_rank_config(rank)
    
    if config.method == "anthropic_api":
        return AnthropicClient(rank, retry_config)
    elif config.method == "gemini_api":
        return GeminiClient(rank, retry_config)
    elif config.method == "claude_code_cli":
        # サブスク経由の場合はダミーまたは別実装
        raise NotImplementedError("Claude Code CLI はこのモジュールではサポートされていません")
    else:
        raise ValueError(f"Unknown method: {config.method}")


# ============================================================
# 並列実行ヘルパー
# ============================================================

async def execute_parallel(
    rank: str,
    prompts: list[str],
    max_concurrency: Optional[int] = None,
    **kwargs
) -> list[dict]:
    """
    並列でAPI呼び出しを実行
    
    Args:
        rank: 階級名
        prompts: プロンプトリスト
        max_concurrency: 最大同時実行数（None=階級のparallel値）
        
    Returns:
        結果リスト
    """
    config = get_rank_config(rank)
    concurrency = max_concurrency or config.parallel
    
    semaphore = asyncio.Semaphore(concurrency)
    client = get_client(rank)
    
    async def call_with_semaphore(prompt: str, index: int) -> dict:
        async with semaphore:
            print(f"  [{rank}#{index+1}] 実行中...")
            result = await client.call(prompt, **kwargs)
            result["index"] = index
            return result
    
    print(f"🚀 {rank} ×{len(prompts)} 並列実行（最大同時: {concurrency}）")
    
    tasks = [
        call_with_semaphore(prompt, i)
        for i, prompt in enumerate(prompts)
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # エラーハンドリング
    final_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            print(f"  ❌ [{rank}#{i+1}] エラー: {result}")
            final_results.append({"index": i, "error": str(result)})
        else:
            final_results.append(result)
    
    return final_results


# ============================================================
# デモ・テスト
# ============================================================

async def demo():
    """デモ実行"""
    print("\n" + "=" * 60)
    print("🔧 API クライアント デモ")
    print("=" * 60)
    
    # 設定表示
    from gozen.config import print_rank_table
    print_rank_table()
    
    # コスト追跡サマリー
    tracker = get_cost_tracker()
    tracker.print_summary()


if __name__ == "__main__":
    asyncio.run(demo())
