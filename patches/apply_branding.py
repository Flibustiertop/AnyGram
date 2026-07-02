#!/usr/bin/env python3
"""
Patches Swiftgram source to become AnyGram.

IMPORTANT: bundle_id and team_id MUST stay the same as Swiftgram's appstore-configuration.json
because fake-codesigning profiles/certs are hardcoded for:
  bundle_id = "ph.telegra.Telegraph"
  team_id   = "C67CF9S4VU"
Sideloadly will re-sign with the user's Apple ID, replacing these automatically.
"""
import sys, os, json, re

REPO     = sys.argv[1]
API_ID   = sys.argv[2] if len(sys.argv) > 2 else "34053256"
API_HASH = sys.argv[3] if len(sys.argv) > 3 else "bc8984a70877b5768e5a6a80222da985"

# Must keep Telegram's bundle_id/team_id for fake-codesigning to work!
BUNDLE_ID = "ph.telegra.Telegraph"
TEAM_ID   = "C67CF9S4VU"
APP_NAME  = "AnyGram"

# ── 1. Create anygram-configuration.json ─────────────────────────────────────
config = {
    "bundle_id":                BUNDLE_ID,
    "api_id":                   API_ID,
    "api_hash":                 API_HASH,
    "team_id":                  TEAM_ID,
    "app_center_id":            "0",
    "is_internal_build":        "false",
    "is_appstore_build":        "false",
    "appstore_id":              "0",
    "app_specific_url_scheme":  "tg",
    "premium_iap_product_id":   "",
    "enable_siri":              False,
    "enable_icloud":            False,
    "sg_config":                ""
}
cfg_path = os.path.join(REPO, "build-system", "anygram-configuration.json")
with open(cfg_path, 'w') as f:
    json.dump(config, f, indent=2)
print(f"[OK] config → {cfg_path}")

# ── 2. Config-Fork.xcconfig: change only the display name ────────────────────
xcconfig = os.path.join(REPO, "Telegram", "Telegram-iOS", "Config-Fork.xcconfig")
if os.path.exists(xcconfig):
    with open(xcconfig) as f:
        txt = f.read()
    # Change display name only — DO NOT touch BUNDLE_ID or TEAM_ID
    txt = re.sub(r'APP_NAME=.*', f'APP_NAME={APP_NAME}', txt)
    # Update API keys in the GCC_PREPROCESSOR_DEFINITIONS line
    txt = re.sub(r'APP_CONFIG_API_ID=\S+',         f'APP_CONFIG_API_ID={API_ID}',       txt)
    txt = re.sub(r'APP_CONFIG_API_HASH="[^"]*"',   f'APP_CONFIG_API_HASH=\\"{API_HASH}\\"', txt)
    with open(xcconfig, 'w') as f:
        f.write(txt)
    print(f"[OK] xcconfig patched (name + API keys only)")
else:
    print(f"[WARN] xcconfig not found: {xcconfig}")

# ── 3. Info.plist: change CFBundleDisplayName and CFBundleName ───────────────
plist = os.path.join(REPO, "Telegram", "Telegram-iOS", "Info.plist")
if os.path.exists(plist):
    with open(plist) as f:
        txt = f.read()
    txt = re.sub(
        r'(<key>CFBundleDisplayName</key>\s*<string>)[^<]*(</string>)',
        rf'\g<1>{APP_NAME}\g<2>', txt)
    txt = re.sub(
        r'(<key>CFBundleName</key>\s*<string>)[^<]*(</string>)',
        rf'\g<1>{APP_NAME}\g<2>', txt)
    with open(plist, 'w') as f:
        f.write(txt)
    print(f"[OK] Info.plist display name patched")
else:
    print(f"[WARN] Info.plist not found: {plist}")

# ── 4. Remove Swiftgram subscription paywall popup (optional, safe) ──────────
# Swiftgram has its own premium intro; we just skip it, leaving normal Telegram UI
for candidate in [
    os.path.join(REPO, "submodules", "TelegramUI", "Sources", "SGPremiumIntroController.swift"),
]:
    if os.path.exists(candidate):
        os.remove(candidate)
        print(f"[OK] Removed {os.path.basename(candidate)}")

print("[DONE] Branding patched")
