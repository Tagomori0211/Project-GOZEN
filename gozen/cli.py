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
  gozen --mode sequential task.yaml

  # 並列実行（Max 5x推奨）
  gozen --mode parallel --plan max5x task.yaml

  # インタラクティブモード
  gozen --interactive

  # python -m でも起動可能
  python -m gozen --interactive
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

    parser.add_argument(
        "--council-mode",
        type=str,
        choices=["council", "execute"],
        default=None,
        help="作戦形式（council: 会議のみ, execute: 全軍展開）省略時は対話選択",
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
    banner = r"""
 ██████╗  ██████╗ ███████╗███████╗███╗   ██╗
██╔════╝ ██╔═══██╗╚══███╔╝██╔════╝████╗  ██║
██║  ███╗██║   ██║  ███╔╝ █████╗  ██╔██╗ ██║
██║   ██║██║   ██║ ███╔╝  ██╔══╝  ██║╚██╗██║
╚██████╔╝╚██████╔╝███████╗███████╗██║ ╚████║
 ╚═════╝  ╚═════╝ ╚══════╝╚══════╝╚═╝  ╚═══╝
       ██╗  ██╗ █████╗ ██╗ ██████╗ ██╗
       ██║ ██╔╝██╔══██╗██║██╔════╝ ██║
       █████╔╝ ███████║██║██║  ███╗██║
       ██╔═██╗ ██╔══██║██║██║   ██║██║
       ██║  ██╗██║  ██║██║╚██████╔╝██║
       ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝ ╚═════╝ ╚═╝

        ~ 御前会議 / 海軍参謀 vs 陸軍参謀 ~
     「陸軍として海軍の提案に反対である」
"""
    print(banner)


def select_mode() -> str:
    """作戦形式の選択画面を表示し、モードを返す"""
    mode_ui = """
╔══════════════════════════════════════════════════════════════╗
║                  ⚔️  作戦形式を選択せよ                      ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  [1] 🏯 会議モード（御前会議）                               ║
║      海軍参謀 vs 陸軍参謀 の討議                             ║
║      国家元首が裁定を下す                                    ║
║      ※ 実行部隊は展開しない                                 ║
║                                                              ║
║  [2] ⚔️  作戦実行モード（全軍展開）                          ║
║      海軍参謀 vs 陸軍参謀 の討議 → 裁定                     ║
║      → 実行部隊を展開                                       ║
║      提督→艦長→海兵×8  /  士官→歩兵×4                       ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
"""
    print(mode_ui)

    try:
        choice = input("👑 [国家元首] 作戦形式を選択 (1-2): ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n会議モードをデフォルト選択します。")
        return "council"

    if choice == "2":
        print("\n⚔️  作戦実行モード（全軍展開）を選択しました。\n")
        return "execute"

    print("\n🏯 会議モード（御前会議）を選択しました。\n")
    return "council"


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

    council_mode = args.council_mode or select_mode()

    orchestrator = GozenOrchestrator(
        default_mode=args.mode,
        plan=args.plan,
        council_mode=council_mode,
    )

    result = asyncio.run(orchestrator.execute_full_cycle(task))

    print("\n" + "=" * 60)
    if result["mode"] == "council":
        print(f"📜 裁定結果: {result['status']}")
    else:
        print(f"✅ 完了: {result['status']}")
    print(f"   タスクID: {result['task_id']}")


def run_interactive(args: argparse.Namespace) -> None:
    """インタラクティブモード"""
    council_mode = args.council_mode or select_mode()

    orchestrator = GozenOrchestrator(
        default_mode=args.mode,
        plan=args.plan,
        council_mode=council_mode,
    )

    mode_label = "🏯 会議モード" if council_mode == "council" else "⚔️  作戦実行モード"
    print(f"インタラクティブモード開始（{mode_label}）")
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

            if result["mode"] == "council":
                print(f"\n📜 裁定結果: {result['status']}\n")
            else:
                print(f"\n✅ 結果: {result['status']}\n")

        except KeyboardInterrupt:
            print("\n\n御前会議を終了します。")
            break
        except Exception as e:
            print(f"❌ エラー: {e}")


if __name__ == "__main__":
    main()
