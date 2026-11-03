#!/usr/bin/env python3
"""Self-tests for tools/patch_dex.py — synthetic fixtures, no Apple code needed.

patch_dex.py operates on a *flat* APK (the output of the merge step), so the
fixtures are flat single-file zips whose classes.dex embeds the test bytes.

Run:  python3 tools/test_patch_dex.py
Exit: 0 = all tests passed.
"""
import os
import subprocess
import sys
import tempfile
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
PATCH = os.path.join(HERE, "patch_dex.py")
OLD = "/system/bin/su"
NEW = "/system/b1n/su"

FAILURES = []
OUTDIR = tempfile.mkdtemp()          # where outputs are written

def run(args):
    return subprocess.run([sys.executable, PATCH] + args, capture_output=True, text=True)

def make_fixture(tmp, bites, stored_entry=False):
    """Build a minimal APK-like zip whose classes.dex contains `bites` bytes."""
    dex = b"dex\n035\x00" + b"\x00" * 8 + bites          # plausible dex-ish header
    path = os.path.join(tmp, "fixture.apk")
    with zipfile.ZipFile(path, "w") as apk:
        apk.writestr("classes.dex", dex, zipfile.ZIP_DEFLATED)
        apk.writestr("resources.arsc", b"S" * 64,
                     zipfile.ZIP_STORED if stored_entry else zipfile.ZIP_DEFLATED)
    return path

def check(name, cond, extra=""):
    if cond:
        print(f"  ok   {name}")
    else:
        print(f"  FAIL {name} {extra}")
        FAILURES.append(name)

print("test: happy path (1 occurrence)")
src = make_fixture(tempfile.mkdtemp(), b"xx" + OLD.encode() + b"yy")
dst = os.path.join(OUTDIR, "out1.apk")
r = run([OLD, NEW, src, dst])
check("exit 0", r.returncode == 0, r.stderr)
if r.returncode == 0:
    with zipfile.ZipFile(dst) as z:
        dex = z.read("classes.dex")
        check("old gone", OLD.encode() not in dex)
        check("new present once", dex.count(NEW.encode()) == 1)
        check("header intact", dex[:4] == b"dex\n")
        check("non-dex untouched", z.read("resources.arsc") == b"S" * 64)

print("test: STORED entry is preserved as STORED")
src = make_fixture(tempfile.mkdtemp(), OLD.encode(), stored_entry=True)
dst = os.path.join(OUTDIR, "out2.apk")
r = run([OLD, NEW, src, dst])
check("exit 0", r.returncode == 0, r.stderr)
if r.returncode == 0:
    with zipfile.ZipFile(dst) as z:
        check("resources.arsc still uncompressed",
              z.getinfo("resources.arsc").compress_type == zipfile.ZIP_STORED)
        check("classes.dex compressed", z.getinfo("classes.dex").compress_type != zipfile.ZIP_STORED)

print("test: zero occurrences -> error")
src = make_fixture(tempfile.mkdtemp(), b"nothing here")
r = run([OLD, NEW, src, os.path.join(OUTDIR, "out3.apk")])
check("exit 1", r.returncode == 1)
check("error message mentions count", "found 0" in r.stderr, r.stderr.strip())

print("test: two occurrences -> error (refuses mass-swap)")
src = make_fixture(tempfile.mkdtemp(), OLD.encode() + b"|" + OLD.encode())
r = run([OLD, NEW, src, os.path.join(OUTDIR, "out4.apk")])
check("exit 1", r.returncode == 1)
check("error message mentions count", "found 2" in r.stderr, r.stderr.strip())

print("test: unequal-length replacement -> error")
src = make_fixture(tempfile.mkdtemp(), OLD.encode())
r = run([OLD, "/bin/su", src, os.path.join(OUTDIR, "out4b.apk")])
check("exit 1", r.returncode == 1)
check("error mentions equal length", "equal" in r.stderr, r.stderr.strip())

print("test: re-run over same output path is allowed")
src = make_fixture(tempfile.mkdtemp(), OLD.encode())
dst = os.path.join(OUTDIR, "out5.apk")
r1 = run([OLD, NEW, src, dst])
r2 = run([OLD, NEW, src, dst])
check("both runs exit 0 (overwrite ok)",
      r1.returncode == 0 and r2.returncode == 0, (r1.stderr + r2.stderr).strip())

print()
if FAILURES:
    print(f"FAILED: {FAILURES}")
    sys.exit(1)
print("ALL TESTS PASSED")
