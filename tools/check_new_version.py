#!/usr/bin/env python3
"""Check APKMirror for a newer Apple Music release than the ones we know.

Exit codes:
    0   up to date
    10  a newer version exists (last stdout line: NEW_VERSION=<x.y.z>)
    3   could not fetch the release index (network / anti-bot); treat as
        "unknown" — do not open an issue

Used by .github/workflows/version-watch.yml (daily cron).
"""
import re
import sys
import urllib.request

INDEX = "https://www.apkmirror.com/apk/apple/apple-music/"
README = "README.md"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0 Safari/537.36")


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,*/*"})
    with urllib.request.urlopen(req, timeout=45) as r:
        return r.read().decode("utf-8", errors="replace")


def latest_release(html):
    """Highest non-beta x.y.z from release hrefs."""
    found = []
    for m in re.finditer(r'apple-music-(\d+)-(\d+)-(\d+)(?:-\d+)?-release/', html):
        m2 = re.search(r'apple-music-\d+-\d+-\d+(?:-\d+)?-release', m.group(0))
        if "beta" in m.group(0) or "-beta" in m.group(0):
            continue
        found.append(tuple(int(g) for g in m.groups()))
    return max(found) if found else None


def known_versions(readme_text):
    vers = set()
    for line in readme_text.splitlines():
        m = re.match(r'\|\s*(\d+)\.(\d+)\.(\d+)\s*\|', line)
        if m:
            vers.add(tuple(int(g) for g in m.groups()))
    return vers


def main():
    try:
        html = fetch(INDEX)
    except Exception as e:
        print(f"WARN could not fetch index: {type(e).__name__}: {e}", file=sys.stderr)
        print("WARN version state unknown (no issue will be opened)")
        return 3

    latest = latest_release(html)
    if not latest:
        print("WARN could not parse any release from the index (layout changed?)")
        return 3

    known = known_versions(open(README, encoding="utf-8").read())
    latest_s = ".".join(map(str, latest))
    print(f"latest on APKMirror : {latest_s}")
    print(f"known in README     : {', '.join('.'.join(map(str, k)) for k in sorted(known)) or '(none)'}")

    if not known:
        print("WARN no versions parsed from README — table format changed?")
        return 3
    if latest > max(known):
        print(f"NEW_VERSION={latest_s}")
        return 10
    print("up to date")
    return 0


if __name__ == "__main__":
    sys.exit(main())
