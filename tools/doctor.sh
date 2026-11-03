#!/usr/bin/env bash
# Pre-flight environment check for the build toolchain.
#
# Usage: ./tools/doctor.sh
# Exit:  0 = ready to build, 1 = a hard requirement is missing.
set -uo pipefail

FAIL=0
ok()   { printf '  [ok]    %s\n' "$*"; }
warn() { printf '  [warn]  %s\n' "$*"; }
bad()  { printf '  [FAIL]  %s\n' "$*"; FAIL=1; }

echo "== Java =="
if command -v java >/dev/null 2>&1; then
    JV="$(java -version 2>&1 | head -1)"
    MAJOR="$(java -version 2>&1 | head -1 | sed -n 's/.*version "\([0-9][0-9]*\)[."].*/\1/p')"
    if [ -z "${MAJOR:-}" ]; then
        bad "could not parse java version: $JV"
    elif [ "$MAJOR" -lt 17 ]; then
        bad "Java $MAJOR found, need 17+ ($JV)"
        echo "        no-root option: download a portable JRE from https://api.adoptium.net (linux/x64/jre)"
    else
        ok "java $MAJOR ($JV)"
    fi
else
    bad "java not found (JDK/JRE 17+ required for APKEditor and uber-apk-signer)"
    echo "        portable JRE: https://api.adoptium.net/v3/binary/latest/17/ga/linux/x64/jre/hotspot/normal/eclipse"
fi

echo "== Other tools =="
for t in python3 curl unzip; do
    if command -v "$t" >/dev/null 2>&1; then
        case "$t" in
            unzip) V="$(unzip -v 2>/dev/null | head -1)" ;;
            *)     V="$("$t" --version 2>&1 | head -1)" ;;
        esac
        ok "$t ($V)"
    else
        bad "$t not found"
    fi
done

echo "== Sign/build JARs =="
TOOLS_DIR="${TOOLS_DIR:-$PWD/.tools}"
for f in APKEditor.jar uber-apk-signer.jar; do
    if [ -f "$TOOLS_DIR/$f" ]; then ok "$TOOLS_DIR/$f"; else warn "$TOOLS_DIR/$f missing — build_patched_apk.sh will download it"; fi
done

echo "== Optional: androguard (verification only) =="
if python3 -c "import androguard" >/dev/null 2>&1; then
    ok "androguard importable"
elif command -v uv >/dev/null 2>&1; then
    warn "androguard not installed; verify step works via: uv run --with androguard python tools/verify_patched_apk.py <apk>"
else
    warn "androguard not installed and 'uv' not available; install with: pip install androguard"
fi

echo "== Disk space =="
AVAIL_MB="$(df -Pm . | awk 'NR==2 {print $4}')"
if [ "${AVAIL_MB:-0}" -ge 2000 ]; then
    ok "${AVAIL_MB} MB free (merge+output needs ~1.5 GB per build)"
else
    warn "only ${AVAIL_MB} MB free — a build needs ~1.5 GB"
fi

echo
if [ "$FAIL" -eq 0 ]; then
    echo "READY: requirements satisfied."
else
    echo "NOT READY: fix the [FAIL] items above."
fi
exit "$FAIL"
