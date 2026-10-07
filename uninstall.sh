#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0
# Adapted from 77garuda/amnezia-wg-mac; modified 2026-10-07 for submodule builds.
# Preserve configs unless the user explicitly requests --purge.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
source "$ROOT/scripts/common.sh"
[[ $# -le 1 && ( $# -eq 0 || $1 == --purge ) ]] || die "Usage: ./uninstall.sh [--purge]"
PREFIX="${PREFIX:-$(default_prefix)}"
BINDIR="$PREFIX/bin"
CONFDIR="/etc/amnezia/amneziawg"
for name in amneziawg-go awg awg-quick; do
    path="$BINDIR/$name"
    [[ -e $path || -L $path ]] || continue
    if [[ -w $BINDIR ]]; then rm -f "$path"; else sudo rm -f "$path"; fi
    say "Removed $path"
done
if [[ ${1:-} == --purge ]]; then
    sudo rm -rf "$CONFDIR"
    say "Removed $CONFDIR and its configurations"
else
    say "Keeping configurations in $CONFDIR (use --purge to delete them)"
fi
