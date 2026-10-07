#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0
# Adapted from 77garuda/amnezia-wg-mac; modified 2026-10-07 for submodule builds.
# Build and install real copies; configs remain separate from this checkout.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
source "$ROOT/scripts/common.sh"
[[ $(uname -s) == Darwin ]] || die "This installer is macOS-only."
PREFIX="${PREFIX:-$(default_prefix)}"
BINDIR="$PREFIX/bin"
CONFDIR="/etc/amnezia/amneziawg"
[[ -d $BINDIR ]] || die "Target $BINDIR does not exist. Install Homebrew or choose an existing PREFIX."
just --justfile "$ROOT/justfile" build

do_install() {
    local mode="$1" src="$2" dst="$3"
    if [[ -w $(dirname "$dst") ]]; then
        install -m "$mode" "$src" "$dst"
    else
        sudo install -m "$mode" "$src" "$dst"
    fi
}
for name in amneziawg-go awg awg-quick; do
    do_install 0755 "$ROOT/bin/$name" "$BINDIR/$name"
done
sudo mkdir -p "$CONFDIR"
sudo chown root:wheel "$CONFDIR"
sudo chmod 0700 "$CONFDIR"
if [[ ! -e "$CONFDIR/awg0.conf.example" ]]; then
    sudo install -m 0600 "$ROOT/conf/awg0.conf.example" "$CONFDIR/awg0.conf.example"
fi
cat <<EOF
Installed into $BINDIR. Configurations live in $CONFDIR.

Create your configuration, fill in the real keys and server parameters:
  sudo cp $CONFDIR/awg0.conf.example $CONFDIR/awg0.conf
  sudo \${EDITOR:-nano} $CONFDIR/awg0.conf
  sudo chmod 600 $CONFDIR/awg0.conf

Then connect or disconnect:
  sudo $BINDIR/awg-quick up awg0
  sudo $BINDIR/awg-quick down awg0

Stop any other client using the same private key before connecting.
The installed executables do not depend on this checkout. Bash 4+ remains required.
EOF
