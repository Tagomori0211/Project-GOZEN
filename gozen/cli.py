"""
Project GOZEN CLI

御前会議サーバーを起動する。

コマンド:
  gozen                      サーバー起動 (Port 9000)
  gozen setup                Qwen環境セットアップ
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from gozen.config import SERVER_HOST, SERVER_PORT

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Project GOZEN - 御前会議サーバー",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command")

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

    # --- サーバー起動オプション ---
    parser.add_argument(
        "--host",
        type=str,
        default=SERVER_HOST,
        help=f"ホスト (デフォルト: {SERVER_HOST})",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=SERVER_PORT,
        help=f"ポート (デフォルト: {SERVER_PORT})",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="ホットリロード有効化 (開発用)",
    )

    args = parser.parse_args()

    if args.command == "setup":
        run_setup(args)
        return

    # サーバー起動
    run_server(args)


def run_server(args: argparse.Namespace) -> None:
    """Uvicornサーバーを起動"""
    print_banner()
    
    print(f"🚀 御前会議サーバーを起動します...")
    print(f"   Listening on http://{args.host}:{args.port}")
    print(f"   API Docs:    http://{args.host}:{args.port}/docs")
    print()

    try:
        import uvicorn
        uvicorn.run(
            "gozen.server:app",
            host=args.host,
            port=args.port,
            reload=args.reload,
        )
    except ImportError:
        print("エラー: uvicorn がインストールされていません。")
        print("pip install uvicorn[standard] fastapi")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nサーバーを停止しました。")


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


def print_banner() -> None:
    """御前会議バナー"""
    banner = r"""
 ██████╗  ██████╗ ███████╗███████╗███╗   ██╗
██╔════╝ ██╔═══██╗╚══███╔╝██╔════╝████╗  ██║
██║  ███╗██║   ██║  ███╔╝ █████╗  ██╔██╗ ██║
██║   ██║██║   ██║ ███╔╝  ██╔══╝  ██║╚██╗██║
╚██████╔╝╚██████╔╝███████╗███████╗██║ ╚████║
 ╚═════╝  ╚═════╝ ╚══════╝╚══════╝╚═╝  ╚═══╝
 
        ~ 御前会議 API Server ~
"""
    print(banner)


if __name__ == "__main__":
    main()
