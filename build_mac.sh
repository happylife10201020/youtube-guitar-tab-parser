#!/bin/bash
# ============================================================
#  Builds the macOS app. Run this ON A MAC (PyInstaller cannot
#  cross-build). Requires Python 3.8+ (python3 on PATH).
#
#  Two build modes:
#    ./build_mac.sh              -> dev build   (GuitarTabParserDev.app,
#                                   verbose Details log box)
#    RELEASE=1 ./build_mac.sh    -> release build (GuitarTabParser.app,
#                                   no Details box; logs go to a file)
#
#  yt-dlp is NOT frozen into the app: it is shipped as a wheel data
#  file, extracted to the user's app-data folder on first run, and
#  auto-updated from PyPI in the background (see ytdlp_runtime.py).
# ============================================================
set -e

cd "$(dirname "$0")"

if [ -n "$RELEASE" ]; then
  MODE=release; NAME=GuitarTabParser
else
  MODE=dev; NAME=GuitarTabParserDev
fi
echo "Building $NAME ($MODE mode)..."

echo "Setting up build environment..."
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt pyinstaller

echo "Fetching the yt-dlp wheel to ship with the app..."
mkdir -p build_assets
python3 -m pip download yt-dlp --no-deps --dest build_assets --quiet
cp "$(ls build_assets/yt_dlp-*.whl | sort | tail -1)" build_assets/ytdlp.whl

# Baked-in build flavor (see app.py).
if [ "$MODE" = release ]; then
  echo "IS_RELEASE = True" > build_config.py
else
  echo "IS_RELEASE = False" > build_config.py
fi

# --exclude-module yt_dlp keeps the frozen (rotting) copy out of the app;
# the wheel data file + ytdlp_runtime.py replace it. The --collect-all
# packages are yt-dlp's optional helpers (HTTP backends, crypto, metadata)
# that must still ship so the runtime-loaded yt-dlp can find them. The full
# standard library is included as hidden imports because the runtime-loaded
# yt-dlp (any future version) may import stdlib modules the app itself never
# references -- PyInstaller would otherwise prune them.
STDLIB_HIDDEN=$(python3 -c "import sys; skip={'antigravity','this','idlelib','turtledemo','turtle','test'}; print(' '.join('--hidden-import='+m for m in sys.stdlib_module_names if not m.startswith('_') and m not in skip))")

python3 -m PyInstaller --noconfirm --onefile --windowed --name "$NAME" \
  --exclude-module yt_dlp \
  --add-data "build_assets/ytdlp.whl:." \
  --collect-all certifi \
  --collect-all requests \
  --collect-all urllib3 \
  --collect-all websockets \
  --collect-all mutagen \
  --collect-all Cryptodome \
  --hidden-import brotli \
  $STDLIB_HIDDEN \
  app.py

echo
echo "============================================================"
echo " Done!  Your app is here:  dist/$NAME.app"
echo " Share that app bundle (zip it first: right-click -> Compress)."
echo "============================================================"
