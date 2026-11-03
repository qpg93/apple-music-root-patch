# Deploying to an Android TV (Xiaomi/Mini LED example)

The patched APK is a normal Android package; installing it on a TV is only about
ADB or a USB drive. This guide uses the Xiaomi TV S-series (HyperOS) as the
example — other brands differ only in menu wording.

## Which version to pick

| TV base OS | Installable | Notes |
|---|---|---|
| Android 8.x / 9.x | none of the new builds | only modified old builds (≤4.8.1-class, minSdk 23) work |
| Android 10 | 5.2.1 | |
| Android 11+ | 5.2.1, 6.5.3, 7.0.0 | |

Check the base OS before choosing:

```bash
adb shell getprop ro.build.version.release   # e.g. "10"
adb shell getprop ro.build.version.sdk       # e.g. 29
```

## Step 1 — enable ADB on the TV

Firmware-dependent, but on HyperOS/MIUI-based Xiaomi TVs:

1. `Settings → About` — tap the **software version / OS version** line several
   times until "Developer options unlocked" appears.
2. `Settings → Developer options` (appears next to About) — enable
   **ADB debugging** and **Network ADB** (or "ADB over network").

## Step 2 — connect and install

From a PC on the same network:

```bash
adb connect <TV_IP>:5555          # port shown on the TV's ADB screen if not 5555
adb devices                       # should list the TV as "device"
```

If a `com.apple.android.music` package signed with a different key is already
installed, uninstall it first — otherwise install fails with a signature mismatch:

```bash
adb uninstall com.apple.android.music
adb install AppleMusic-5.2.1-patched.apk
```

Verify:

```bash
adb shell pm list packages | grep apple
adb logcat -d | grep -i -E "applemusic|android.music" | tail -20
```

## Step 3 — USB sideload (no PC)

1. Copy the APK to a FAT32/exFAT USB drive.
2. On the TV open the built-in **file manager**, select the APK. If the TV asks
   to allow installs from that source, accept (only for the file manager).
3. Signature note still applies: un-install the official app first.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `INSTALL_FAILED_OLDER_SDK` | the build's minSdk is newer than the TV's base OS (e.g. 6.5.3 on Android 10) | pick a lower version (see table) |
| `INSTALL_FAILED_UPDATE_INCOMPATIBLE` | an app signed with another key is present | `adb uninstall com.apple.android.music` first |
| `INSTALL_FAILED_NO_MATCHING_ABIS` | installing a base-only APK without native libs | use the merged output of `tools/build_patched_apk.sh` (all ABIs included) |
| `Connection refused` on `adb connect` | network ADB off, or a different port | re-enable in Developer options; try the port shown on the TV screen |
| `more than one device` | phone + TV both connected | `adb -s <TV_IP>:5555 <command>` |
| App opens then closes immediately | leftover official-app user data conflicts, or TV blocked version | uninstall + reboot + reinstall; then see the FAQ |
| Login works but playback fails server-side | DRM/device attestation issue, *not* fixed by the root-check patch | the patch does not touch DRM — playback failures are typically account/region issues |

## A note on the root check on TVs

On some Xiaomi TV firmwares the *official* app fails the same `su`-path check
as a rooted device would (false positive). That is the case this patch
originally targeted: the app is not "more rooted" after patching — the app
simply stops being told that `/system/bin/su` exists.
