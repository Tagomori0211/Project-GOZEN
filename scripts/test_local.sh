#!/bin/bash
# Project GOZEN - Local Headless Verification Script

set -e

# Navigate to project root
cd "$(dirname "$0")/.."

echo "🚀 Starting Headless Verification Layer..."

# Ensure we have a clean environment
pkill -f "gozen.server" || true

# Start the server in the background
echo "🏯 Starting Server (127.0.0.1:9000)..."
source .venv/bin/activate
export PYTHONUNBUFFERED=1
python3 -m gozen.server &
SERVER_PID=$!

# Wait for startup
echo "⏳ Waiting 5s for server initialization..."
sleep 5

# Run verification
echo "🧪 Running verify_flow.py..."
if python3 verify_flow.py "$@"; then
    echo -e "\n✅ ALL TESTS PASSED."
    RESULT=0
else
    echo -e "\n❌ TESTS FAILED."
    RESULT=1
fi

# Cleanup
echo "🧹 Cleaning up..."
kill $SERVER_PID || true
wait $SERVER_PID 2>/dev/null || true

exit $RESULT
