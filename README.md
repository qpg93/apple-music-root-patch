# Apple Music Root Patch

**English** | [日本語](README.ja.md) | [Français](README.fr.md) | [简体中文](README.zh-CN.md)

Engineering notes and build tooling for disabling the **root detection** in
Apple Music for Android — **no APK binaries are hosted here**. Everything in
this repository is a script, a patch technique, or documentation; you download
the official app yourself and apply the patch locally.

This project was originally inspired by
[arabaizzet's repo](https://github.com/arabaizzet/Apple-Music-for-Rooted-Devices)
(which distributed a modified Apple Music 4.8.1). That repo is no longer updated,
so this is now an independent project built around the same technique: documented
and automated, confirmed to work unchanged against Apple Music **5.2.1, 6.5.3 and 7.0.0**.

## Why

Since v4.7 (March 2024), Apple Music for Android refuses to run when it thinks
the device is rooted. This trips up on:

- genuinely rooted devices where `su` lives in one of the checked paths, and
- stock devices that give a false positive — e.g. some **Xiaomi TVs**, where the
  official app exits at startup.

## How the root detection works

Reverse-engineering details (smali dumps, class names per version) are in
[`docs/root-detection-analysis.md`](docs/root-detection-analysis.md). In short,
the app's `Application` class runs a check equivalent to:

```java
boolean isDeviceRooted() {
    return helperCheck()                     // ("test-keys", /system/app/Superuser.apk, /system/xbin/su)
        || new File("/system/bin/su").exists();
}
```

The helper chain passes on stock systems; the discriminating check on blocked
devices is the `new File("/system/bin/su").exists()` test.

### The patch

Replace the 14-byte string `/system/bin/su` in the dex constant pool with an
non-existent path of the **same length**:

```
/system/bin/su   →   /system/b1n/su        ("bin" → "b1n")
```

Because the replacement is the same length and the dex is only binary-patched
(no smali recompilation), the resulting APK is byte-for-byte identical to the
official one except those 14 bytes — plus zipalign and re-signing (the split
APKs must also be re-signed, so a full re-sign is unavoidable anyway).

The original 4.8.1 mod used the same idea with the string
`/system/bin/applemusicwizzeyeren` (which required smali recompilation, since
that string is longer).

**What is not changed:** no DRM modification, no subscription bypass, no
anything-else. You still need a real Apple ID with an active Apple Music
subscription to use the app.

## Build your own patched APK

### Prerequisites

- JDK 17+ (only `java` is needed; no compilation of Java sources)
- [APKEditor 1.4.x](https://github.com/REAndroid/APKEditor/releases) — merges the
  base APK and config splits of the official `.apkm` bundle into one universal APK
- [uber-apk-signer 1.3.x](https://github.com/patrickfav/uber-apk-signer/releases) —
  zipalign + v1/v2/v3 signing with a generated debug key
- (optional, for verification) Python 3 with `uv` or `pip install androguard`

The build script downloads both JARs automatically if they are missing.
Run `./tools/doctor.sh` first if unsure whether your environment is ready.

### 1. Get the official bundle

```bash
python3 tools/fetch_official.py --version 5.2.1
```

Downloads the official `.apkm` from APKMirror automatically (cookie- and
referer-aware download chain) and verifies the SHA-256 from the table below
before saving. Full chain description and a manual fallback:
[`docs/downloading-official.md`](docs/downloading-official.md).

| Version | versionCode | Requires Android | APKMirror release page | SHA-256 of `.apkm` |
|---|---|---|---|---|
| 5.2.1 | 1545 | 10.0 (API 29) | [release](https://www.apkmirror.com/apk/apple/apple-music/apple-music-5-2-1-release/) | `1d74cea9d0d6a7c77bf4d004197be52e9e14110414255caa3825142fc19b7962` |
| 6.5.3 | 1599 | 11.0 (API 30) | [release](https://www.apkmirror.com/apk/apple/apple-music/apple-music-6-5-3-release/) | `a0494d1aac72f9d7901683b9da7df0afe46fae56ac5ad4070c7e265567eabd89` |
| 7.0.0 | 1614 | 11.0 (API 30) | [release](https://www.apkmirror.com/apk/apple/apple-music/apple-music-7-0-0-release/) | `08219d7f9ab143e4ca5858964c630e8b197881eff0e8dff0742cdc7510bf4b1c` |

*(On the download page pick the **universal / BUNDLE** variant. Verify the
SHA-256 after downloading.)*

### 2. Run the build

```bash
./tools/build_patched_apk.sh AppleMusic-5.2.1.apkm
# → AppleMusic-5.2.1-patched.apk
```

The script: merges the bundle → binary-patches every `/system/bin/su` in the
dexes → reports patch count → zipaligns and signs the result. It fails loudly
if the patch count is not exactly 1.

### 3. Verify (optional but recommended)

```bash
uv run --with androguard python tools/verify_patched_apk.py AppleMusic-5.2.1-patched.apk
```

Checks package/versions, that the old string is gone and the replacement
present, and that the APK is v1+v2+v3 signed.

### 4. Install

If a copy of the app already exists on the device with a different signature,
uninstall it first (passwords may be asked for at re-login):

```bash
adb uninstall com.apple.android.music
adb install AppleMusic-5.2.1-patched.apk
```

Or copy the APK to the device and install it from a file manager (enable
"Install unknown apps" for the file manager first).

## Repository layout

```
tools/fetch_official.py          download the official .apkm from APKMirror + sha256 check
tools/doctor.sh                  pre-flight environment check (java/python/curl/disk)
tools/build_patched_apk.sh       merge → binary-patch → sign pipeline (.apkm or flat .apk)
tools/patch_dex.py               the string patch itself (used by the script above)
tools/test_patch_dex.py          self-tests for the patch logic (no Apple code needed)
tools/verify_patched_apk.py      post-build verification (androguard)
tools/locate_root_check.py       dex scanner that finds the su-path checks
tools/check_new_version.py       compares APKMirror's latest release with the table above
docs/root-detection-analysis.md  full RE findings, per-version class/method map
docs/building-android-tv.md      TV sideload guide + troubleshooting (Xiaomi example)
docs/downloading-official.md     APKMirror download chain, anti-bot quirks
DISCLAIMER.md                    the long-form legal/disclaimer text
```

Continuous integration runs the patch-logic self-tests on every push — see
`.github/workflows/ci.yml`. A daily scheduled workflow
(`.github/workflows/version-watch.yml`) checks APKMirror for a newer Apple Music
release and opens an issue with the follow-up checklist when one appears.

Scripts and documentation are MIT-licensed (`LICENSE`); Apple Music's binaries
are not included in, nor distributed by, this repository.

## Legal

**Read [`DISCLAIMER.md`](DISCLAIMER.md) in full.** Summary: this repository
contains scripts and documentation only — no Apple binaries. It is unaudited,
unaffiliated research into a 14-byte diagnostic string patch; it does not touch
DRM, subscription checks, or any content-protection mechanism. Building and
installing a patched APK is your decision and your responsibility under your
local law, Apple's terms, and your device's warranty. No warranty of any kind.
