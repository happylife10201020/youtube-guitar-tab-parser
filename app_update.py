"""Checks GitHub for a newer release of this app and installs it.

The app cannot overwrite itself while it is running, so installing happens in
three steps:

1. Ask the GitHub releases API for the latest tag and compare it to
   APP_VERSION. Anything that fails here (no network, rate limit, odd JSON) is
   swallowed: an update check must never get in the way of using the app.
2. Download that platform's asset and unpack it into a staging folder. This
   runs in the background right after the check, so by the time the user
   notices the "update ready" button the bytes are already on disk.
3. On the user's go-ahead, write a tiny helper script, hand it the app's PID,
   and exit. The helper waits for this process to die, swaps the new app over
   the old one, and relaunches it.

Only frozen release builds update themselves. Running from source updates
through git, and a dev build must not be replaced by a release build.
"""

import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import threading
import zipfile
from urllib.request import urlopen, Request

from version import APP_VERSION

REPO = "happylife10201020/youtube-guitar-tab-parser"
LATEST_RELEASE_URL = f"https://api.github.com/repos/{REPO}/releases/latest"
RELEASES_PAGE_URL = f"https://github.com/{REPO}/releases/latest"

# Which release asset belongs to this platform. The CI names them
# GuitarTabParser-mac-v1.2.0.zip / GuitarTabParser-windows-v1.2.0.zip.
ASSET_MARKER = {"darwin": "-mac-", "win32": "-windows-"}

USER_AGENT = f"GuitarTabParser/{APP_VERSION}"
CHECK_TIMEOUT = 15
DOWNLOAD_TIMEOUT = 120


def version_key(version):
    """Sortable key for 'v1.2.10' / '1.2.10'. Unparseable sorts lowest."""
    return tuple(int(n) for n in re.findall(r"\d+", version or "")) or (0,)


def is_newer(candidate, current=APP_VERSION):
    return version_key(candidate) > version_key(current)


def installed_app_path():
    """The file or bundle a new version has to replace, or None when running
    from source.

    macOS ships a GuitarTabParser.app folder (PyInstaller --onedir), so the
    thing to swap is the bundle that contains sys.executable, not the binary
    inside it. Windows ships one .exe, which is sys.executable itself.
    """
    if not getattr(sys, "frozen", False):
        return None
    exe = os.path.abspath(sys.executable)
    if sys.platform == "darwin":
        parts = exe.split(os.sep)
        for i, part in enumerate(parts):
            if part.endswith(".app"):
                return os.sep.join(parts[:i + 1])
        return None
    return exe


def can_self_update():
    """True when this build can replace itself in place.

    Needs a frozen build and write access to the install location *and* its
    parent (the swap deletes and recreates the bundle, which is a write to the
    parent folder). An app in /Applications usually qualifies for an admin
    user; one inside a read-only mount or App Translocation copy does not.
    """
    target = installed_app_path()
    if not target or not os.path.exists(target):
        return False
    if "/AppTranslocation/" in target:
        return False
    return os.access(os.path.dirname(target), os.W_OK) and os.access(target, os.W_OK)


def fetch_latest(timeout=CHECK_TIMEOUT):
    """{'version', 'url', 'name'} for the newest release, or None.

    Returns None rather than raising: a failed check is not an app error.
    """
    marker = ASSET_MARKER.get(sys.platform)
    if not marker:
        return None
    try:
        request = Request(LATEST_RELEASE_URL, headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/vnd.github+json",
        })
        with urlopen(request, timeout=timeout) as response:
            release = json.load(response)
        version = (release.get("tag_name") or "").lstrip("v")
        if not version:
            return None
        for asset in release.get("assets", []):
            name = asset.get("name", "")
            if marker in name and name.endswith(".zip"):
                return {"version": version,
                        "url": asset["browser_download_url"],
                        "name": name}
    except Exception:
        return None
    return None


def _download(url, dest_path, on_progress=None, timeout=DOWNLOAD_TIMEOUT):
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=timeout) as response:
        total = int(response.headers.get("Content-Length") or 0)
        done = 0
        last_pct = -1
        with open(dest_path, "wb") as out:
            while True:
                chunk = response.read(256 * 1024)
                if not chunk:
                    break
                out.write(chunk)
                done += len(chunk)
                if total and on_progress:
                    pct = int(done * 100 / total)
                    if pct > last_pct:
                        last_pct = pct
                        on_progress(pct)
    return dest_path


def stage_update(release, on_progress=None, log=print):
    """Downloads and unpacks `release`; returns the new app's path on disk.

    The staging folder is deliberately left behind: the helper script that runs
    after this process exits still needs it.
    """
    staging = tempfile.mkdtemp(prefix="gtp_update_")
    archive = os.path.join(staging, release["name"])
    log(f"Downloading version {release['version']}...")
    _download(release["url"], archive, on_progress=on_progress)

    unpacked = os.path.join(staging, "unpacked")
    os.makedirs(unpacked, exist_ok=True)
    if sys.platform == "darwin" and shutil.which("ditto"):
        # ditto keeps bundle metadata and symlinks that zipfile flattens.
        subprocess.run(["ditto", "-x", "-k", archive, unpacked], check=True)
    else:
        with zipfile.ZipFile(archive) as zf:
            zf.extractall(unpacked)

    wanted = os.path.basename(installed_app_path() or "")
    for root, dirs, files in os.walk(unpacked):
        for entry in list(dirs) + list(files):
            if entry == wanted:
                return os.path.join(root, entry)
        if sys.platform == "darwin":
            for entry in dirs:
                if entry.endswith(".app"):
                    return os.path.join(root, entry)
        else:
            for entry in files:
                if entry.lower().endswith(".exe"):
                    return os.path.join(root, entry)
    raise RuntimeError("The downloaded update did not contain the app.")


_MAC_HELPER = """#!/bin/sh
# Waits for the running app to exit, swaps in the new one, relaunches it.
PID="$1"; TARGET="$2"; NEW="$3"; STAGING="$4"
i=0
while kill -0 "$PID" 2>/dev/null && [ $i -lt 150 ]; do sleep 0.2; i=$((i+1)); done
BACKUP="${TARGET}.old-$$"
mv "$TARGET" "$BACKUP" || exit 1
if ditto "$NEW" "$TARGET"; then
    xattr -cr "$TARGET" 2>/dev/null
    rm -rf "$BACKUP"
else
    rm -rf "$TARGET"
    mv "$BACKUP" "$TARGET"   # put the working app back
fi
open "$TARGET"
rm -rf "$STAGING"
"""

_WIN_HELPER = """@echo off
rem Waits for the running app to exit, swaps in the new one, relaunches it.
set PID=%~1
set TARGET=%~2
set NEW=%~3
set STAGING=%~4
set /a tries=0
:wait
tasklist /FI "PID eq %PID%" 2>nul | find "%PID%" >nul
if errorlevel 1 goto swap
set /a tries+=1
if %tries% GEQ 60 goto swap
timeout /t 1 /nobreak >nul
goto wait
:swap
move /y "%TARGET%" "%TARGET%.old" >nul
copy /y "%NEW%" "%TARGET%" >nul
if errorlevel 1 (
    move /y "%TARGET%.old" "%TARGET%" >nul
) else (
    del /q "%TARGET%.old" >nul 2>&1
)
start "" "%TARGET%"
rmdir /s /q "%STAGING%" >nul 2>&1
"""


def apply_update(new_app_path, log=print):
    """Spawns the swap helper and returns; the caller should exit right after.

    The helper outlives this process on purpose -- it cannot replace the app
    until the app is gone.
    """
    target = installed_app_path()
    if not target:
        raise RuntimeError("This build cannot update itself.")
    staging = os.path.dirname(os.path.dirname(os.path.abspath(new_app_path)))

    if sys.platform == "win32":
        helper = os.path.join(staging, "apply_update.bat")
        with open(helper, "w", encoding="utf-8") as handle:
            handle.write(_WIN_HELPER)
        command = ["cmd", "/c", helper, str(os.getpid()), target, new_app_path, staging]
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0) \
            | getattr(subprocess, "DETACHED_PROCESS", 0)
        subprocess.Popen(command, close_fds=True, creationflags=creationflags)
    else:
        helper = os.path.join(staging, "apply_update.sh")
        with open(helper, "w", encoding="utf-8") as handle:
            handle.write(_MAC_HELPER)
        os.chmod(helper, os.stat(helper).st_mode | stat.S_IXUSR)
        command = ["/bin/sh", helper, str(os.getpid()), target, new_app_path, staging]
        subprocess.Popen(command, close_fds=True, start_new_session=True)
    log("Restarting to finish the update...")


def start_background_check(on_ready, log=print, enabled=True):
    """Checks for a newer release and pre-downloads it, off the UI thread.

    `on_ready(version, new_app_path)` runs only when an update is downloaded
    and ready to install. Everything else stays silent in the log.
    """
    if not enabled or not can_self_update():
        return

    def work():
        try:
            release = fetch_latest()
            if not release:
                return
            if not is_newer(release["version"]):
                log(f"Up to date (v{APP_VERSION}).")
                return
            log(f"Version {release['version']} is available.")
            new_app = stage_update(release, log=log)
            log(f"Version {release['version']} is ready to install.")
            on_ready(release["version"], new_app)
        except Exception as exc:
            log(f"Update check skipped: {exc}")

    threading.Thread(target=work, daemon=True).start()
