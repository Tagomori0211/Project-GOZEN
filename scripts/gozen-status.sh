#!/usr/bin/env bash
# ============================================================
# Project GOZEN - Status Dashboard Helper
# ============================================================
# Called by `watch` in the status pane of gozen-tmux.sh.
# Displays queue counts, latest files, audit summary, and
# API key validation status.
# ============================================================

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Source .env if available (for API key checks)
if [[ -f "$PROJECT_DIR/.env" ]]; then
    set -a
    source "$PROJECT_DIR/.env" 2>/dev/null
    set +a
fi

# --- Helpers ---

count_files() {
    local dir="$1"
    if [[ -d "$dir" ]]; then
        find "$dir" -type f 2>/dev/null | wc -l
    else
        echo 0
    fi
}

latest_file() {
    local dir="$1"
    if [[ -d "$dir" ]]; then
        ls -t "$dir" 2>/dev/null | head -1
    fi
}

check_api_key() {
    local name="$1"
    local value="$2"
    if [[ -n "$value" && "$value" != "your_"* ]]; then
        echo "OK (${value:0:8}...)"
    else
        echo "NOT SET"
    fi
}

# --- Display ---

QUEUE_DIR="$PROJECT_DIR/queue"
AUDIT_DIR="$PROJECT_DIR/audit"

echo "========================================"
echo "  PROJECT GOZEN - Status Dashboard"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo "========================================"

echo ""
echo "--- Queue Status ---"
printf "  Proposals:  %3d files" "$(count_files "$QUEUE_DIR/proposal")"
latest="$(latest_file "$QUEUE_DIR/proposal")"
[[ -n "$latest" ]] && printf "  (latest: %s)" "$latest"
echo ""

printf "  Objections: %3d files" "$(count_files "$QUEUE_DIR/objection")"
latest="$(latest_file "$QUEUE_DIR/objection")"
[[ -n "$latest" ]] && printf "  (latest: %s)" "$latest"
echo ""

printf "  Decisions:  %3d files" "$(count_files "$QUEUE_DIR/decision")"
latest="$(latest_file "$QUEUE_DIR/decision")"
[[ -n "$latest" ]] && printf "  (latest: %s)" "$latest"
echo ""

printf "  Executions: %3d files" "$(count_files "$QUEUE_DIR/execution")"
latest="$(latest_file "$QUEUE_DIR/execution")"
[[ -n "$latest" ]] && printf "  (latest: %s)" "$latest"
echo ""

echo ""
echo "--- Audit Summary ---"
audit_count="$(count_files "$AUDIT_DIR")"
printf "  Reports: %d" "$audit_count"
echo ""

if [[ "$audit_count" -gt 0 ]]; then
    latest_audit="$(latest_file "$AUDIT_DIR")"
    if [[ -n "$latest_audit" ]]; then
        echo "  Latest: $latest_audit"
        # Extract result from YAML if possible
        if command -v grep &>/dev/null; then
            result="$(grep -m1 'result:' "$AUDIT_DIR/$latest_audit" 2>/dev/null | awk '{print $2}')"
            if [[ -n "$result" ]]; then
                case "$result" in
                    pass)        echo "  Result: PASS" ;;
                    fail)        echo "  Result: FAIL" ;;
                    conditional) echo "  Result: CONDITIONAL" ;;
                    *)           echo "  Result: $result" ;;
                esac
            fi
        fi
    fi
fi

echo ""
echo "--- API Keys ---"
echo "  ANTHROPIC_API_KEY:  $(check_api_key 'ANTHROPIC' "${ANTHROPIC_API_KEY:-}")"
echo "  GOOGLE_API_KEY:     $(check_api_key 'GOOGLE' "${GOOGLE_API_KEY:-}")"
echo "  GEMINI_API_KEY:     $(check_api_key 'GEMINI' "${GEMINI_API_KEY:-}")"

echo ""
echo "--- Environment ---"
if [[ -n "${VIRTUAL_ENV:-}" ]]; then
    echo "  venv: active ($(basename "$VIRTUAL_ENV"))"
else
    echo "  venv: inactive"
fi
echo "  Python: $(python3 --version 2>/dev/null || echo 'not found')"
echo "  tmux:   $(tmux -V 2>/dev/null || echo 'not found')"
