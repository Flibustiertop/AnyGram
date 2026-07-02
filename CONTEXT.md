# AnyGram (Swiftgram-based) — Project Context for AI Assistants

> Repo: https://github.com/aIIsafe/anygram
> Local: `C:\Users\aka pro\Desktop\anygram-swiftgram-build\`

---

## 1. What is this?

This repo contains **build scripts and patches** that download Swiftgram
(= full Telegram iOS fork) and apply AnyGram branding on top.

The ACTUAL Telegram code is NOT in this repo — it is cloned from
`https://github.com/Swiftgram/Telegram-iOS` during the CI build.

**User needs:** Windows only, no Mac, free Apple ID → IPA via Sideloadly.

---

## 2. Repo Structure

```
anygram/
├── .github/workflows/build.yml   ← main CI (macos-13, ~2h build time)
├── patches/
│   ├── apply_branding.py         ← app name, bundle ID, API keys, config JSON
│   ├── apply_proxy.py            ← MTProto proxy injection into AppDelegate.swift
│   └── apply_icon.sh             ← replace app icon in all xcassets
├── assets/
│   └── AppIcon.png               ← AnyGram icon 1024×1024
└── CONTEXT.md                    ← this file
```

---

## 3. Build Parameters

| Parameter | Value |
|-----------|-------|
| App name | AnyGram |
| Bundle ID | `com.anygram.messenger` |
| API ID | `34053256` (secret: `TELEGRAM_API_ID`) |
| API Hash | `bc8984a70877b5768e5a6a80222da985` (secret: `TELEGRAM_API_HASH`) |
| URL Scheme | `tg` |
| Proxy server | `78.17.154.32:443` |
| Proxy secret | `ee012c78136de96da97a3b0c9b5dc635fd6966636f6e6669672e6d65` |
| Proxy type | MTProto FakeTLS |
| Swiftgram source | `https://github.com/Swiftgram/Telegram-iOS` |
| Build runner | `macos-13` |
| Build system | Bazel + `fake-codesigning` |

---

## 4. How the Build Works

```
GitHub Actions (macos-13)
  1. Checkout this repo (patches + assets)
  2. Free disk (~10 GB from simulators)
  3. Select Xcode version from versions.json
  4. git clone --depth=1 --recurse-submodules --shallow-submodules Swiftgram → /Users/Shared/telegram-ios
  5. python3 patches/apply_branding.py  → changes Config-Fork.xcconfig, Info.plist, creates anygram-configuration.json
  6. python3 patches/apply_proxy.py     → creates AnyGramProxySetup.swift, patches AppDelegate.swift
  7. bash patches/apply_icon.sh         → sips resize + Contents.json update for all appiconsets
  8. python3 build-system/Make/ImportCertificates.py  (fake certs)
  9. python3 build-system/Make/Make.py ... build --configuration=release_arm64
 10. Collect IPA from bazel-out/...
 11. Upload artifact "AnyGram-Swiftgram-IPA"
```

---

## 5. How to Trigger Build

```powershell
gh workflow run build.yml --repo aIIsafe/anygram
# Monitor:
gh run list --repo aIIsafe/anygram --limit 1
gh run watch <RUN_ID> --repo aIIsafe/anygram
```

---

## 6. Proxy Injection Details

**File created:** `submodules/TelegramUI/Sources/AnyGramProxySetup.swift`

This Swift file defines `AnyGramProxySetup.injectDefaultProxy(accountManager:...)` which:
1. Checks `UserDefaults` for `anygram_default_proxy_v2`
2. If not set: converts hex secret to `Data`, creates `ProxyServerSettings(.mtp(secret:))`
3. Calls `updateProxySettingsInteractively(accountManager:)` to save + enable the proxy
4. Sets the UserDefaults flag so it only runs once

**Injection point in AppDelegate.swift:** After `SharedAccountContext(` constructor call.
Fallback: After `self.accountManager = accountManager` line.

**BUILD file registration:** `AnyGramProxySetup.swift` is added to TelegramUI module's
source list in `submodules/TelegramUI/BUILD`.

---

## 7. Branding Changes Made

In `apply_branding.py`:

1. **`build-system/anygram-configuration.json`** (new file) — full config with API keys
2. **`Telegram/Telegram-iOS/Config-Fork.xcconfig`** — patched:
   - `APP_NAME=AnyGram`
   - `APP_BUNDLE_ID=com.anygram.messenger`
   - `APP_CONFIG_API_ID=34053256`
   - `APP_CONFIG_API_HASH="bc8984a70877b5768e5a6a80222da985"`
3. **`Telegram/Telegram-iOS/Info.plist`** — `CFBundleDisplayName` and `CFBundleName` → `AnyGram`

---

## 8. WHY BLACK SCREEN HAPPENS (and how to avoid it)

### Root causes of black screen after Sideloadly install:

| Cause | Symptom | Fix |
|-------|---------|-----|
| `enable_icloud: true` in config | Crash on launch (iCloud entitlement not granted by free Apple ID) | Set `enable_icloud: false` in config |
| `enable_siri: true` in config | Crash on launch | Set `enable_siri: false` |
| APNS `production` environment | Crash / black screen | Patch entitlements to `development` |
| Wrong `bundle_id` in config | Build fails / codesigning mismatch | Keep `ph.telegra.Telegraph` — matches fake-codesigning profiles |
| Wrong `team_id` in config | Build fails / codesigning mismatch | Keep `C67CF9S4VU` — matches fake-codesigning certs |
| Missing or wrong API keys | App opens but can't connect | Use correct `api_id` / `api_hash` from my.telegram.org |

### CRITICAL RULE about bundle_id and team_id:
The `fake-codesigning/profiles/*.mobileprovision` files inside Swiftgram are tied to:
- `bundle_id = "ph.telegra.Telegraph"`
- `team_id = "C67CF9S4VU"`

NEVER change these in the config — the IPA will fail to build or sign.
The display name "AnyGram" comes from `Info.plist CFBundleDisplayName`, NOT from bundle_id.

---

## 9. Common Build Problems & Fixes

### Build times out (6h limit)
- Shallow clone helps a lot (`--depth=1 --shallow-submodules`)
- If still timing out: try using `--no-build-extension-targets` or `--parallelism=4`
- Consider using a self-hosted runner (needs a Mac)

### Proxy injection fails
- Check if `AnyGramProxySetup.swift` was created (look in build log step 6)
- The injection marker `SharedAccountContext(` might have moved in a newer Swiftgram version
- Fallback to `self.accountManager = accountManager` marker

### Icon replacement fails
- `sips` requires macOS — always available on `macos-13` runner
- If Contents.json is not updated, icon may not show correctly

### `updateProxySettingsInteractively` import errors
- Ensure `AnyGramProxySetup.swift` imports: `Foundation`, `TelegramCore`, `Postbox`, `SwiftSignalKit`
- Ensure it's registered in `submodules/TelegramUI/BUILD`

---

## 9. User Info

- GitHub: `aIIsafe`
- No Mac, no paid Apple account
- Language: Russian
- IPA installed via Sideloadly

---

## 10. The Other AnyGram Project (BetterTG-based)

There is also a simpler, faster-building project at `aIIsafe/BetterTG` workspace
`c:\Users\aka pro\Desktop\anygram bettertg`. It's a lighter TDLib-based client
with custom UI. See `CONTEXT.md` there for details.

Use BetterTG for quick UI experiments; Swiftgram for full feature parity.

---

*Last updated: 2026-07-02*
