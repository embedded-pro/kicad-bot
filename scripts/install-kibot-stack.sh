#!/usr/bin/env bash
#
# Install the KiBot stack (KiBot + KiCost + KiDiff) and its native dependencies.
#
# kibot depends on wxPython, which publishes no universal manylinux wheel on
# PyPI for most releases. Without a matching prebuilt wheel, pip falls back to
# compiling wxPython from source against the GTK/wx headers -- a slow build that
# frequently fails on CI runners with:
#
#     error: failed-wheel-build-for-install
#     Failed to build installable wheels for some pyproject.toml based projects
#     wxPython
#
# To avoid that, we install a prebuilt wxPython wheel from the official extras
# index that matches the runner's Ubuntu release, restricting pip to binary
# wheels so it can never silently fall back to a source build. Only once
# wxPython is satisfied do we install the rest of the stack.
#
# Usage: install-kibot-stack.sh [KICAD_MAJOR_VERSION]
set -euo pipefail

kicad_version="${1:-9}"

# System packages: KiCad itself, a headless X server for the GUI-bound tools,
# and the GTK runtime libraries the prebuilt wxPython wheel links against at
# import time.
sudo add-apt-repository --yes "ppa:kicad/kicad-${kicad_version}.0-releases"
sudo apt-get update
sudo apt-get install --yes \
  kicad \
  xvfb \
  libgtk-3-0 \
  libnotify4 \
  libsdl2-2.0-0

# Resolve the Ubuntu release so we can fetch the matching prebuilt wxPython
# wheel from the extras index (folders are named e.g. ubuntu-24.04).
ubuntu_release=""
if [ -r /etc/os-release ]; then
  # shellcheck disable=SC1091
  ubuntu_release="$(. /etc/os-release && echo "${VERSION_ID:-}")"
fi
wx_index="https://extras.wxpython.org/wxPython4/extras/linux/gtk3/ubuntu-${ubuntu_release}"

# Install wxPython first, as a binary wheel only. --only-binary guarantees pip
# never falls back to a source build (the original failure mode); if no matching
# wheel exists the command fails loudly instead of compiling for several minutes.
pip install --only-binary wxPython --find-links "${wx_index}" wxPython

# With wxPython already satisfied, the rest of the stack installs without trying
# to build it from source.
pip install kibot kicost kidiff
