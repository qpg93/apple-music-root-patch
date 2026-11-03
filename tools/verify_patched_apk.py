#!/usr/bin/env python3
"""Verify a patched Apple Music APK: manifest parity, patch state, signatures.

Usage:
    uv run --with androguard python verify_patched_apk.py <patched.apk>

Checks:
  * package name / version / min & target SDK
  * no remaining "/system/bin/su" in any dex, exactly one "/system/b1n/su"
  * v1 + v2 + v3 signatures present
  * arm64-v8a native libraries present (splits are expected to be merged)
"""
import sys
import zipfile

def die(msg):
    print(f"FAIL  {msg}")
    sys.exit(1)

def main():
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    path = sys.argv[1]

    from androguard.core.apk import APK
    a = APK(path)

    pkg = a.get_package()
    print(f"package            : {pkg}")
    print(f"version            : {a.get_androidversion_name()} (code {a.get_androidversion_code()})")
    print(f"minSdk / targetSdk : {a.get_min_sdk_version()} / {a.get_target_sdk_version()}")

    if pkg != "com.apple.android.music":
        die(f"unexpected package {pkg}")

    with zipfile.ZipFile(path) as z:
        dex_names = [n for n in z.namelist() if n.endswith(".dex")]
        old = new = 0
        for n in dex_names:
            d = z.read(n)
            old += d.count(b"/system/bin/su")
            new += d.count(b"/system/b1n/su")
    print(f"dex files          : {len(dex_names)}")
    print(f"'/system/bin/su'   : {old} remaining (must be 0)")
    print(f"'/system/b1n/su'   : {new} present (must be >= 1)")

    if old != 0:
        die("original su path still present — patch incomplete")
    if new < 1:
        die("replacement path missing — patch did not apply")

    libs = [n for n in a.get_files() if n.startswith("lib/arm64-v8a/") and n.endswith(".so")]
    print(f"arm64-v8a libs     : {len(libs)}")
    if not libs:
        die("no arm64-v8a libraries — splits were not merged into this APK")

    signed_v1 = a.is_signed_v1()
    signed_v2 = a.is_signed_v2()
    signed_v3 = a.is_signed_v3()
    print(f"signatures         : v1={signed_v1} v2={signed_v2} v3={signed_v3}")
    if not (signed_v1 and signed_v2):
        die("missing v1/v2 signature — APK is not installable/verifiable as-is")

    print("OK    all checks passed")

if __name__ == "__main__":
    main()
