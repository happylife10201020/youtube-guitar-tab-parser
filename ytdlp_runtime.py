"""Loads yt-dlp from a user-writable folder and keeps it up to date.

YouTube changes its player and anti-bot checks all the time, and yt-dlp answers
with frequent releases. A PyInstaller app freezes whatever yt-dlp existed at
build time, so a bundled copy silently rots until downloads stop working. To
avoid that, the build ships yt-dlp as a plain *wheel file* (a data file -- the
package itself is excluded from the frozen imports):

- On first run the wheel is extracted into the user's app-data folder and
  yt-dlp is imported from there.
- On every launch a background thread asks PyPI for the newest version and, if
  there is one, installs it next to the current one. The new version is picked
  up on the next run, so a run that is already in progress is never disturbed.
- Running from source (not frozen) simply falls back to the pip-installed
  package when no extracted copy exists.

yt-dlp is pure Python, so "installing" a wheel is just unzipping it -- no pip
needed at runtime.
"""

import json
import os
import re
import shutil
import sys
import threading
import zipfile
from urllib.request import urlopen, Request

APP_NAME = "GuitarTabParser"
PYPI_JSON_URL = "https://pypi.org/pypi/yt-dlp/json"
KEEP_VERSIONS = 2   # newest copies to keep; older ones are pruned

_lock = threading.Lock()
_ytdlp = None


def data_dir():
    """Per-user, writable folder for this app (created on demand)."""
    if sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Application Support")
    elif sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    else:
        base = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    path = os.path.join(base, APP_NAME)
    os.makedirs(path, exist_ok=True)
    return path


def _pkg_root():
    path = os.path.join(data_dir(), "yt-dlp")
    os.makedirs(path, exist_ok=True)
    return path


def _ver_key(version):
    """Sortable key for versions like '2026.08.11'."""
    return tuple(int(n) for n in re.findall(r"\d+", version)) or (0,)


def _installed_versions():
    """[(version, dir)] of extracted copies, newest first."""
    root = _pkg_root()
    found = []
    for name in os.listdir(root):
        path = os.path.join(root, name)
        if os.path.isdir(path) and os.path.isdir(os.path.join(path, "yt_dlp")):
            found.append((name, path))
    return sorted(found, key=lambda item: _ver_key(item[0]), reverse=True)


def _bundled_wheel():
    """Path to the wheel shipped inside the app, or None when running from
    source without one."""
    if getattr(sys, "frozen", False):
        candidate = os.path.join(getattr(sys, "_MEIPASS", ""), "ytdlp.whl")
    else:
        candidate = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 "build_assets", "ytdlp.whl")
    return candidate if os.path.isfile(candidate) else None


def _wheel_version(wheel_path):
    """Version encoded in the wheel's dist-info directory name."""
    with zipfile.ZipFile(wheel_path) as zf:
        for name in zf.namelist():
            match = re.match(r"yt_dlp-([^-/]+)\.dist-info/", name)
            if match:
                return match.group(1)
    return "0"


def _install_wheel(wheel_path, version=None):
    """Extracts a wheel into <root>/<version>/ atomically; returns that dir."""
    version = version or _wheel_version(wheel_path)
    root = _pkg_root()
    final = os.path.join(root, version)
    if os.path.isdir(os.path.join(final, "yt_dlp")):
        return final
    tmp = final + ".tmp"
    shutil.rmtree(tmp, ignore_errors=True)
    with zipfile.ZipFile(wheel_path) as zf:
        zf.extractall(tmp)
    if os.path.isdir(final):   # another thread/process won the race
        shutil.rmtree(tmp, ignore_errors=True)
    else:
        os.replace(tmp, final)
    return final


def _prune_old_versions():
    for _, path in _installed_versions()[KEEP_VERSIONS:]:
        shutil.rmtree(path, ignore_errors=True)


def get_ytdlp(log=print):
    """Imports and returns the newest available yt-dlp module.

    Priority: newest extracted copy in app data > bundled wheel (extracted on
    the spot) > the normally installed package (source runs).
    """
    global _ytdlp
    with _lock:
        if _ytdlp is not None:
            return _ytdlp

        installed = _installed_versions()
        if not installed:
            wheel = _bundled_wheel()
            if wheel:
                _install_wheel(wheel)
                installed = _installed_versions()

        if installed:
            version, path = installed[0]
            sys.path.insert(0, path)
            log(f"yt-dlp {version}")

        import yt_dlp   # from the inserted path, or site-packages as fallback
        _ytdlp = yt_dlp
        return _ytdlp


def current_version():
    """Version string of the copy get_ytdlp() would load right now."""
    installed = _installed_versions()
    if installed:
        return installed[0][0]
    wheel = _bundled_wheel()
    if wheel:
        return _wheel_version(wheel)
    try:
        from importlib import metadata
        return metadata.version("yt-dlp")
    except Exception:
        return "0"


def _check_and_update(log):
    try:
        request = Request(PYPI_JSON_URL, headers={"User-Agent": APP_NAME})
        with urlopen(request, timeout=15) as response:
            info = json.load(response)
        latest = info["info"]["version"]
        if _ver_key(latest) <= _ver_key(current_version()):
            return
        wheel_url = next(u["url"] for u in info["urls"]
                         if u["filename"].endswith(".whl"))
        log(f"Updating yt-dlp {current_version()} -> {latest} ...")
        tmp_wheel = os.path.join(_pkg_root(), f"download-{latest}.whl.part")
        with urlopen(wheel_url, timeout=60) as response, open(tmp_wheel, "wb") as out:
            shutil.copyfileobj(response, out)
        _install_wheel(tmp_wheel, version=latest)
        os.remove(tmp_wheel)
        _prune_old_versions()
        log(f"yt-dlp {latest} installed -- it will be used the next time the app starts.")
    except Exception as exc:
        # Never let an update problem break the app; the current copy still works.
        log(f"yt-dlp update check skipped: {exc}")


def start_background_update(log=print):
    """Checks PyPI for a newer yt-dlp without blocking the app."""
    threading.Thread(target=_check_and_update, args=(log,), daemon=True).start()
