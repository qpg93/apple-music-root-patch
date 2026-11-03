# Disclaimer

**Read this before using anything in this repository.**

## 1. No affiliation, no endorsement

This project is an independent technical study. It is **not** affiliated with,
endorsed by, sponsored by, or connected to Apple Inc. in any way.

- "Apple" and "Apple Music" are trademarks of Apple Inc.
- The app analyzed here is the property of Apple Inc. All rights remain with Apple.
- Nothing here should be read as Apple's position, or as an invitation to do
  anything against Apple's policies.

## 2. What this repository actually contains

Scripts and documentation **only**. This repository does **not** contain,
does **not** distribute, and has never distributed:

- Apple Music APK/IPA binaries (official or modified)
- decrypted/refused-or-broken DRM content
- Apple source code

If you build a patched APK here, you do so **locally** by downloading the
official bundle from a third-party store and applying a 14-byte patch yourself.

## 3. Educational and research purpose

The purpose of this work is to document software-engineering practice on a
real-world APK: versioned bundle formats, dex constant pools, obfuscation
drift analysis, binary patching, APK signing schemes, and sideloading flows.
It was written because the upstream repo's one-line description had no
workflow a second person could follow.

## 4. On the "root check" patch specifically

The patch replaces a **self-referential file-existence probe** inside the app,
`new File("/system/bin/su").exists()`, with a path that does not exist. The
belief of this project's author is that this is a diagnostic, not an access
control on any copyrighted work (no DRM, no content gating, no license
verification is touched). **This is not a legal opinion or legal advice**, and
no jurisdiction or court is bound by it.

- **DRM is not touched.** Film/music content remains fully protected; playback
  and downloads require a normal Apple Music session and subscription.
- **No subscription bypass.** No code path grants access to content without an
  entitlement the user already has.
- **No other code path is altered.** Every shipping byte except the string
  `/system/bin/su` → `/system/b1n/su` is untouched before re-signing.

## 5. What the user is responsible for

Using a rebuilt APK is a deviation from Apple's End User License Agreement and
may also violate local laws, your device warranty, enterprise MDM policies, or
app-store terms. **You** agree that:

- you use the scripts at your own risk, understanding what they modify;
- you own or have the right to use whatever device you install on;
- you hold a genuine Apple Music subscription if you intend to use the app;
- you will not use this to circumvent any protection, share content, or
  redistribute Apple binaries (modified or not);
- compliance with the Apple Music Terms of Use, local law, and your device
  maker's conditions remains your responsibility at all times.

## 6. No warranty

The scripts are provided "AS IS", without warranty of any kind, express or
implied, including but not limited to the warranties of merchantability,
fitness for a particular purpose and non-infringement. In no event shall the
author be liable for any claim, damages, app malfunction, account restriction,
or other liability arising from the use of the scripts. Your Apple account,
your device, and your data are your responsibility — back them up.

## 7. Takedown commitment

If Apple Inc. (or any rights holder) considers any content here infringing and
files a valid DMCA notice, the repository owner will remove the disputed
content promptly and responsibly. Contact details for takedown requests are
not required by GitHub's process itself; use the normal GitHub DMCA flow.

## 8. Contributions carry the same rules

PRs that propose distributing Apple binaries, defeating DRM, or otherwise
shifting this repository from *technique + tooling* toward *piracy or
binary distribution* will be declined, reversed, and documented.
