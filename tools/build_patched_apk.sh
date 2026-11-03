#!/usr/bin/env bash
# Build a root-detection-patched Apple Music APK from an official `.apkm`
# bundle — or from an already-flat `.apk` (merge step is skipped then).
#
# Usage:  ./build_patched_apk.sh AppleMusic-<version>.apkm|.apk [output.apk]
#
# Pipeline:
#   1. (auto-download APKEditor + uber-apk-signer if absent)
#   2. merge the .apkm (base + config splits) into one universal APK     [APKEditor]
#      (skipped automatically when the input is already a flat APK)
#   3. binary-patch the dex constant string  /system/bin/su  -> /system/b1n/su
#   4. zipalign + sign with a generated debug key                        [uber-apk-signer]
#
# Requires: java (JDK 17+), python3, curl. Run ./doctor.sh first if unsure.
set -euo pipefail

TOOLS_DIR="${TOOLS_DIR:-$PWD/.tools}"
APKEDITOR_URL="https://github.com/REAndroid/APKEditor/releases/download/V1.4.9/APKEditor-1.4.9.jar"
UBER_SIGN_URL="https://github.com/patrickfav/uber-apk-signer/releases/download/v1.3.0/uber-apk-signer-1.3.0.jar"
OLD_STR="/system/bin/su"
NEW_STR="/system/b1n/su"

if [ $# -lt 1 ]; then
    echo "Usage: $0 <official.apkm|flat.apk> [output.apk]" >&2
    exit 1
fi
INPUT="$1"
BASE="$(basename "$INPUT")"; BASE="${BASE%.apkm}"; BASE="${BASE%.apk}"; BASE="${BASE%-unsigned}"
OUT="${2:-${BASE}-patched.apk}"

command -v java >/dev/null || { echo "ERROR: java not found (JDK 17+ required)" >&2; exit 1; }
command -v python3 >/dev/null || { echo "ERROR: python3 not found" >&2; exit 1; }
[ -f "$INPUT" ]               || { echo "ERROR: input $INPUT not found" >&2; exit 1; }

# A flat APK has AndroidManifest.xml at the zip root; an .apkm bundle has
# base.apk + split_config.*.apk entries instead.
if python3 - "$INPUT" <<'PY'
import sys, zipfile
with zipfile.ZipFile(sys.argv[1]) as z:
    names = set(z.namelist())
sys.exit(0 if "AndroidManifest.xml" in names else 1)
PY
then
    FLAT_APK=1
else
    FLAT_APK=0
fi

mkdir -p "$TOOLS_DIR" work
if [ "$FLAT_APK" -eq 0 ]; then
    for f in APKEditor.jar uber-apk-signer.jar; do
        if [ ! -f "$TOOLS_DIR/$f" ]; then
            url="$APKEDITOR_URL"; [ "$f" = "uber-apk-signer.jar" ] && url="$UBER_SIGN_URL"
            echo "[*] Downloading $f ..."
            curl -sS -L --retry 3 -o "$TOOLS_DIR/$f" "$url"
        fi
    done
fi
if [ ! -f "$TOOLS_DIR/uber-apk-signer.jar" ]; then
    curl -sS -L --retry 3 -o "$TOOLS_DIR/uber-apk-signer.jar" "$UBER_SIGN_URL"
fi

if [ "$FLAT_APK" -eq 1 ]; then
    echo "[*] Input is a flat APK - skipping merge"
    cp "$INPUT" "work/${BASE}-unsigned.apk"
else
    echo "[*] Merging $INPUT ..."
    java -jar "$TOOLS_DIR/APKEditor.jar" m -i "$INPUT" -o "work/${BASE}-unsigned.apk" >/dev/null
fi

echo "[*] Patching dex strings in work/${BASE}-unsigned.apk ..."
"$(dirname "$0")/patch_dex.py" "$OLD_STR" "$NEW_STR" "work/${BASE}-unsigned.apk" "work/${BASE}-patched.apk"
echo "    OK: exactly 1 occurrence patched"

echo "[*] Zipalign + sign ..."
java -jar "$TOOLS_DIR/uber-apk-signer.jar" --apks "work/${BASE}-patched.apk" \
     --allowResign --overwrite >/dev/null
mv "work/${BASE}-patched.apk" "$OUT"

echo "[OK]  ${OUT}  ($(du -h "$OUT" | cut -f1))"
echo "      Install:  adb uninstall com.apple.android.music && adb install ${OUT}"
