#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

export PYINSTALLER_NO_CODESIGN=1

python -m PyInstaller --clean --noconfirm mac_app/SuperLibraryMachine.spec

echo "App bundle generated under dist/SuperLibraryMachine.app"
