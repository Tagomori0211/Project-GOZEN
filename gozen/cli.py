"""
Project GOZEN CLI

御前会議をコマンドラインから実行する。
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from gozen.gozen_orchestrator import GozenOrchestrator


def main() -> None:
    parser = argparse.ArgumentParser(
        description="🏯 Project GOZEN - 御前会議CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
例:
  # 順次実行（Pro推奨）
  python -m gozen.cli --mode sequential task.yaml

  # 並列実行（Max 5x推奨）
  python -m gozen.cli --mode parallel --plan max5x task.yaml

  # インタラクティブモード
  python -m gozen.cli --interactive
""",
    )

    parser.add_argument(
        "task_file",
        nargs="?",
        help="タスク定義YAMLファイル",
    )

    parser.add_argument(
        "--mode",
        type=str,
        choices=["sequential", "parallel"],
        default="sequential",
        help="実行モード（デフォルト: sequential）",
    )

    parser.add_argument(
        "--plan",
        type=str,
        choices=["pro", "max5x", "max20x"],
        default="pro",
        help="Claudeプラン（デフォルト: pro）",
    )

    parser.add_argument(
        "--interactive",
        action="store_true",
        help="インタラクティブモードで起動",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="実行せずに計画のみ表示",
    )

    args = parser.parse_args()

    print_banner()

    if args.interactive:
        run_interactive(args)
    elif args.task_file:
        run_task(args)
    else:
        parser.print_help()


def print_banner() -> None:
    """御前会議バナー"""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║          🏯 PROJECT GOZEN 御前会議                          ║
║         ~ 海軍参謀 vs 陸軍参謀 ~                            ║
║                                                              ║
║    「陸軍として海軍の提案に反対である」                      ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
"""
    print(banner)


def run_task(args: argparse.Namespace) -> None:
    """タスクファイルから実行"""
    task_path = Path(args.task_file)

    if not task_path.exists():
        print(f"❌ エラー: ファイルが見つかりません: {task_path}")
        return

    with open(task_path, "r", encoding="utf-8") as f:
        task: dict[str, Any] = yaml.safe_load(f)

    print(f"📋 タスク読み込み: {task_path}")
    print(f"   モード: {args.mode}")
    print(f"   プラン: {args.plan}")

    if args.dry_run:
        print("\n[DRY-RUN] 実行計画:")
        print(yaml.dump(task, allow_unicode=True, default_flow_style=False))
        return

    orchestrator = GozenOrchestrator(
        default_mode=args.mode,
        plan=args.plan,
    )

    result = asyncio.run(orchestrator.execute_full_cycle(task))

    print("\n" + "=" * 60)
    print(f"✅ 完了: {result['status']}")
    print(f"   タスクID: {result['task_id']}")


def run_interactive(args: argparse.Namespace) -> None:
    """インタラクティブモード"""
    orchestrator = GozenOrchestrator(
        default_mode=args.mode,
        plan=args.plan,
    )

    print("インタラクティブモード開始")
    print("'exit' で終了\n")

    while True:
        try:
            mission = input("👑 [国家元首] 任務を入力: ").strip()

            if mission.lower() == "exit":
                print("\n御前会議を終了します。")
                break

            if not mission:
                continue

            task: dict[str, Any] = {
                "task_id": f"INTERACTIVE-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "mission": mission,
                "requirements": [],
            }

            result = asyncio.run(orchestrator.execute_full_cycle(task))
            print(f"\n結果: {result['status']}\n")

        except KeyboardInterrupt:
            print("\n\n御前会議を終了します。")
            break
        except Exception as e:
            print(f"❌ エラー: {e}")


if __name__ == "__main__":
    main()
