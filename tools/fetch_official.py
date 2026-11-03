#!/usr/bin/env python3
"""Download the official Apple Music `.apkm` bundle from APKMirror.

Usage:
    fetch_official.py --version 5.2.1                 # known version (table below)
    fetch_official.py --url <variant-download-page>   # any release

Options:
    --output FILE      destination (default: AppleMusic-<version>.apkm)
    --sha256 HEX       verify the download against this digest (the known-version
                       table verifies automatically)

APKMirror anti-bot notes (learned the hard way, see docs/downloading-official.md):
  * session cookies must be kept across hops (307 "thank_you_invalid_referer" otherwise)
  * hop 2 requires the *exact variant page URL* as Referer, not the app's dir
  * keys are single-use; every fresh variant-page fetch yields a fresh key
"""
import argparse
import gzip
import hashlib
import http.cookiejar
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request

BASE = "https://www.apkmirror.com"
APKM_REF = BASE + "/apk/apple/apple-music/"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0 Safari/537.36")

# Version table: sha256 of the .apkm used for the reference builds, plus the
# universal/BUNDLE variant page that hosts it.
KNOWN = {
    "5.2.1": {
        "page": ("https://www.apkmirror.com/apk/apple/apple-music/"
                 "apple-music-5-2-1-release/apple-music-5-2-1-android-apk-download/"),
        "sha256": "1d74cea9d0d6a7c77bf4d004197be52e9e14110414255caa3825142fc19b7962",
    },
    "6.5.3": {
        "page": ("https://www.apkmirror.com/apk/apple/apple-music/"
                 "apple-music-6-5-3-release/apple-music-6-5-3-android-apk-download/"),
        "sha256": "a0494d1aac72f9d7901683b9da7df0afe46fae56ac5ad4070c7e265567eabd89",
    },
    "7.0.0": {
        "page": ("https://www.apkmirror.com/apk/apple/apple-music/"
                 "apple-music-7-0-0-release/apple-music-7-0-0-android-apk-download/"),
        "sha256": "08219d7f9ab143e4ca5858964c630e8b197881eff0e8dff0742cdc7510bf4b1c",
    },
}

_JAR = http.cookiejar.CookieJar()

def _opener():
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(_JAR))

def fetch_text(url, referer=APKM_REF, retries=3):
    """GET url with UA + cookies; returns text."""
    last = None
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": UA,
                "Referer": referer,
                "Accept": "text/html,*/*",
            })
            with _opener().open(req, timeout=45) as r:
                data = r.read()
                if r.headers.get("Content-Encoding") == "gzip":
                    data = gzip.decompress(data)
            return data.decode("utf-8", errors="replace")
        except (urllib.error.URLError, OSError) as e:
            last = e
            print(f"[!] attempt {attempt}/{retries} failed: {e}", file=sys.stderr)
    raise RuntimeError(f"could not fetch {url}: {last}")


def resolve_download_php(page_url):
    """variant page -> button key -> download.php link (fresh single-use key)."""
    page = fetch_text(page_url)
    m = re.search(r'href="([^"]*/download/\?key=[0-9a-f]+)"', page)
    if not m:
        raise RuntimeError("no download button found on the variant page (layout changed?)")
    btn = m.group(1)
    if btn.startswith("/"):
        btn = BASE + btn
    hop2 = fetch_text(btn, referer=page_url)          # exact page referer is required
    m = re.search(r'href="(/wp-content/themes/APKMirror/download\.php\?[^"]+)"', hop2)
    if not m:
        raise RuntimeError("no download.php link after hop 2 (cookies/referer rejected, "
                           "or APKMirror changed the flow)")
    return BASE + m.group(1)


def download(php_url, dest):
    """Download the .apkm; curl preferred (robust redirect + cookie handling)."""
    has_curl = subprocess.call(["which", "curl"], stdout=subprocess.DEVNULL) == 0
    if has_curl:
        # seed curl with the same cookies the python hops collected
        cookie_hdr = "; ".join(f"{c.name}={c.value}" for c in _JAR)
        cmd = ["curl", "-sS", "-L", "--retry", "3", "--connect-timeout", "15",
               "-A", UA, "-e", APKM_REF]
        if cookie_hdr:
            cmd += ["-H", f"Cookie: {cookie_hdr}"]
        cmd += ["-o", dest, php_url]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(f"curl failed: {proc.err.strip()}")
    else:
        req = urllib.request.Request(php_url, headers={"User-Agent": UA, "Referer": APKM_REF})
        with urllib.request.urlopen(req, timeout=60) as r, open(dest, "wb") as f:
            for chunk in iter(lambda: r.read(1 << 20), b""):
                f.write(chunk)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--version", help="known version key: " + ", ".join(KNOWN))
    src.add_argument("--url", help="URL of the variant download page (...-android-apk-download/)")
    ap.add_argument("--output", help="destination file")
    ap.add_argument("--sha256", help="expected sha256 (optional for --version)")
    args = ap.parse_args()

    if args.version:
        if args.version not in KNOWN:
            sys.exit(f"ERROR: unknown version {args.version}; known: {', '.join(KNOWN)}")
        page = KNOWN[args.version]["page"]
        expect = args.sha256 or KNOWN[args.version]["sha256"]
        out = args.output or f"AppleMusic-{args.version}.apkm"
    else:
        page = args.url
        expect = args.sha256
        out = args.output or "apple-music.apkm"

    print(f"[*] resolving {page}")
    php = resolve_download_php(page)
    print(f"[*] downloading via {php[:85]}")
    download(php, out)
    if not os.path.exists(out) or os.path.getsize(out) == 0:
        sys.exit(f"ERROR: {out} is empty/missing — download failed silently")

    size = os.path.getsize(out)
    digest = sha256_file(out)
    print(f"[*] {out}: {size} bytes, sha256 {digest}")
    if expect and digest != expect:
        os.remove(out)
        sys.exit(f"ERROR: sha256 mismatch (expected {expect}); file deleted — "
                 f"APKMirror may have served a rotated bundle")
    print("[OK] done")


if __name__ == "__main__":
    main()
