#!/bin/bash
# ============================================================
#  Builds GuitarTabParser.app -- a single, double-click-to-run
#  macOS app. Run this ON A MAC (PyInstaller cannot cross-build
#  a Mac app from Windows/Linux).
#  Requires Python 3.8+ installed (python3 on PATH).
#  The person you share the app with needs NOTHING installed.
# ============================================================
set -e

cd "$(dirname "$0")"

echo "Setting up build environment..."
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt pyinstaller

echo "Building GuitarTabParser.app..."
python3 -m PyInstaller --noconfirm --onefile --windowed --name GuitarTabParser \
  --collect-all yt_dlp \
  app.py

echo
echo "============================================================"
echo " Done!  Your app is here:  dist/GuitarTabParser.app"
echo " Share that app bundle (zip it first: right-click -> Compress)."
echo "============================================================"
