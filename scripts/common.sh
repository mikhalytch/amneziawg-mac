#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0
# Shared helpers are compatible with macOS /bin/bash 3.2.

die() { printf 'Error: %s\n' "$*" >&2; exit 1; }
say() { printf '>> %s\n' "$*"; }

find_bash() {
    local candidate
    if [[ -n ${BASH_BIN:-} ]]; then
        candidate="$BASH_BIN"
        [[ $candidate == /* && -x $candidate ]] || die "BASH_BIN must be an absolute executable path."
        "$candidate" -c '[[ ${BASH_VERSINFO[0]} -ge 4 ]]' || die "Bash 4+ required. Install: brew install bash"
        printf '%s\n' "$candidate"
        return
    fi
    for candidate in "$(command -v bash)" /opt/homebrew/bin/bash /usr/local/bin/bash; do
        [[ -x $candidate ]] || continue
        if "$candidate" -c '[[ ${BASH_VERSINFO[0]} -ge 4 ]]'; then
            printf '%s\n' "$candidate"
            return
        fi
    done
    die "Bash 4+ required at runtime. Install: brew install bash"
}

require_submodules() {
    local name
    for name in amneziawg-go amneziawg-tools; do
        [[ -e "$ROOT/src/$name/.git" ]] &&
            git -C "$ROOT/src/$name" rev-parse --verify HEAD >/dev/null 2>&1 ||
            die "Missing submodule src/$name. Run: git submodule update --init --recursive (or make init-submodules)."
        git -C "$ROOT/src/$name" diff --quiet HEAD -- ||
            die "src/$name has tracked local edits. Builds export committed sources; save your edits before building."
    done
}

default_prefix() { brew --prefix 2>/dev/null || printf '/usr/local\n'; }
