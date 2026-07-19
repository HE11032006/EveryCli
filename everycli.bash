#!/usr/bin/env bash
# EveryCli Bash integration — source this file from your ~/.bashrc or ~/.bash_profile
# 
# Usage:
#   echo '. /path/to/EveryCli/everycli.bash' >> ~/.bashrc
#   source ~/.bashrc
#
# Then simply type:
#   evc "lance tous les containers en arriere plan"
#
# The matched command is inserted into your readline buffer (ready to edit/confirm).

# ── Locate the EveryCli installation ─────────────────────────────────────────

_everycli_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

_everycli_run() {
    # Priority: EVERYCLI_BIN env var > compiled binary > local .venv
    if [[ -n "$EVERYCLI_BIN" && -x "$EVERYCLI_BIN" ]]; then
        "$EVERYCLI_BIN" search "$1" -s
        return
    fi

    local binary="$_everycli_root/everycli"
    if [[ -x "$binary" ]]; then
        "$binary" search "$1" -s
        return
    fi

    local python="$_everycli_root/.venv/bin/python"
    if [[ -x "$python" ]]; then
        "$python" -m everycli.everycli search "$1" -s
        return
    fi

    echo "EveryCli: not found. Set EVERYCLI_BIN or create a local .venv." >&2
    return 1
}

# ── Main function: evc ────────────────────────────────────────────────────────

evc() {
    if [[ $# -eq 0 ]]; then
        echo 'Usage: evc "describe what you want to do"' >&2
        return 1
    fi

    local query="$*"

    # The child process writes the rich display to stderr, and only the raw
    # command to stdout — so we capture stdout cleanly here.
    local selected
    selected="$(_everycli_run "$query" 2>/dev/tty)"
    local exit_code=$?

    if [[ $exit_code -ne 0 || -z "$selected" ]]; then
        return $exit_code
    fi

    # Insert the command into the readline buffer so the user can review/edit
    # it before pressing Enter — we never execute automatically.
    if [[ -n "$READLINE_LINE" ]] || declare -p READLINE_LINE &>/dev/null 2>&1; then
        # We're inside a readline-aware context (bind -x)
        READLINE_LINE="$selected"
        READLINE_POINT="${#READLINE_LINE}"
    else
        # Fallback: print the command so the user can copy it
        printf '%s\n' "$selected"
    fi
}

# ── Readline binding (optional) ───────────────────────────────────────────────
# Bind Ctrl+Space to open an interactive evc prompt.
# Uncomment if you want this shortcut:
# bind -x '"\C- ": _evc_interactive'

_evc_interactive() {
    local query
    read -r -p "evc> " query
    [[ -z "$query" ]] && return
    evc "$query"
}
