#!/usr/bin/env bash
#
# Install KiCad MAJOR from the official KiCad PPA, and prove that it is the
# KiCad that ended up on PATH.
#
# Ubuntu 26.04 runners (`ubuntu-latest` since late 2026) enable the amd64v3
# architecture variant, so apt reads only the binary-amd64v3 package indexes.
# The KiCad PPAs build KiCad for plain amd64 only: their amd64v3 index carries
# just the Architecture: all docs and libraries. apt therefore never sees the
# PPA's kicad and silently installs Ubuntu's own, older KiCad instead (9.0.8 on
# 26.04), which cannot open KiCad 10 files ("Failed to load schematic").
#
# The fix limits the PPA source to the machine's dpkg architecture -- Ubuntu's
# workaround for PPAs without variant builds -- and then checks the installed
# major version, so a wrong KiCad fails here instead of later.
#
# Usage: install-kicad.sh MAJOR [APT_INSTALL_ARGS...]
#        (default install arguments: --no-install-recommends kicad)
# APT_SOURCES_DIR overrides /etc/apt/sources.list.d (tests).
set -euo pipefail

major="${1:?usage: install-kicad.sh MAJOR [APT_INSTALL_ARGS...]}"
shift
if [ "$#" -eq 0 ]; then
  set -- --no-install-recommends kicad
fi

ppa="kicad/kicad-${major}.0-releases"
sources_dir="${APT_SOURCES_DIR:-/etc/apt/sources.list.d}"

sudo add-apt-repository --yes "ppa:${ppa}"

# Pin the PPA's deb822 source to the dpkg architecture (amd64, arm64, ...).
# A no-op on releases without architecture variants; legacy .list files
# (Ubuntu 22.04 and older) predate variants and are left alone.
arch="$(dpkg --print-architecture)"
for file in "${sources_dir}"/*.sources; do
  [ -e "$file" ] || continue
  grep -qF "/${ppa}/" "$file" || continue
  grep -q '^Architectures:' "$file" && continue
  sudo sed -i "/^Types:/a Architectures: ${arch}" "$file"
  echo "install-kicad: limited ${file##*/} to ${arch}"
done

sudo apt-get update
sudo apt-get install --yes "$@"

installed="$(kicad-cli version)"
if [ "${installed%%.*}" != "${major}" ]; then
  echo "::error::kicad-bot asked for KiCad ${major}, but kicad-cli reports ${installed}." >&2
  exit 1
fi
echo "install-kicad: KiCad ${installed}"
