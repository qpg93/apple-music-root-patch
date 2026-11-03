#!/usr/bin/env python3
"""Equal-length binary patch of a su-path string inside an APK's dex files.

Usage:
    patch_dex.py <old> <new> <in.apk> <out.apk>

Behaviour:
  * old/new must have the same UTF-8 byte length (dex constant-pool-safe)
  * exactly ONE occurrence must be present across all dex entries; anything
    else is an error (silent mass-swap is never attempted)
  * entries that were ZIP-STORED stay ZIP-STORED; the rest are re-deflated
  * non-dex entries are copied byte-for-byte

Exit codes: 0 = patched, 2 = usage, 1 = invariant violated.
"""
import sys
import zipfile


def patch_apk(src, dst, old, new):
    if len(old.encode()) != len(new.encode()):
        raise ValueError(f"old ({old!r}) and new ({new!r}) must be equal UTF-8 byte length")
    old_b, new_b = old.encode(), new.encode()

    zin = zipfile.ZipFile(src)
    patched = {}
    for name in zin.namelist():
        data = zin.read(name)
        if name.endswith(".dex"):
            n = data.count(old_b)
            if n:
                patched[name] = n
                data = data.replace(old_b, new_b)
    total = sum(patched.values())
    if total != 1:
        raise ValueError(
            f"invariant violated: expected exactly 1 '{old}' occurrence in dexes, found {total}: {patched}"
        )

    with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zout:
        for name in zin.namelist():
            info = zin.getinfo(name)
            data = zin.read(name)
            if name.endswith(".dex"):
                data = data.replace(old_b, new_b)
            keep = zipfile.ZIP_STORED if info.compress_type == zipfile.ZIP_STORED else zipfile.ZIP_DEFLATED
            zout.writestr(info, data, keep)
    zin.close()
    return patched


def main():
    if len(sys.argv) != 5:
        print(__doc__)
        return 2
    old, new, src, dst = sys.argv[1:5]
    try:
        patched = patch_apk(src, dst, old, new)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    print("patched entries: " + ", ".join(f"{k} ({v}x)" for k, v in patched.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
