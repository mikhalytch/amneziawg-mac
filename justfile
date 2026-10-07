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
    @"$ROOT/scripts/prepare.sh"

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
