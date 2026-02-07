#!/usr/bin/env python3
"""
Qwenモデルの動作確認スクリプト
各モデルに簡単なプロンプトを投げて応答を確認する
"""

import subprocess
import sys
import time

MODELS = [
    ("qwen2.5:32b-instruct-q4_K_M", "参謀用"),
    ("qwen2.5:14b-instruct-q4_K_M", "提督/士官用"),
    ("qwen2.5:7b-instruct-q8_0", "書記用"),
    ("qwen2.5:7b-instruct-q4_K_M", "海兵/歩兵用"),
]

TEST_PROMPT = "1+1は？簡潔に答えよ。"


def test_model(model: str, description: str) -> bool:
    """モデルの動作テスト"""
    print(f"\n{'='*50}")
    print(f"テスト: {model} ({description})")
    print("=" * 50)

    try:
        start = time.time()
        result = subprocess.run(
            ["ollama", "run", model, TEST_PROMPT],
            capture_output=True,
            text=True,
            timeout=120,  # 2分タイムアウト
        )
        elapsed = time.time() - start

        if result.returncode == 0:
            print(f"  成功 ({elapsed:.1f}秒)")
            print(f"  応答: {result.stdout.strip()[:100]}")
            return True
        else:
            print(f"  失敗")
            print(f"  エラー: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        print(f"  タイムアウト (120秒)")
        return False
    except FileNotFoundError:
        print("  エラー: ollama コマンドが見つかりません")
        return False
    except Exception as e:
        print(f"  例外: {e}")
        return False


def main() -> None:
    print("=" * 50)
    print("  Project GOZEN - Qwenモデル動作確認")
    print("=" * 50)

    results = []
    for model, desc in MODELS:
        ok = test_model(model, desc)
        results.append((model, desc, ok))

    print("\n" + "=" * 50)
    print("  結果サマリ")
    print("=" * 50)

    all_ok = True
    for model, desc, ok in results:
        status = "[OK]" if ok else "[NG]"
        print(f"  {status} {model} ({desc})")
        if not ok:
            all_ok = False

    if all_ok:
        print("\n全モデル正常動作")
        sys.exit(0)
    else:
        print("\n一部モデルに問題あり")
        sys.exit(1)


if __name__ == "__main__":
    main()
