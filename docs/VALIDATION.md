# Validation — 2026-10-07

Environment: macOS, Apple Silicon (`darwin/arm64`), Go `go1.27.1`, Bash `5.3.20`,
Xcode Command Line Tools. Upstream pins and their exact tags are listed in the
README; both official remote master heads were checked with `git ls-remote`.

## Local port

- Native build: passed; `amneziawg-go`, `awg`, and `awg-quick` are generated.
- Engine reports `v3.1.20260828`; C tool reports `v3.1.20260812`.
- Local regression suite: 13 tests passed. It exercises real Darwin functions
  with temporary configuration/name/socket files and controlled route commands,
  plus clean export preparation and its missing-source/dirty-source/conflict
  failures. The test's CLI help check uses upstream's stderr output convention.
- Bash 3.2 parses the bootstrap/install scripts; generated awg-quick selects
  Bash 4+ explicitly. The old Bash override is rejected by a regression test.
- Both submodules remain clean. The original project and sibling repositories
  were not modified. The existing untracked `src/tmp/` in the sibling tools
  checkout predates this work.
- Original license notice and full GPLv2 text are preserved byte-for-byte.

## Upstream suite limitation

The full upstream suite is **not green** on this machine. With downloads routed
through the official Go proxy, all tested packages pass except `device`, where
`TestAWGDevicePing` times out in both directions:

```text
TestAWGDevicePing/ping_1.0.0.1: device_test.go:245: ping did not transit
TestAWGDevicePing/ping_1.0.0.2: device_test.go:248: pong did not transit
```

The same test fails against the unmodified sibling `amneziawg-go` checkout at
the identical master commit. The exported device source is unchanged. This
establishes that the failure is reproducible without the macOS port; it does not
establish whether its ultimate cause is an upstream defect or this environment.
The requested master pin is retained; this port adds no Go protocol patches.

Initial testing with this machine's `GOPROXY=direct` also failed to resolve the
gVisor revision. The official Go proxy returned the correct revision, downloaded
it with checksum validation, and the netstack/Outline packages then built or
passed their tests. The retry changes the proxy for that command only:

```sh
GOPROXY=https://proxy.golang.org,direct just test-upstream
```

To reproduce the remaining failure without running the full suite:

```sh
cd src/amneziawg-go
go test ./device -run '^TestAWGDevicePing$' -count=1
```

## Boundaries

No real VPN configuration, live server, privileged tunnel, system installation,
route change, or DNS change was exercised. Nothing was published during
validation. A real tunnel smoke test is still required before treating this as
validated for production connectivity. Review of this port was performed by its implementing
agent; no subagents were used.
