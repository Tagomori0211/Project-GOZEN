"""
Project GOZEN CLI

御前会議をコマンドラインから実行する。

コマンド:
  gozen <task_file>          タスク実行
  gozen --interactive        インタラクティブモード
  gozen decide               エスカレーション時の元首裁定
  gozen setup                Qwen環境セットアップ
"""

from __future__ import annotations

import argparse
import asyncio
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from gozen.gozen_orchestrator import GozenOrchestrator


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Project GOZEN - 御前会議CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
例:
  # タスク実行
  gozen task.yaml

  # セキュリティレベル指定
  gozen --security confidential task.yaml

  # インタラクティブモード
  gozen --interactive

  # エスカレーション裁定
  gozen decide --task TASK-001 --action force-kaigun

  # Qwen環境セットアップ
  gozen setup
  gozen setup --check-only

  # python -m でも起動可能
  python -m gozen --interactive
""",
    )

    subparsers = parser.add_subparsers(dest="command")

    # --- decide コマンド ---
    decide_parser = subparsers.add_parser(
        "decide",
        help="エスカレーション時の元首裁定",
    )
    decide_parser.add_argument(
        "--task",
        required=True,
        help="タスクID",
    )
    decide_parser.add_argument(
        "--action",
        required=True,
        choices=["force-kaigun", "force-rikugun", "manual-merge", "split", "abort"],
        help="裁定アクション",
    )

    # --- setup コマンド ---
    setup_parser = subparsers.add_parser(
        "setup",
        help="Qwen環境のセットアップ",
    )
    setup_parser.add_argument(
        "--check-only",
        action="store_true",
        help="確認のみ（ダウンロードしない）",
    )

    # --- メインコマンド引数（サブコマンドなし時） ---
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

    parser.add_argument(
        "--security",
        type=str,
        choices=["public", "confidential"],
        default=None,
        help="セキュリティレベル（省略時: public）",
    )

    args = parser.parse_args()

    # サブコマンド分岐
    if args.command == "decide":
        run_decide(args)
        return
    elif args.command == "setup":
        run_setup(args)
        return

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
║                  作戦形式を選択せよ                          ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  [1] 会議モード（御前会議）                                  ║
║      海軍参謀 vs 陸軍参謀 の討議                             ║
║      国家元首が裁定を下す                                    ║
║                                                              ║
║  [2] 作戦実行モード（全軍展開）                              ║
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
        print("\n作戦実行モード（全軍展開）を選択しました。\n")
        return "execute"

    print("\n会議モード（御前会議）を選択しました。\n")
    return "council"


def _apply_security_level(security: str | None) -> None:
    """セキュリティレベルをグローバルに適用"""
    if security is not None:
        from gozen.config import SecurityLevel
        import gozen.config as config_module
        config_module.DEFAULT_SECURITY_LEVEL = SecurityLevel(security)


def run_task(args: argparse.Namespace) -> None:
    """タスクファイルから実行"""
    task_path = Path(args.task_file)

    if not task_path.exists():
        print(f"エラー: ファイルが見つかりません: {task_path}")
        return

    with open(task_path, "r", encoding="utf-8") as f:
        task: dict[str, Any] = yaml.safe_load(f)

    # セキュリティレベル: CLI引数 > YAMLファイル > デフォルト
    security = args.security or task.get("security_level")
    _apply_security_level(security)

    print(f"タスク読み込み: {task_path}")
    print(f"  モード: {args.mode}")
    print(f"  プラン: {args.plan}")
    if security:
        print(f"  セキュリティ: {security}")

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
        print(f"裁定結果: {result['status']}")
    else:
        print(f"完了: {result['status']}")
    print(f"  タスクID: {result['task_id']}")


def run_interactive(args: argparse.Namespace) -> None:
    """インタラクティブモード"""
    _apply_security_level(args.security)

    council_mode = args.council_mode or select_mode()

    orchestrator = GozenOrchestrator(
        default_mode=args.mode,
        plan=args.plan,
        council_mode=council_mode,
    )

    mode_label = "会議モード" if council_mode == "council" else "作戦実行モード"
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
                print(f"\n裁定結果: {result['status']}\n")
            else:
                print(f"\n結果: {result['status']}\n")

        except KeyboardInterrupt:
            print("\n\n御前会議を終了します。")
            break
        except Exception as e:
            print(f"エラー: {e}")


def run_decide(args: argparse.Namespace) -> None:
    """エスカレーション時の元首裁定を処理"""
    from gozen.council_mode import resolve_deadlock

    task_id = args.task
    action = args.action

    match action:
        case "force-kaigun":
            resolve_deadlock(task_id, adopted="kaigun")
            print(f"海軍案を強制採択しました: {task_id}")

        case "force-rikugun":
            resolve_deadlock(task_id, adopted="rikugun")
            print(f"陸軍案を強制採択しました: {task_id}")

        case "manual-merge":
            merge_dir = Path(__file__).parent.parent / "queue" / "synthesis"
            merge_dir.mkdir(parents=True, exist_ok=True)
            merge_file = merge_dir / f"{task_id}_manual_merge.yaml"

            if not merge_file.exists():
                # テンプレート作成
                template = {
                    "title": "手動統合案",
                    "summary": "",
                    "key_points": [],
                    "description": "ここに統合案を記述してください",
                }
                with open(merge_file, "w", encoding="utf-8") as f:
                    yaml.dump(template, f, allow_unicode=True, default_flow_style=False)

            print(f"マージファイルを編集してください: {merge_file}")

            try:
                confirm = input("マージ案を保存しましたか？ (y/n): ")
            except EOFError:
                confirm = "n"

            if confirm.lower() == "y":
                resolve_deadlock(task_id, adopted="manual", merge_file=str(merge_file))
                print(f"手動マージ案を採択しました: {task_id}")
            else:
                print("キャンセルしました")

        case "split":
            print("タスク分割ウィザードを起動...")
            _launch_split_wizard(task_id)

        case "abort":
            try:
                confirm = input("本当に中止しますか？ (y/n): ")
            except EOFError:
                confirm = "n"

            if confirm.lower() == "y":
                _abort_task(task_id)
                print(f"タスクを中止しました: {task_id}")
            else:
                print("キャンセルしました")


def run_setup(args: argparse.Namespace) -> None:
    """Qwen環境セットアップ"""
    script_path = Path(__file__).parent.parent / "scripts" / "setup_qwen.sh"

    if not script_path.exists():
        print(f"エラー: セットアップスクリプトが見つかりません: {script_path}")
        return

    cmd = ["bash", str(script_path)]
    if args.check_only:
        cmd.append("--check-only")

    subprocess.run(cmd)


def _launch_split_wizard(task_id: str) -> None:
    """タスク分割ウィザード"""
    print(f"\nタスク分割: {task_id}")
    print("-" * 40)

    subtasks = []
    print("サブタスクを入力してください（空行で終了）:")

    i = 1
    while True:
        try:
            name = input(f"  サブタスク{i}: ").strip()
        except EOFError:
            break

        if not name:
            break

        subtasks.append({
            "id": f"{task_id}-SUB{i:03d}",
            "name": name,
        })
        i += 1

    if subtasks:
        queue_dir = Path(__file__).parent.parent / "queue" / "split"
        queue_dir.mkdir(parents=True, exist_ok=True)

        split_file = queue_dir / f"{task_id}_split.yaml"
        with open(split_file, "w", encoding="utf-8") as f:
            yaml.dump({"parent_task": task_id, "subtasks": subtasks}, f,
                       allow_unicode=True, default_flow_style=False)
        print(f"\nサブタスク {len(subtasks)} 件を登録しました: {split_file}")
    else:
        print("サブタスクが入力されませんでした。")


def _abort_task(task_id: str) -> None:
    """タスク中止処理"""
    from gozen.council_mode import resolve_deadlock
    resolve_deadlock(task_id, adopted="abort")


if __name__ == "__main__":
    main()
