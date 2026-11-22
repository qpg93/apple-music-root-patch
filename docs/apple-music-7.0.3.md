# Apple Music 7.0.3 arm64 preview

This build uses an APKPure XAPK for `com.apple.android.music` (versionCode
1626, minSdk 30, targetSdk 36). It includes the base APK, an `arm64-v8a` split,
and an `mdpi` split. The merged APK is **not universal**. APKMirror returned
HTTP 403 during verification, so this bundle is not in the APKMirror download
table or `fetch_official.py`.

## Download and verify the input

Download [build 1626 from APKPure](https://d.apkpure.net/b/XAPK/com.apple.android.music?versionCode=1626)
and save it as `AppleMusic-7.0.3.xapk`:

```bash
printf '%s\n' '61d92006523f85d0e98ea149862cb741675e334bba00a5e198032a9b18aa6aec  AppleMusic-7.0.3.xapk' | sha256sum -c -
```

`apksigner verify --verbose --print-certs` verified the base and both splits.
All three have the same signers: the Apple certificate for API 30–32 matches
[Apple Music's published fingerprint](https://music.apple.com/.well-known/assetlinks.json)
(`88ba590ec2e1ea33c4458daf59489faee2cef297a9b4071e18cf82ef531100aa`),
and the v3.1 signer for API 33+ is linked to it by the signing lineage.

## Build and verify

From the repository root:

```bash
./tools/build_patched_apk.sh AppleMusic-7.0.3.xapk AM-7.0.3-arm64-patched.apk
uv run --with androguard python tools/verify_patched_apk.py AM-7.0.3-arm64-patched.apk
apksigner verify --verbose --min-sdk-version 21 AM-7.0.3-arm64-patched.apk
```

The existing patch changes exactly one string in `classes2.dex`. The output
passes the static verifier and `apksigner` (v1, v2, and v3). The lower SDK
value in the verification command checks the older signature schemes; the APK
still requires Android 11+. The output uses the build tool's debug signer,
not Apple's. Installation, launch, sign-in, and playback still need to be
tested on an arm64 Android 11+ device.
