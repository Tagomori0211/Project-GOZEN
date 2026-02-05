#!/bin/bash
# Project GOZEN - フロントエンドビルドスクリプト

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
FRONTEND_DIR="$PROJECT_ROOT/frontend"
STATIC_DIR="$PROJECT_ROOT/gozen/web/static"

echo "🏗️  Project GOZEN フロントエンドビルド"
echo "========================================"

# frontendディレクトリへ移動
cd "$FRONTEND_DIR"

# node_modulesが存在しない場合はインストール
if [ ! -d "node_modules" ]; then
    echo "📦 依存関係をインストール中..."
    npm install
fi

# ビルド実行
echo "🔨 ビルド中..."
npm run build

echo ""
echo "✅ ビルド完了"
echo "   出力先: $STATIC_DIR"
echo ""
echo "🚀 起動方法:"
echo "   gozen"
echo "   または"
echo "   python -m gozen.web.server"
