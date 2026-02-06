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
