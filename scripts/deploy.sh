#!/bin/bash
set -e

PROJECT_ROOT="/home/shinari/project-gozen"
cd "$PROJECT_ROOT"

echo "=== Deployment Started ==="

# 1. Update Python dependencies
echo "Updating Python dependencies..."
source .venv/bin/activate
pip install -e .

# 2. Build Frontend
echo "Building Frontend..."

# Ensure Node.js v20 is available
NODE_VERSION="v20.11.0"
NODE_DIR="$PROJECT_ROOT/node-$NODE_VERSION-linux-x64"

if ! command -v node >/dev/null 2>&1 || [[ "$(node -v)" != v20* ]]; then
    if [ ! -d "$NODE_DIR" ]; then
        echo "Node.js v20 not found. Downloading..."
        wget -q https://nodejs.org/dist/$NODE_VERSION/node-$NODE_VERSION-linux-x64.tar.xz
        tar -xf node-$NODE_VERSION-linux-x64.tar.xz
        rm node-$NODE_VERSION-linux-x64.tar.xz
    fi
    export PATH="$NODE_DIR/bin:$PATH"
fi

echo "Using Node $(node -v)"
cd frontend
npm install
npm run build

# 3. Copy Frontend Assets to Backend Static Dir
echo "Syncing frontend assets..."
# package.json defines build as 'vite build', which usually outputs to 'dist'
# but we need to check gozen/web/static location
mkdir -p ../gozen/web/static/
cp -r dist/* ../gozen/web/static/

# 4. Restart Background Service
echo "Restarting gozen service..."
sudo systemctl restart gozen

echo "=== Deployment Completed Successfully ==="
