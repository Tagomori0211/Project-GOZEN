#!/usr/bin/env bash
# ============================================================
# Project GOZEN - tmux Launcher
# ============================================================
# Usage: ./scripts/gozen-tmux.sh [OPTIONS]
#
# Options:
#   --interactive    Start orchestrator in interactive mode (default)
#   --task FILE      Start orchestrator with a task YAML file
#   --kill           Kill existing gozen tmux session
#   --attach         Attach to existing session without recreating
#   --help           Show this help message
# ============================================================

set -euo pipefail

# --- Constants ---
SESSION="gozen"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
STATUS_SCRIPT="$SCRIPT_DIR/gozen-status.sh"

# --- Colors ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# --- Functions ---

usage() {
    cat <<'USAGE'
============================================================
  PROJECT GOZEN - tmux Launcher
============================================================

Usage: ./scripts/gozen-tmux.sh [OPTIONS]

Options:
  --interactive    Start orchestrator in interactive mode (default)
  --task FILE      Start orchestrator with a task YAML file
  --kill           Kill existing gozen tmux session
  --attach         Attach to existing session without recreating
  --help           Show this help message

Windows:
  [0] gensui  - Orchestrator, queue monitors, status dashboard
  [1] sakusen - Naval shell, army shell, audit log, general shell

Examples:
  ./scripts/gozen-tmux.sh                         # Interactive mode
  ./scripts/gozen-tmux.sh --task tasks/sample.yaml # Run a task file
  ./scripts/gozen-tmux.sh --kill                   # Kill session
USAGE
}

log_info()  { echo -e "${CYAN}[GOZEN]${NC} $*"; }
log_ok()    { echo -e "${GREEN}[GOZEN]${NC} $*"; }
log_warn()  { echo -e "${YELLOW}[GOZEN]${NC} $*"; }
log_error() { echo -e "${RED}[GOZEN]${NC} $*"; }

check_deps() {
    if ! command -v tmux &>/dev/null; then
        log_error "tmux is not installed. Please install it first."
        exit 1
    fi
}

kill_session() {
    if tmux has-session -t "$SESSION" 2>/dev/null; then
        tmux kill-session -t "$SESSION"
        log_ok "Session '$SESSION' killed."
    else
        log_warn "No session '$SESSION' found."
    fi
}

# Build the shell init command that sources .env and activates .venv
pane_init() {
    local cmds=""
    cmds+="cd '$PROJECT_DIR'"
    if [[ -f "$PROJECT_DIR/.env" ]]; then
        cmds+=" && set -a && source '$PROJECT_DIR/.env' && set +a"
    fi
    if [[ -f "$PROJECT_DIR/.venv/bin/activate" ]]; then
        cmds+=" && source '$PROJECT_DIR/.venv/bin/activate'"
    fi
    echo "$cmds"
}

create_session() {
    local orchestrator_cmd="$1"

    # Abort if session already exists
    if tmux has-session -t "$SESSION" 2>/dev/null; then
        log_warn "Session '$SESSION' already exists. Use --kill first or --attach."
        tmux attach-session -t "$SESSION"
        return
    fi

    local init
    init="$(pane_init)"

    log_info "Creating tmux session: $SESSION"

    # ========================================================
    # Window 0: gensui (司令部)
    # ========================================================
    # Target layout:
    # +------------------------------------------+------------------------+
    # |                                          | Naval Queue Monitor    |
    # |  ORCHESTRATOR                            +------------------------+
    # |  (65% width)                             | Army Queue Monitor     |
    # |                                          +------------------------+
    # |                                          | Status Dashboard       |
    # +------------------------------------------+------------------------+
    # | Decision & Execution Monitor (20% height)                        |
    # +------------------------------------------------------------------+
    #
    # Build order (tracking pane IDs via unique markers):
    #   1. Create session -> pane %0 (orchestrator)
    #   2. Split %0 horizontally -> %0 left, %1 right
    #   3. Split %1 vertically -> %1 top-right, %2 mid-right
    #   4. Split %2 vertically -> %2 mid-right, %3 bottom-right
    #   5. Split %0 vertically -> %0 top-left, %4 bottom-left (full-width bottom)
    # ========================================================

    tmux new-session -d -s "$SESSION" -n "gensui" -x 200 -y 50

    # Step 1: pane %0 = orchestrator (full window initially)
    tmux send-keys -t "$SESSION:gensui.0" "$init && clear" C-m

    # Step 2: split right 35% -> new pane is right side
    tmux split-window -t "$SESSION:gensui.0" -h -p 35
    # Now: .0 = left (orchestrator), .1 = right
    tmux send-keys -t "$SESSION:gensui.1" "$init && clear" C-m

    # Step 3: split .1 vertically 66% below -> naval queue stays top, new pane below
    tmux split-window -t "$SESSION:gensui.1" -v -p 66
    # Now: .0 = left, .1 = right-top (naval), .2 = right-bottom
    tmux send-keys -t "$SESSION:gensui.2" "$init && clear" C-m

    # Step 4: split .2 vertically 50% -> army queue top, status bottom
    tmux split-window -t "$SESSION:gensui.2" -v -p 50
    # Now: .0 = left, .1 = right-top, .2 = right-mid, .3 = right-bottom
    tmux send-keys -t "$SESSION:gensui.3" "$init && clear" C-m

    # Step 5: split .0 (orchestrator) vertically 20% bottom for decision monitor
    tmux split-window -t "$SESSION:gensui.0" -v -p 20
    # After splitting .0: new pane inserted as .1, old .1->.2, .2->.3, .3->.4
    # Final indices:
    #   .0 = orchestrator (top-left)
    #   .1 = decision monitor (bottom-left)
    #   .2 = naval queue (right-top)
    #   .3 = army queue (right-mid)
    #   .4 = status dashboard (right-bottom)
    tmux send-keys -t "$SESSION:gensui.1" "$init && clear" C-m

    # --- Send commands to each pane ---

    # Naval queue monitor
    tmux send-keys -t "$SESSION:gensui.2" \
        "watch -n 3 'echo \"=== Naval Queue Monitor ===\"; echo \"--- Proposals ---\"; ls -lt \"$PROJECT_DIR/queue/proposal/\" 2>/dev/null | head -10; echo; echo \"Count: \$(find \"$PROJECT_DIR/queue/proposal/\" -type f 2>/dev/null | wc -l) files\"'" C-m

    # Army queue monitor
    tmux send-keys -t "$SESSION:gensui.3" \
        "watch -n 3 'echo \"=== Army Queue Monitor ===\"; echo \"--- Objections ---\"; ls -lt \"$PROJECT_DIR/queue/objection/\" 2>/dev/null | head -10; echo; echo \"Count: \$(find \"$PROJECT_DIR/queue/objection/\" -type f 2>/dev/null | wc -l) files\"'" C-m

    # Status dashboard
    tmux send-keys -t "$SESSION:gensui.4" \
        "watch -n 5 '$STATUS_SCRIPT'" C-m

    # Decision & Execution monitor
    tmux send-keys -t "$SESSION:gensui.1" \
        "watch -n 3 'echo \"=== Decision & Execution Monitor ===\"; echo \"--- Decisions ---\"; ls -lt \"$PROJECT_DIR/queue/decision/\" 2>/dev/null | head -8; echo; echo \"--- Executions ---\"; ls -lt \"$PROJECT_DIR/queue/execution/\" 2>/dev/null | head -8'" C-m

    # Start orchestrator in pane 0
    tmux send-keys -t "$SESSION:gensui.0" "$orchestrator_cmd" C-m

    # ========================================================
    # Window 1: sakusen (作戦室)
    # ========================================================
    # Layout (2x2 grid):
    # +----------------------------------+----------------------------------+
    # | Naval Shell (海軍操作)            | Audit Log (監査記録)              |
    # +----------------------------------+----------------------------------+
    # | Army Shell (陸軍操作)             | General Shell (汎用)              |
    # +----------------------------------+----------------------------------+
    #
    # Build order:
    #   1. New window -> pane .0 (naval shell)
    #   2. Split .0 horizontally 50% -> .0 left, .1 right (audit)
    #   3. Split .1 vertically 50% -> .1 top-right (audit), .2 bottom-right (general)
    #   4. Split .0 vertically 50% -> .0 top-left (naval), new .1 bottom-left (army)
    #      (old .1 -> .2 audit, old .2 -> .3 general)
    # ========================================================

    tmux new-window -t "$SESSION" -n "sakusen"

    # Step 1: .0 = naval shell
    tmux send-keys -t "$SESSION:sakusen.0" "$init && clear" C-m

    # Step 2: split right 50%
    tmux split-window -t "$SESSION:sakusen.0" -h -p 50
    # .0 = left (naval), .1 = right (audit)
    tmux send-keys -t "$SESSION:sakusen.1" "$init && clear" C-m

    # Step 3: split .1 vertically 50%
    tmux split-window -t "$SESSION:sakusen.1" -v -p 50
    # .0 = left, .1 = right-top (audit), .2 = right-bottom (general)
    tmux send-keys -t "$SESSION:sakusen.2" "$init && clear" C-m

    # Step 4: split .0 vertically 50%
    tmux split-window -t "$SESSION:sakusen.0" -v -p 50
    # .0 = top-left (naval), .1 = bottom-left (army), .2 = top-right (audit), .3 = bottom-right (general)
    tmux send-keys -t "$SESSION:sakusen.1" "$init && clear" C-m

    # --- Send commands to sakusen panes ---

    tmux send-keys -t "$SESSION:sakusen.0" "echo '=== Naval Shell (海軍操作) ==='" C-m
    tmux send-keys -t "$SESSION:sakusen.1" "echo '=== Army Shell (陸軍操作) ==='" C-m

    # Audit log watcher
    tmux send-keys -t "$SESSION:sakusen.2" \
        "watch -n 5 'echo \"=== Audit Log (監査記録) ===\"; echo \"--- Reports ---\"; ls -lt \"$PROJECT_DIR/audit/\" 2>/dev/null | head -15; echo; latest=\"\$(ls -t \"$PROJECT_DIR/audit/\"*_audit.yaml 2>/dev/null | head -1)\"; if [ -n \"\$latest\" ]; then echo \"--- Latest: \$(basename \"\$latest\") ---\"; cat \"\$latest\" 2>/dev/null; fi'" C-m

    tmux send-keys -t "$SESSION:sakusen.3" "echo '=== General Shell (汎用) ==='" C-m

    # ========================================================
    # Final adjustments
    # ========================================================

    # Select orchestrator pane in window 0
    tmux select-window -t "$SESSION:gensui"
    tmux select-pane -t "$SESSION:gensui.0"

    # Set tmux options for the session
    tmux set-option -t "$SESSION" mouse on
    tmux set-option -t "$SESSION" pane-border-status top
    tmux set-option -t "$SESSION" pane-border-format " #{pane_index}: #{pane_title} "
    tmux set-option -t "$SESSION" status-left "#[fg=black,bg=yellow,bold] GOZEN "
    tmux set-option -t "$SESSION" status-right "#[fg=white,bg=blue] %Y-%m-%d %H:%M "

    # Set pane titles for gensui
    tmux select-pane -t "$SESSION:gensui.0" -T "ORCHESTRATOR"
    tmux select-pane -t "$SESSION:gensui.1" -T "Decision/Execution"
    tmux select-pane -t "$SESSION:gensui.2" -T "Naval Queue"
    tmux select-pane -t "$SESSION:gensui.3" -T "Army Queue"
    tmux select-pane -t "$SESSION:gensui.4" -T "Status"

    # Set pane titles for sakusen
    tmux select-pane -t "$SESSION:sakusen.0" -T "Naval Shell"
    tmux select-pane -t "$SESSION:sakusen.1" -T "Army Shell"
    tmux select-pane -t "$SESSION:sakusen.2" -T "Audit Log"
    tmux select-pane -t "$SESSION:sakusen.3" -T "General Shell"

    log_ok "Session '$SESSION' created successfully."
    log_info "  Window 0: gensui  (司令部) - Orchestrator + Monitors"
    log_info "  Window 1: sakusen (作戦室) - Shells + Audit"
    log_info ""
    log_info "Attaching..."

    tmux attach-session -t "$SESSION"
}

# --- Main ---

main() {
    check_deps

    local mode="interactive"
    local task_file=""

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --interactive)
                mode="interactive"
                shift
                ;;
            --task)
                mode="task"
                if [[ -z "${2:-}" ]]; then
                    log_error "--task requires a YAML file argument."
                    exit 1
                fi
                task_file="$2"
                shift 2
                ;;
            --kill)
                kill_session
                exit 0
                ;;
            --attach)
                if tmux has-session -t "$SESSION" 2>/dev/null; then
                    tmux attach-session -t "$SESSION"
                else
                    log_error "No session '$SESSION' to attach to."
                    exit 1
                fi
                exit 0
                ;;
            --help|-h)
                usage
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                usage
                exit 1
                ;;
        esac
    done

    # Build orchestrator command
    local orchestrator_cmd
    if [[ "$mode" == "task" ]]; then
        if [[ ! -f "$task_file" ]]; then
            # Try relative to project dir
            if [[ -f "$PROJECT_DIR/$task_file" ]]; then
                task_file="$PROJECT_DIR/$task_file"
            else
                log_error "Task file not found: $task_file"
                exit 1
            fi
        fi
        orchestrator_cmd="python -m gozen.cli '$task_file'"
    else
        orchestrator_cmd="python -m gozen.cli --interactive"
    fi

    create_session "$orchestrator_cmd"
}

main "$@"
