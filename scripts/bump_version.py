#!/usr/bin/env python3
"""
bump_version.py — update every version stamp in one shot.

Stamps updated (each must match exactly once, or the script aborts):
  web/VERSION      — bare semver
  web/index.html   — style.css?v= and app.js?v= cache-bust strings + footer fallback
  README.md        — "**Current version: vX.Y.Z**" badge
  CLAUDE.md        — "**vX.Y.Z** — see `web/VERSION` file." line

Deliberately NOT automated: the README changelog entry (needs human words)
and the git tag (`git tag vX.Y.Z && git push origin vX.Y.Z`).

Usage: python scripts/bump_version.py 1.8.0
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent


def sub_exactly_once(text, pattern, repl, where):
    new, count = re.subn(pattern, repl, text)
    if count != 1:
        sys.exit(f"ERROR: expected exactly 1 match for {pattern!r} in {where}, found {count}. "
                 f"Fix the file (or this script) before bumping.")
    return new


def main():
    if len(sys.argv) != 2 or not re.fullmatch(r"\d+\.\d+\.\d+", sys.argv[1]):
        sys.exit("Usage: python scripts/bump_version.py X.Y.Z")
    v = sys.argv[1]

    (ROOT / "web" / "VERSION").write_text(v)

    path = ROOT / "web" / "index.html"
    text = path.read_text()
    text = sub_exactly_once(text, r"style\.css\?v=\d+\.\d+\.\d+", f"style.css?v={v}", "index.html")
    text = sub_exactly_once(text, r"app\.js\?v=\d+\.\d+\.\d+", f"app.js?v={v}", "index.html")
    text = sub_exactly_once(text, r'(id="footer-version">)v\d+\.\d+\.\d+',
                            rf"\g<1>v{v}", "index.html")
    path.write_text(text)

    path = ROOT / "README.md"
    text = sub_exactly_once(path.read_text(), r"\*\*Current version: v\d+\.\d+\.\d+\*\*",
                            f"**Current version: v{v}**", "README.md")
    path.write_text(text)

    path = ROOT / "CLAUDE.md"
    text = sub_exactly_once(path.read_text(), r"\*\*v\d+\.\d+\.\d+\*\* — see `web/VERSION` file\.",
                            f"**v{v}** — see `web/VERSION` file.", "CLAUDE.md")
    path.write_text(text)

    print(f"All version stamps set to {v}.")
    print(f"Still manual: README changelog entry, commit, `git tag v{v} && git push origin v{v}`.")


if __name__ == "__main__":
    main()
