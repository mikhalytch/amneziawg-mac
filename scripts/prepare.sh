#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
source "$ROOT/scripts/common.sh"
require_submodules
BASH_BIN="$(find_bash)"
mkdir -p "$ROOT/build"
stage="$(mktemp -d "$ROOT/build/.prepare.XXXXXX")"
trap 'rm -rf "$stage"' EXIT

for name in amneziawg-go amneziawg-tools; do
    mkdir "$stage/$name"
    git -C "$ROOT/src/$name" archive HEAD | tar -x -C "$stage/$name"
done

# Git must not discover the parent repository: patches target the export only.
while IFS= read -r patch_name || [[ -n $patch_name ]]; do
    [[ -n $patch_name && $patch_name != \#* ]] || continue
    [[ $patch_name != */* ]] || die "Invalid patch name in patches/series: $patch_name"
    say "Applying $patch_name"
    (
        cd "$stage/amneziawg-tools"
        export GIT_CEILING_DIRECTORIES="$ROOT/build"
        git apply --check "$ROOT/patches/$patch_name"
        git apply "$ROOT/patches/$patch_name"
    )
done < "$ROOT/patches/series"

version="$(git -C "$ROOT/src/amneziawg-go" describe --tags --always)"
printf 'package main\n\nconst Version = "%s"\n' "$version" > "$stage/amneziawg-go/version.go"
{
    printf '#!%s\n' "$BASH_BIN"
    tail -n +2 "$stage/amneziawg-tools/src/wg-quick/darwin.bash"
} > "$stage/awg-quick"
chmod 0755 "$stage/awg-quick"
"$BASH_BIN" -n "$stage/awg-quick"

for name in amneziawg-go amneziawg-tools awg-quick; do
    rm -rf "$ROOT/build/$name"
    mv "$stage/$name" "$ROOT/build/$name"
done
{
    for name in amneziawg-go amneziawg-tools; do
        printf '%s %s\n' "$name" "$(git -C "$ROOT/src/$name" rev-parse HEAD)"
    done
} > "$ROOT/build/upstream-revisions.txt"
say "Prepared clean source exports; upstream submodules were not modified."
