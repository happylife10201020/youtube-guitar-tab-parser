"""Fails if Korean text appears in anything that ships to users.

This app, its docs, and its release notes are English-only. A Korean string
that slips into a GUI message, the README, or a commit subject reaches real
users -- commit subjects included, because the release workflow builds release
notes from them. Reviewing for that by eye does not scale, so this check
blocks it mechanically.

Usage:
    python tools/check_english.py                 # scan git-tracked files
    python tools/check_english.py --commit-msg F  # scan a commit message file

Escape hatch: put "allow-hangul" on the same line to permit one that is
genuinely needed (a test fixture, say).

Exit code 0 when clean, 1 when Korean is found.
"""

import argparse
import re
import subprocess
import sys

# Hangul syllables, conjoining jamo, and compatibility jamo. Written as escapes
# so this file stays ASCII and never flags itself.
HANGUL = re.compile("[\uac00-\ud7a3\u1100-\u11ff\u3130-\u318f]")

ALLOW_MARKER = "allow-hangul"

# Only text we author. Binaries and vendored trees are pointless to scan.
SCANNED_SUFFIXES = (".py", ".md", ".txt", ".bat", ".sh", ".yml", ".yaml",
                    ".cfg", ".ini", ".toml", ".json")

SKIPPED_PREFIXES = (".venv/", "dist/", "build/", "build_assets/", "assets/")


def tracked_files():
    """Text files git knows about, minus vendored and generated trees."""
    out = subprocess.run(["git", "ls-files", "-z"], capture_output=True,
                         text=True, check=True).stdout
    for path in out.split("\0"):
        if not path or not path.endswith(SCANNED_SUFFIXES):
            continue
        if path.startswith(SKIPPED_PREFIXES):
            continue
        yield path


def offending_lines(text):
    """[(line number, line)] for lines with Korean and no escape marker."""
    hits = []
    for number, line in enumerate(text.splitlines(), start=1):
        if HANGUL.search(line) and ALLOW_MARKER not in line:
            hits.append((number, line.strip()))
    return hits


def check_files():
    failures = []
    for path in tracked_files():
        try:
            with open(path, encoding="utf-8", errors="replace") as handle:
                text = handle.read()
        except OSError as exc:
            print(f"warning: could not read {path}: {exc}", file=sys.stderr)
            continue
        for number, line in offending_lines(text):
            failures.append(f"{path}:{number}: {line}")
    return failures


def check_commit_msg(path):
    with open(path, encoding="utf-8", errors="replace") as handle:
        text = handle.read()
    # Git's own comment lines are stripped before the message is stored, so a
    # template written in Korean must not fail the commit.
    body = "\n".join(l for l in text.splitlines() if not l.startswith("#"))
    return [f"commit message line {n}: {line}"
            for n, line in offending_lines(body)]


def main():
    # The report quotes the offending line, which is Korean by definition. A
    # console that cannot encode it (a plain Windows code page, say) would
    # otherwise crash the check instead of reporting it.
    try:
        sys.stderr.reconfigure(errors="backslashreplace")
    except (AttributeError, ValueError):
        pass

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commit-msg", metavar="FILE",
                        help="check this commit message file instead of the tree")
    args = parser.parse_args()

    if args.commit_msg:
        failures = check_commit_msg(args.commit_msg)
        subject = "This commit message contains Korean."
    else:
        failures = check_files()
        subject = "These files contain Korean."

    if not failures:
        return 0

    print(f"English-only check failed. {subject}", file=sys.stderr)
    print("Anything users can see -- GUI text, README, commit subjects that",
          file=sys.stderr)
    print("become release notes -- must be English.\n", file=sys.stderr)
    for failure in failures:
        print(f"  {failure}", file=sys.stderr)
    print(f"\nIf a line genuinely needs Korean, add '{ALLOW_MARKER}' to it.",
          file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
