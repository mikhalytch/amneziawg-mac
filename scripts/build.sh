#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
source "$ROOT/scripts/common.sh"
[[ $(uname -s) == Darwin ]] || die "This project builds the macOS CLI only."
require_submodules
find_bash >/dev/null
command -v go >/dev/null || die "Go 1.25+ required. Install: brew install go"
go_version="$(go version)"
[[ $go_version =~ go([0-9]+)\.([0-9]+) ]] || die "Cannot determine Go version: $go_version"
[[ ${BASH_REMATCH[1]} -gt 1 || ${BASH_REMATCH[2]} -ge 25 ]] || die "Go 1.25+ required. Install: brew install go"
xcode-select -p >/dev/null 2>&1 || die "Xcode Command Line Tools required. Run: xcode-select --install"
command -v clang >/dev/null || die "clang required. Run: xcode-select --install"

just --justfile "$ROOT/justfile" prepare
mkdir -p "$ROOT/bin"
say "Building amneziawg-go"
(cd "$ROOT/build/amneziawg-go" && go build -trimpath -o "$ROOT/bin/amneziawg-go")
say "Building awg"
make -C "$ROOT/build/amneziawg-tools/src" all
install -m 0755 "$ROOT/build/amneziawg-tools/src/wg" "$ROOT/bin/awg"
install -m 0755 "$ROOT/build/awg-quick" "$ROOT/bin/awg-quick"
say "Built amneziawg-go, awg, and awg-quick in $ROOT/bin"
