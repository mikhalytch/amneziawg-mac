# AmneziaWG CLI for macOS

Build and run AmneziaWG on macOS from the command line, without the Amnezia GUI:

```sh
sudo awg-quick up awg0
sudo awg-quick down awg0
```

This project ports the macOS fixes and packaging from
[77garuda/amnezia-wg-mac](https://github.com/77garuda/amnezia-wg-mac), using
official upstream **Git submodules** instead of vendored source copies. The Go
engine and C configuration tool retain upstream behavior; local patches adapt
the Darwin `awg-quick` script and add the `ExcludeIPs` routing extension.

## Upstream sources and pinned versions

The directories under `src/` are Git submodules. The parent repository records
an exact commit for each, making a checkout reproducible. Both submodules are
configured with `branch = master` for explicit updates; this does **not** make
ordinary checkout or build commands automatically follow the moving branch.

These pins were verified against the official remote `master` heads on
2026-10-07:

| Submodule | Exact tag at the pinned commit | Full commit SHA | Update branch |
| --- | --- | --- | --- |
| [amneziawg-go](https://github.com/amnezia-vpn/amneziawg-go) | `v3.1.20260828` | `b5928efb6ca19f0153958460c3d141f04abc5c2e` | `master` |
| [amneziawg-tools](https://github.com/amnezia-vpn/amneziawg-tools) | `v3.1.20260812` | `ee0f0a9aa34ff0a0da4b3433b9512781cfe02843` | `master` |

The original macOS project bundled Go `v0.2.19` and tools `v1.0.20260618-2`.
This port uses AWG 3.1 sources. Copy configuration parameters from your provider
or server; the bundled template intentionally illustrates only basic settings.

## Prerequisites

```sh
xcode-select --install
brew install go bash just
```

- **Xcode Command Line Tools** provide clang and make for the upstream C tool.
- **Just** runs this project's tasks; install it with `brew install just`.
- **Go 1.25+** builds the engine; Go is not required after installation.
- **Bash 4+ is required at runtime.** macOS `/bin/bash` 3.2 cannot run this
  script. The build locates a suitable Bash and writes its absolute path into
  the generated `awg-quick` shebang so `sudo` does not select the old shell.
- Git and tar export the submodule sources. Python 3 is needed only for tests.

Homebrew is used to discover the installation prefix, normally `/opt/homebrew`
on Apple Silicon or `/usr/local` on Intel. An existing custom prefix can be
selected with `PREFIX=...`. Set `BASH_BIN=/absolute/path/to/bash` if needed.

## Get a complete checkout

Once this repository has a remote, clone it recursively:

```sh
git clone --recurse-submodules <this-repository-url> amneziawg-mac
cd amneziawg-mac
just
```

For an existing checkout or a clone made without `--recurse-submodules`:

```sh
cd ~/prj/amneziawg-mac
git submodule update --init --recursive
# Equivalent convenience target: just init-submodules
just
```

After pulling parent-repository changes, synchronize and check out its recorded
pins before rebuilding:

```sh
git pull
git submodule sync --recursive
git submodule update --init --recursive
just
```

`just` reports the initialization command if a submodule is missing. Ordinary
builds use the currently checked-out committed submodule revisions and do not
fetch upstream updates. Tracked local edits inside a submodule are rejected;
put macOS adaptations in `patches/` instead.

## Build and install

Run `just --list` to see all available tasks. The default `just` task builds
the three executables. Use `PREFIX=... just install` to override the destination.

```sh
just                         # outputs bin/amneziawg-go, bin/awg, bin/awg-quick
./install.sh                 # builds, then installs real copies
# Optional override: PREFIX=/usr/local ./install.sh
```

`just install` installs executable copies using the production installer. It installs the three executables
into `$PREFIX/bin`, creates root-owned `/etc/amnezia/amneziawg` with mode `0700`,
and places a configuration example there with mode `0600`. It never overwrites
a real configuration. No LaunchDaemon or kernel extension is installed.

The binaries are native to the machine doing the build. After a normal install,
the checkout can be moved or removed. Keep the selected Bash installation.

For development, `just dev-install` creates symlinks into this checkout; the
checkout must stay in place. `just clean` removes only generated `bin/` and
`build/` files and leaves upstream submodules intact.

## Configure and run

```sh
sudo cp /etc/amnezia/amneziawg/awg0.conf.example /etc/amnezia/amneziawg/awg0.conf
sudo ${EDITOR:-nano} /etc/amnezia/amneziawg/awg0.conf
sudo chmod 600 /etc/amnezia/amneziawg/awg0.conf

sudo awg-quick up awg0
sudo awg show
sudo awg-quick down awg0
```

Replace every placeholder and use your assigned address, server public key,
endpoint, and obfuscation parameters. `S1`–`S4` and `H1`–`H4` must agree with
the server; junk/signature packet settings are client-side. If the server uses
AWG 3.x features such as `HeaderProtectionKey`, copy those settings as well.

The config filename before `.conf` is the logical interface name, at most 15
characters. The real interface is a kernel-assigned `utunN`. A config can also
be supplied by path: `sudo awg-quick up ./awg0.conf`.

## Local additions and fixes

The ordered series in `patches/series` is applied to an exported tools source
tree under `build/`, leaving the upstream submodule unmodified:

1. **`01-darwin-cli-fixes.patch`** ports all three runtime-directory corrections
   from `/var/run/wireguard` to `/var/run/amneziawg`, and all seven `wg` → `awg`
   command substitutions. These fix interface discovery, configuration, and
   cleanup on macOS.
2. **`02-exclude-ips.patch`** ports the full custom extension: parsing, stripping,
   IPv4/IPv6 bypass routes, cleanup, gateway refresh, and command help.
3. **`03-exclude-ips-safety.patch`** preserves exclusions across `save` and
   `SaveConfig`, respects `Table = off`, avoids duplicate additions, and removes
   only routes successfully added by this script. Route-add failures and missing
   gateways produce warnings.

The root Makefile, production installer, uninstaller, dev-install flow,
configuration example, troubleshooting documentation, and license notice are
also ported. New build helpers export committed sources before compiling; the
Go version string is generated from the pinned revision in the export. The Go
and C protocol implementations receive no local changes.

### Optional ExcludeIPs

```ini
[Interface]
ExcludeIPs = 192.168.0.0/24, 10.20.0.0/16
```

The script routes these destinations through the ordinary gateway while leaving
`AllowedIPs` unchanged. It refreshes owned bypass routes when the gateway changes
in the upstream automatic full-tunnel routing mode. Cleanup is handled by the
background route monitor when the tunnel closes. A subnet with an existing route
may reject an addition; that existing route is left untouched.

## Safety reminders

- Real `.conf` files contain private keys. Keep them out of Git, use mode `0600`,
  and avoid posting configurations or secret-bearing command output. The example
  has placeholders; there are no usable keys in this repository.
- `ExcludeIPs` traffic bypasses the VPN and leaves through your normal network.
  Use it only for destinations you deliberately want to exclude. It is a macOS
  routing extension, not an upstream engine feature or an anonymity guarantee.
- Check route warnings: a missing gateway or failed route addition means the
  requested bypass was not installed. `Table = off` disables exclusion routes too.
- Stop the Amnezia GUI or any other client using the same private key before
  connecting; concurrent clients can compete for the server's peer endpoint.
- Configuration hooks (`PreUp`, `PostUp`, `PreDown`, `PostDown`) execute commands
  as root. Run only configurations and source revisions you trust.
- `sudo` is needed for tunnel creation, routing, and DNS changes. `just test`
  uses temporary files and simulated routing commands instead of changing the
  machine's VPN, routes, DNS, or installed executables.
- Uninstall preserves configs by default. `./uninstall.sh --purge` deletes them
  permanently. Use the same `PREFIX` used for installation.

Verify routing with your real configuration:

```sh
route -n get 8.8.8.8          # full tunnel: interface should be utunN
route -n get 10.20.0.1       # configured exclusion: ordinary interface/gateway
```

## Updating upstream pins

Updates are explicit; `branch = master` is an update preference, not a floating
dependency. To fetch both official master heads and check patch applicability:

```sh
just update-upstreams
just
just test
just test-upstream
just print-upstreams
```

Review the upstream changes and update the versions table above with each full
SHA and exact tag (`git -C src/amneziawg-go tag --points-at HEAD`, likewise for
tools). If a commit has no exact tag, state that and retain its full SHA. Then
record the new gitlinks and README in a parent-repository commit:

```sh
git add src/amneziawg-go src/amneziawg-tools README.md
git commit -m "Update AmneziaWG upstream pins"
```

If an update conflicts with a patch, preparation stops. Review the upstream
change, adjust or retire the patch, and rerun checks. Do not use a stale generated
binary after a failed build. To restore the currently recorded pins:

```sh
git submodule update --init --recursive
just
```

## Checks and troubleshooting

```sh
just check-patches            # clean exports, ordered patch checks, shell syntax
just test                     # local Darwin and build-workflow regressions
just test-upstream            # upstream Go suite in the build export
just print-upstreams          # actual checked-out submodule revisions
```

Missing submodules: run `just init-submodules`. Missing Go/clang/Bash: install the
prerequisites above. If commands are not found after installation, check that
`$PREFIX/bin` is on your shell's and sudo's command search path, or invoke the
installed executable by absolute path. If a tunnel has no handshake, verify
server parameters and ensure no second client is using the same key.

See [docs/INTERNALS.md](docs/INTERNALS.md) for the original failure mechanism and
the patch/build architecture.

If dependency downloads fail with a locally configured `GOPROXY=direct`, retry
using the official Go proxy for that command only:

```sh
GOPROXY=https://proxy.golang.org,direct just test-upstream
```

Validation results and any inherited upstream test failures are recorded in
[docs/VALIDATION.md](docs/VALIDATION.md). Passing the build and local regressions
does not establish connectivity to your real VPN server.

## Uninstall

```sh
./uninstall.sh                # removes executables, keeps configs
./uninstall.sh --purge        # also removes the system config directory
```

## Attribution and licenses

The original macOS patch and packaging work comes from
[77garuda/amnezia-wg-mac](https://github.com/77garuda/amnezia-wg-mac), commit
`7d3d26246fe5ccf3f6f5f5978c77f6dc55b0acba`. Its original notice is preserved in
[LICENSES/amnezia-wg-mac-NOTICE](LICENSES/amnezia-wg-mac-NOTICE).

Local patches, packaging, documentation, and tests are provided under GPL-2.0;
see [LICENSE](LICENSE) and the full license in [COPYING](COPYING). The upstream
Go engine retains MIT and the tools retain GPL-2.0, with their original notices
inside their submodules. Reuse and redistribution must preserve the applicable
notices and license terms. Binary redistribution requires corresponding GPL
source/build materials or another source-provision method allowed by GPLv2;
a submodule link alone is not a complete binary-distribution source package.
