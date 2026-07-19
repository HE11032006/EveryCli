#!/usr/bin/env zsh
# EveryCli Zsh integration — source this file from your ~/.zshrc
#
# Usage:
#   echo '. /path/to/EveryCli/everycli.zsh' >> ~/.zshrc
#   source ~/.zshrc
#
# Then simply type:
#   evc "lance tous les containers en arriere plan"
#
# The matched command is inserted into your ZLE buffer (ready to edit/confirm).

# ── Locate the EveryCli installation ─────────────────────────────────────────

_everycli_root="${0:A:h}"  # Resolve symlinks; get directory of this script

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

    print -u2 "EveryCli: not found. Set EVERYCLI_BIN or create a local .venv."
    return 1
}

# ── Main function: evc ────────────────────────────────────────────────────────

evc() {
    if [[ $# -eq 0 ]]; then
        print -u2 'Usage: evc "describe what you want to do"'
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

    # Insert the command into the ZLE buffer so the user can review/edit
    # before pressing Enter — we NEVER execute automatically.
    if [[ -n "$ZLE_STATE" ]]; then
        # We're in ZLE (normal interactive shell) — use zle to insert
        print -z "$selected"
    else
        # Fallback (e.g. inside a script): just print it
        print -- "$selected"
    fi
}

# ── ZLE widget binding (optional) ────────────────────────────────────────────
# Bind Ctrl+Space to open an interactive evc prompt from within the ZLE buffer.

_evc_zle_widget() {
    local query
    # Temporarily exit ZLE to accept input
    zle -I
    print -n "evc> " >/dev/tty
    read -r query </dev/tty
    [[ -z "$query" ]] && zle reset-prompt && return

    local selected
    selected="$(_everycli_run "$query" 2>/dev/tty)"
    if [[ -n "$selected" ]]; then
        LBUFFER="$selected"
    fi
    zle reset-prompt
}

zle -N _evc_zle_widget
# Uncomment to bind Ctrl+Space:
# bindkey '^ ' _evc_zle_widget
