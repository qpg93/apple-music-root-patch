# Apple-Music-for-Rooted-Devices

Apple Music for Android (since 4.7) refuses to run if it detects a rooted device.
This repository provides patched builds that disable the root detection, so the app
can run on rooted TVs, boxes, or other devices that would otherwise be blocked.

> This started as a fork of [arabaizzet's repo](https://github.com/arabaizzet/Apple-Music-for-Rooted-Devices),
> which published v4.8.1 (Oct 2024). This fork extends the same technique to the
> newer official versions **5.2.1, 6.5.3 and 7.0.0**.

## What devices is this for?

Originally for rooted devices, but it is also useful on **stock devices where the
`/system/bin/su` file path check gives a false positive** — for example Xiaomi TVs,
where the official app exits at startup.

## How the patch works

Original technique (applied by arabaizzet/wizzeteren to 4.8.1):

- The app's init code runs a check equivalent to
  `new File("/system/bin/su").exists()`.
- The string `/system/bin/su` is replaced by a path that does not exist
  (`/system/bin/applemusicwizzeyeren`), so `exists()` always returns `false`
  and the root detection never triggers.

Builds in this fork use an equal-length in-place binary patch on the dex string:

```
/system/bin/su   ->   /system/b1n/su     ("bin" -> "b1n", path does not exist)
```

This means the dex is **byte-for-byte identical except for 14 bytes** — no smali
recompilation, no reordering, no other modifications. The base APK and its
config splits are merged into a single universal APK (with the APKEditor merge
of the official APKMirror `.apkm` bundle), then zipaligned and re-signed.

## Downloads

Go to the [Releases](../../releases) tab. Each release contains one universal APK
(all architectures included, splits merged).

| Version | versionCode | Requires Android | Target SDK | SHA-256 |
|---|---|---|---|---|
| 5.2.1 | 1545 | 10.0 (API 29) | 35 | `2dfbb54efc475748f3b1cee9ff0a54bd19cda90285768d0cece0292bb6cb5ec2` |
| 6.5.3 | 1599 | 11.0 (API 30) | 35 | `5706d91f10de78778f20b88295dd26c740b57f1c04486ff370f85d1dacf05304` |
| 7.0.0 | 1614 | 11.0 (API 30) | 36 | `cc35aef7bff65e0faf0c3f4636b27729fb6448935526aff951ec346d3112c6c9` |

Source bases: official no-DRM-removal bundles from APKMirror
(version 5.2.1, 6.5.3, 7.0.0), merged with
[APKEditor](https://github.com/REAndroid/APKEditor) and signed with
[uber-apk-signer](https://github.com/patrickfav/uber-apk-signer).

## What is NOT changed

- No DRM protection modification.
- No ad removal, no subscription bypass.
- Only the root check string is touched. Everything else is identical to the
  official app: you need a real Apple ID with an active Apple Music
  subscription to use it.

## Installation

If you have the app already installed from a different package, uninstall it first
(signatures differ, so installing over it will fail with a signature mismatch):

```bash
adb uninstall com.apple.android.music
adb install AppleMusic-<version>-patched.apk
```

Or copy the APK to the device and install it from a file manager (enable
"Install unknown apps" for the file manager). You need Android 10+ for 5.2.1
and Android 11+ for 6.5.3/7.0.0.

## Verification of the build

For each build, the following was verified with
[androguard](https://github.com/androguard/androguard):

- Package/permissions identical to the official version.
- Exactly **1 occurrence** of the `/system/bin/su` string was replaced, 0 remaining.
- No other dex changes.
- arm64-v8a, armeabi-v7a, x86, x86_64 native libraries all present.
- ZIP-aligned and v1+v2+v3 signed.
