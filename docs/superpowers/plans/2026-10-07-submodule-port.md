# Submodule Port Implementation Plan

**Goal:** Port the complete macOS CLI project with current upstream master pins
and maintainable local patches.

**Architecture:** Clean official submodules provide committed sources. Build
exports receive the ordered Darwin patches. Root scripts own build/install flows.

**Tech stack:** Git, Make, Bash, Go 1.25+, clang; Python 3 for behavioral tests.

**Spec:** `docs/superpowers/specs/2026-10-07-submodule-port-design.md`.

## Global constraints

- Work in the user-selected `~/prj/amneziawg-mac`; retain the source repository.
- Preserve every existing patch and surrounding addition.
- Pin both verified official master heads and configure branch=master.
- Keep upstream submodules clean, builds offline unless dependencies need download.
- No system installation, live tunnel changes, or push. Local commits were
  authorized by the caller after port validation.

## Tasks

- [x] Add official submodules and verify remote master pins.
- [x] Write/run failing Darwin behavior tests against upstream and legacy scripts.
- [x] Port patches and add SaveConfig/Table=off/route ownership corrections.
- [x] Implement build exports, Bash prerequisites, Make targets, installer/uninstaller.
- [x] Port/update config, license, internals, checkout and maintenance documentation.
- [x] Build and test, check patch failures and clean submodules, review final diff.

## Execution results

The 13 local regression tests and native build pass. Upstream testing was run;
its remaining TestAWGDevicePing failure reproduces on the unchanged upstream
checkout. Retain the caller-requested master pins rather than adding an engine
patch or downgrading. See `docs/VALIDATION.md` for the evidence and limits.

The source project remains untouched. The caller subsequently authorized local
commits grouped by source pins, original port/build workflow, route safety fixes,
and documentation. No push, installation, or live VPN activation was requested.
No subagents were requested or used.

## Review focus

Missing submodules must produce a recovery command. Repeated preparation must not
double-apply patches. Patch conflicts must fail the build. SaveConfig must retain
exclusions. Table=off must not touch exclusion routes. Tests must not alter host
networking. Installer must use Bash 4+ under sudo and keep configs by default.
