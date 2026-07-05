import re
from pathlib import Path

ROOT = Path(__file__).parent.parent


def read(rel):
    return (ROOT / rel).read_text()


def test_all_version_stamps_match():
    v = read("web/VERSION").strip()
    assert re.fullmatch(r"\d+\.\d+\.\d+", v), f"web/VERSION is not bare semver: {v!r}"

    html = read("web/index.html")
    assert f"style.css?v={v}" in html, "style.css cache-bust query string is stale"
    assert f"app.js?v={v}" in html, "app.js cache-bust query string is stale"
    assert f'id="footer-version">v{v}<' in html, "footer fallback version is stale"

    assert f"**Current version: v{v}**" in read("README.md"), "README badge is stale"
    assert f"**v{v}**" in read("CLAUDE.md"), "CLAUDE.md version line is stale"
