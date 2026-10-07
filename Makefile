# SPDX-License-Identifier: GPL-2.0
# Project tasks moved to justfile on 2026-10-07. This file prints references only.
.PHONY: all build prepare check-patches test test-upstream install uninstall dev-install clean init-submodules update-upstreams print-upstreams

all build prepare check-patches test test-upstream install uninstall dev-install clean init-submodules update-upstreams print-upstreams:
	@printf 'Project tasks use Just. Run: just %s\n' '$@'

.DEFAULT:
	@printf '%s\n' 'Project tasks use Just. Run: just --list'
