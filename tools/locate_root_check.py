#!/usr/bin/env python3
"""Locate the root-detection code inside an Apple Music APK (any version).

Usage:
    uv run --with androguard python locate_root_check.py <official.apk>

Scans every dex for su-related constant strings and, for each hit, prints the
class and method that reference it. This is the "recon" step you run first on a
newly released version to confirm the patch point has not moved.

Typical output for 5.x–7.x:

    [classes.dex] Lcom/apple/android/music/AppleMusicApplication; -> g:
        v1, "/system/bin/su"
    [classes2.dex] Ltd/h; -> h:
        v1, "/system/xbin/su"
"""
import sys
import zipfile

from androguard.core.dex import DEX

SU_PATHS = {"/system/bin/su", "/system/xbin/su", "/sbin/su", "/su/bin",
            "/system/app/Superuser.apk"}

def scan(apk_path):
    z = zipfile.ZipFile(apk_path)
    for dn in sorted(n for n in z.namelist() if n.endswith(".dex")):
        d = DEX(z.read(dn))
        strs = d.get_strings()
        watch = {s: [] for s in SU_PATHS if s in strs}
        # also catch log-ish strings near the feature
        for s in strs:
            if s.endswith(", isRooted=") or "is_rooted" == s:
                watch[s] = []
        if not watch:
            continue
        for c in d.get_classes():
            for m in c.get_methods():
                code = m.get_code()
                if code is None:
                    continue
                try:
                    for inst in m.get_instructions():
                        if inst.get_op_value() not in (0x1A, 0x1B):  # const-string[/jumbo]
                            continue
                        out = inst.get_output()
                        for s in watch:
                            if f'"{s[:28]}' in out:
                                watch[s].append((c.get_name(), m.get_name()))
                except Exception:
                    pass
        for s, refs in watch.items():
            print(f"[{dn}] string {s!r}")
            for cls, meth in refs:
                print(f"    referenced by  {cls} -> {meth}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    scan(sys.argv[1])
