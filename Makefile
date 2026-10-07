# SPDX-License-Identifier: GPL-2.0
# Adapted from 77garuda/amnezia-wg-mac; modified 2026-10-07 for submodule builds.
# Upstream sources remain clean; patches and compilation use build/ exports.
ROOT := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
PREFIX ?= $(shell brew --prefix 2>/dev/null || printf /usr/local)

.PHONY: all build prepare check-patches test test-upstream install uninstall dev-install clean init-submodules update-upstreams print-upstreams
all: build

build:
	@"$(ROOT)/scripts/build.sh"

prepare:
	@"$(ROOT)/scripts/prepare.sh"

check-patches: prepare

test: prepare
	@BASH_BIN="$$(head -n 1 "$(ROOT)/build/awg-quick" | cut -c 3-)" AWG_QUICK_SCRIPT="$(ROOT)/build/awg-quick" python3 -m unittest discover -s "$(ROOT)/tests" -v

test-upstream: prepare
	cd "$(ROOT)/build/amneziawg-go" && go test ./...

install:
	@PREFIX="$(PREFIX)" "$(ROOT)/install.sh"

uninstall:
	@PREFIX="$(PREFIX)" "$(ROOT)/uninstall.sh"

dev-install: build
	@test -d "$(PREFIX)/bin" || { echo "Missing $(PREFIX)/bin; choose an existing PREFIX." >&2; exit 1; }
	ln -sf "$(ROOT)/bin/amneziawg-go" "$(PREFIX)/bin/amneziawg-go"
	ln -sf "$(ROOT)/bin/awg" "$(PREFIX)/bin/awg"
	ln -sf "$(ROOT)/bin/awg-quick" "$(PREFIX)/bin/awg-quick"

init-submodules:
	git -C "$(ROOT)" submodule update --init --recursive

# Explicit network/update operation: ordinary builds never move the pins.
update-upstreams:
	git -C "$(ROOT)" submodule update --init --remote --checkout src/amneziawg-go src/amneziawg-tools
	@$(MAKE) --no-print-directory -C "$(ROOT)" check-patches
	git -C "$(ROOT)" diff --submodule=log -- src/amneziawg-go src/amneziawg-tools

print-upstreams:
	@for name in amneziawg-go amneziawg-tools; do \
		printf '%s: ' "$$name"; \
		git -C "$(ROOT)/src/$$name" rev-parse HEAD || exit 1; \
		git -C "$(ROOT)/src/$$name" describe --tags --exact-match HEAD 2>/dev/null || printf '(no exact tag)\n'; \
	done

clean:
	rm -rf "$(ROOT)/bin" "$(ROOT)/build"
