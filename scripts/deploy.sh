#!/bin/bash
set -e

PROJECT_ROOT="/home/shinari/project-gozen"
cd "$PROJECT_ROOT"

echo "=== Deployment Started ==="

# 1. Update Python dependencies
echo "Updating Python dependencies..."
# 仮想環境が確実にある前提で進めるばい
source .venv/bin/activate
pip install -e .

# 2. Build Frontend
echo "Building Frontend..."

# WSLにインストール済みの nvm/Node v20 を有効化する
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
nvm use 20 > /dev/null

echo "Using Node $(node -v)"

cd frontend
# OS側のnpmとNodeをセットで使うことで 'semver' エラーを防ぐばい
npm install
npm run build

# 3. Copy Frontend Assets to Backend Static Dir
echo "Syncing frontend assets..."
mkdir -p ../gozen/web/static/
# Viteの出力先(dist)をバックエンドの静的ディレクトリに同期
cp -r dist/* ../gozen/web/static/

# 4. Restart Background Service
echo "Restarting gozen service..."
# sudoのパスワード入力を求められないよう、visudo等の設定が必要な場合もあるけ注意してね
sudo systemctl restart gozen

echo "=== Deployment Completed Successfully ==="