# AmneziaWG macOS submodule port

Port the complete CLI project from `~/prj/amnezia-wg-mac` to the existing empty
repository at `~/prj/amneziawg-mac`. Preserve its CLI, production installation,
development installation, uninstall, config template, and macOS routing extension.

## Source ownership

Use `src/amneziawg-go` and `src/amneziawg-tools` as Git submodules with official
HTTPS URLs and update branch `master`. Start at verified remote master commits
`b5928efb6ca19f0153958460c3d141f04abc5c2e` and
`ee0f0a9aa34ff0a0da4b3433b9512781cfe02843`, respectively. Gitlinks pin builds;
normal builds never fetch or advance the pins. No local Go protocol changes.

Export committed submodule sources into ignored `build/` directories. Apply an
ordered patch series to the exported tools tree, never the submodule checkout.
Build Go and C from the exports; collect three executables in `bin/`.

## Patches and corrections

Preserve the three Darwin runtime-path corrections, seven awg command fixes,
and ExcludeIPs parsing, route lifecycle, gateway refresh, and help. Add a separate
correction patch preserving ExcludeIPs during SaveConfig, respecting Table=off,
avoiding duplicate route additions, and tracking only successfully added routes
for cleanup. Warn on failed additions or missing gateways.
Require Bash 4+ at build/install time and use its absolute path in the generated
script shebang, including when launched through sudo. Go requires 1.25+ as upstream
does; Xcode command line tools provide the C toolchain.

## Installation and maintenance

Install executable copies and a private system configuration directory. Preserve
configs on uninstall unless --purge is explicit. Auto-detect Homebrew prefix,
permit PREFIX override, and support dev symlinks. Document recursive clone,
existing-checkout initialization, explicit master updates, review/recording of
new gitlinks, patch conflicts, and runtime verification.

## Verification

Behavior tests execute the real Darwin functions with temporary configs/runtime
files and controlled OS route commands. Cover strip, IPv4/IPv6 exclusions,
Table=off, save/reload, interface discovery/cleanup, and gateway changes. Check
missing-submodule diagnostics, repeated preparation, patch conflicts, clean
submodules, native build, executable versions, and upstream Go tests. Do not
change the host's VPN, routing table, DNS, or installed executables during tests.
