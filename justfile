# SPDX-License-Identifier: GPL-2.0
# Adapted from 77garuda/amnezia-wg-mac; modified 2026-10-07 for Just tasks.
set shell := ["/bin/bash", "-euo", "pipefail", "-c"]
set positional-arguments
export ROOT := justfile_directory()

# Build the native macOS CLI (the default task).
all: build

# Build the engine, configuration tool, and patched awg-quick.
build:
    @"$ROOT/scripts/build.sh"

# Export committed upstream sources and apply the ordered patches.
prepare:
    #!/bin/bash
    set -euo pipefail
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

# Verify patch applicability and generated shell syntax.
check-patches: prepare

# Run isolated local regression tests.
test: prepare
    #!/bin/bash
    set -euo pipefail
    export BASH_BIN="$(head -n 1 "$ROOT/build/awg-quick" | cut -c 3-)"
    export AWG_QUICK_SCRIPT="$ROOT/build/awg-quick"
    python3 -m unittest discover -s "$ROOT/tests" -v

# Run the upstream Go suite (known AWG ping failure is documented).
test-upstream: prepare
    @cd "$ROOT/build/amneziawg-go" && go test ./...

# Install executable copies and the protected configuration directory.
install:
    @"$ROOT/install.sh"

# Remove installed executables; pass --purge to delete configurations too.
uninstall *args:
    @"$ROOT/uninstall.sh" "$@"

# Symlink build outputs into PREFIX/bin for development.
dev-install: build
    #!/bin/bash
    set -euo pipefail
    source "$ROOT/scripts/common.sh"
    PREFIX="${PREFIX:-$(default_prefix)}"
    [[ -d "$PREFIX/bin" ]] || die "Missing $PREFIX/bin; choose an existing PREFIX."
    for name in amneziawg-go awg awg-quick; do
        ln -sf "$ROOT/bin/$name" "$PREFIX/bin/$name"
    done

# Remove generated outputs without touching the submodules.
clean:
    @rm -rf "$ROOT/bin" "$ROOT/build"

# Check out the parent repository's recorded submodule pins.
init-submodules:
    @git -C "$ROOT" submodule update --init --recursive

# Explicitly fetch both master heads, check patches, and show changed gitlinks.
update-upstreams:
    #!/bin/bash
    set -euo pipefail
    git -C "$ROOT" submodule update --init --remote --checkout src/amneziawg-go src/amneziawg-tools
    just --justfile "$ROOT/justfile" check-patches
    git -C "$ROOT" diff --submodule=log -- src/amneziawg-go src/amneziawg-tools

# Print each checked-out commit and its exact tag, if present.
print-upstreams:
    #!/bin/bash
    set -euo pipefail
    for name in amneziawg-go amneziawg-tools; do
        printf '%s: ' "$name"
        git -C "$ROOT/src/$name" rev-parse HEAD
        git -C "$ROOT/src/$name" describe --tags --exact-match HEAD 2>/dev/null || printf '(no exact tag)\n'
    done
