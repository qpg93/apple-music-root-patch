#!/usr/bin/env bash
# Build a root-detection-patched Apple Music APK from an official `.apkm` bundle.
#
# Usage:  ./build_patched_apk.sh AppleMusic-<version>.apkm [output.apk]
#
# Pipeline:
#   1. (auto-download APKEditor + uber-apk-signer if absent)
#   2. merge the .apkm (base + config splits) into one universal APK     [APKEditor]
#   3. binary-patch the dex constant string  /system/bin/su  -> /system/b1n/su
#   4. zipalign + sign with a generated debug key                        [uber-apk-signer]
#
# Requires: java (JDK 17+), python3, curl.
set -euo pipefail

TOOLS_DIR="${TOOLS_DIR:-$PWD/.tools}"
APKEDITOR_URL="https://github.com/REAndroid/APKEditor/releases/download/V1.4.9/APKEditor-1.4.9.jar"
UBER_SIGN_URL="https://github.com/patrickfav/uber-apk-signer/releases/download/v1.3.0/uber-apk-signer-1.3.0.jar"
OLD_STR="/system/bin/su"
NEW_STR="/system/b1n/su"

if [ $# -lt 1 ]; then
    echo "Usage: $0 <official.apkm> [output.apk]" >&2
    exit 1
fi
INPUT="$1"
BASE="$(basename "$INPUT")"; BASE="${BASE%.apkm}"
OUT="${2:-${BASE}-patched.apk}"

command -v java >/dev/null || { echo "ERROR: java not found (JDK 17+ required)" >&2; exit 1; }
command -v python3 >/dev/null || { echo "ERROR: python3 not found" >&2; exit 1; }
[ -f "$INPUT" ]               || { echo "ERROR: input $INPUT not found" >&2; exit 1; }

mkdir -p "$TOOLS_DIR" work
for f in APKEditor.jar uber-apk-signer.jar; do
    if [ ! -f "$TOOLS_DIR/$f" ]; then
        url="$APKEDITOR_URL"; [ "$f" = "uber-apk-signer.jar" ] && url="$UBER_SIGN_URL"
        echo "[*] Downloading $f ..."
        curl -sS -L --retry 3 -o "$TOOLS_DIR/$f" "$url"
    fi
done

echo "[*] Merging $INPUT ..."
java -jar "$TOOLS_DIR/APKEditor.jar" m -i "$INPUT" -o "work/${BASE}-unsigned.apk" >/dev/null

echo "[*] Patching dex strings in work/${BASE}-unsigned.apk ..."
"$(dirname "$0")/patch_dex.py" "$OLD_STR" "$NEW_STR" "work/${BASE}-unsigned.apk" "work/${BASE}-patched.apk"
echo "    OK: exactly 1 occurrence patched"

echo "[*] Zipalign + sign ..."
java -jar "$TOOLS_DIR/uber-apk-signer.jar" --apks "work/${BASE}-patched.apk" \
     --allowResign --overwrite >/dev/null
mv "work/${BASE}-patched.apk" "$OUT"

echo "[OK]  ${OUT}  ($(du -h "$OUT" | cut -f1))"
echo "      Install:  adb uninstall com.apple.android.music && adb install ${OUT}"
