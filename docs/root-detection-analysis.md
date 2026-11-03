# Root detection analysis (Apple Music for Android)

Findings from static analysis of the official APKs (androguard, dex-level only —
no native lib reversal was needed). This is the reference for why the one-string
patch in `tools/build_patched_apk.sh` is sufficient.

## Summary across versions

| Version | versionCode | minSdk / target | Detection intro method | Dex | Helper class |
|---|---|---|---|---|---|
| 4.8.1 | 1397 | 23 / 33 | `AppleMusicApplication->f()` | classes.dex | `Lsl/e;` |
| 5.2.1 | 1545 | 29 / 35 | `AppleMusicApplication->g()` | classes.dex | `Ltd/h;` |
| 6.5.3 | 1599 | 30 / 35 | `AppleMusicApplication->g()` | classes2.dex | `LXe/h;` |
| 7.0.0 | 1614 | 30 / 36 | `AppleMusicApplication->i()` | classes2.dex | `Lwg/h;` |

Only the obfuscated names drift between versions; the logic is identical.

## The check chain

All versions execute the equivalent of:

```java
// AppleMusicApplication (Application subclass)
static boolean isDeviceRooted() {
    return helperCheck()
        || new File("/system/bin/su").exists();
}

// helper (Ltd/h; in 5.2.1)
static boolean helperCheck() {
    return otherCheck()
        || Build.TAGS.contains("test-keys")
        || new File("/system/app/Superuser.apk").exists()
        || new File("/system/xbin/su").exists();
}
```

Effective smali of the 5.2.1 entry point (`classes.dex`, method `g`), 14 instructions:

```smali
invoke-static {}, Ltd/h;->h()Z            # helper chain
move-result v0
if-eqz v0, +e                             # helper said no → try /system/bin/su
const 1; return v0                        # helper said yes → rooted
new-instance v0, File
const-string v1, "/system/bin/su"
invoke-direct File-><init>(v0, v1)
invoke-virtual v0, File->exists()Z
move-result v0
if-eqz v0, +4
const 1; return v0                        # su found → rooted
const 0
return v0                                 # clean
```

## Callers

The check is consumed in two places per version:

- `AppleMusicApplication` itself (its own init chain — 4.8.1 reports it in the
  "onCreate: AMLog initialization - Issue found on: " log line)
- one gated main activity, which calls it twice during `onCreate`:
  - 4.8.1: `Lcom/apple/android/music/common/activity/q;`
  - 5.2.1: `Lcom/apple/android/music/common/activity/t;`
  - 6.5.3: `Lcom/apple/android/music/common/activity/u;`
  - 7.0.0: `Lcom/apple/android/music/common/activity/y;`

There is no user-facing "rooted device" dialog string anywhere in the dexes —
the app simply takes a different (degraded) code path when the check is true.

## Telemetry, not blocking

The `, isRooted=` string belongs to a data-class `toString` and the `is_rooted`
key is put into a JSON payload that is uploaded as `os.json`
(`LCd/a;->h()` in 5.2.1). That is analytics — the *blocking* decision comes from
the two call sites above, so patching the file path is enough.

## Why the one-string patch suffices

On a genuinely rooted device all of the sub-checks may report rooted, but
patching the `"/system/bin/su"` constant breaks the `exists()` chain at one
link. On stock devices that were **falsely** tripping the check (observed on
Xiaomi TVs), the only failing check was this one — so a single replacement
makes the app run. As a bonus, replacing with a *non-existent* path rather than
nopping the `exists()` call keeps the control flow (registers, branch targets)
entirely intact — the dex is only 14 bytes different before re-packaging.

## The 4.8.1 reference mod

The original mod ("AppleMusicbywizzeteren.apk") used the replacement string
`/system/bin/applemusicwizzeyeren`. Because that string is longer, the dex had
to be recompiled (smali) rather than patched in place. The builds in this
repository take the equal-length `/system/b1n/su` route so that the dex
bytecode is untouched.

## Reproducing this analysis

```bash
uv run --with androguard python tools/locate_root_check.py <official.apk>
```

prints the strings and their referencing classes/methods for a newly released
version — the names will differ, but one `/system/bin/su` reference under
`AppleMusicApplication` (and the helper chain) is the expected signature.
