# Downloading the official `.apkm` from APKMirror

Apple Music's official bundles are distributed by Apple on the Play Store in
(split) format; APKMirror republishes them as `.apkm` archives
(base APK + config splits in one zip). To build a patched APK you start from
that bundle — this document records the exact, reproducible download chain and
its quirks, so the step is scriptable.

## Option A — scripted (preferred)

`tools/fetch_official.py` implements the whole chain and verifies the result
against a pinned SHA-256:

```bash
python3 tools/fetch_official.py --version 5.2.1
# → AppleMusic-5.2.1.apkm  (sha256 checked automatically)
```

## Option B — manual

On the APKMirror release page, pick the **BUNDLE / universal** variant
(e.g. `apple-music-5-2-1-android-apk-download/`). The embedded chain is:

```
1. variant page
     .../apple-music-5-2-1-android-apk-download/
        └─ href="/.../android-apk-download/download/?key=<hex>"

2. GET that URL with the EXACT variant page URL as Referer
     → the page contains href="/wp-content/themes/APKMirror/download.php?id=<pid>&key=<hex-2>"

3. GET the download.php URL (the <hex-2> key is fresh and single-use)
     → HTTP 302 to a signed Cloudflare R2 URL (X-Amz-Signature, 1h expiry)

4. download the R2 URL → *.apkm  (≈150–200 MB, sha256 above)
```

Requirements discovered in practice:

- **Cookies**: hop 2 must reuse session cookies from hop 1, otherwise the site
  answers `307 → ?redirected=thank_you_invalid_referer` and re-serves the
  variant page (the key is consumed; refetch to get a fresh one).
- **Referer**: hop 2 requires the *exact* variant page URL — not the app's
  generic `/apk/apple/apple-music/` path.
- A fresh Chrome-like desktop User-Agent is expected by the CDN.
- One failed attempt burns a key; rerun the whole chain rather than reusing it.

## Verifying what you got

Regardless of how you download, check the SHA-256 against the table in the
README (per-version `.apkm` digests). A mismatch means APKMirror served a different
upload (e.g. a re-push) — stop and re-check the release page before patching.

## When APKMirror blocks you entirely

Symptoms: JS challenge pages, HTTP 403 on all hops. Then there is no scripted
failing gracefully — use a real browser to download the bundle manually and
still verify the SHA-256.

## After the download

```bash
./tools/build_patched_apk.sh AppleMusic-5.2.1.apkm
```
