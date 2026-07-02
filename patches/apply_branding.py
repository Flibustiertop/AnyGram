#!/usr/bin/env python3
"""Patches Swiftgram source to become AnyGram."""
import sys, os, json, re, shutil

REPO   = sys.argv[1]
API_ID = sys.argv[2] if len(sys.argv) > 2 else "34053256"
API_HASH = sys.argv[3] if len(sys.argv) > 3 else "bc8984a70877b5768e5a6a80222da985"

BUNDLE_ID   = "com.anygram.messenger"
APP_NAME    = "AnyGram"
URL_SCHEME  = "tg"

# 1 ── Build configuration JSON
config = {
    "bundle_id": BUNDLE_ID,
    "api_id":    API_ID,
    "api_hash":  API_HASH,
    "team_id":   "anygram",
    "app_center_id": "0",
    "is_internal_build": "false",
    "is_appstore_build": "false",
    "appstore_id": "0",
    "app_specific_url_scheme": URL_SCHEME,
    "premium_iap_product_id": "",
    "enable_siri": False,
    "enable_icloud": False,
    "sg_config": ""
}
cfg_path = os.path.join(REPO, "build-system", "anygram-configuration.json")
with open(cfg_path, 'w') as f:
    json.dump(config, f, indent=2)
print(f"[OK] Wrote {cfg_path}")

# 2 ── Config-Fork.xcconfig (app name, bundle id, API keys)
xcconfig = os.path.join(REPO, "Telegram", "Telegram-iOS", "Config-Fork.xcconfig")
if os.path.exists(xcconfig):
    with open(xcconfig) as f:
        txt = f.read()
    txt = re.sub(r'APP_NAME=.*',       f'APP_NAME={APP_NAME}',   txt)
    txt = re.sub(r'APP_BUNDLE_ID=.*',  f'APP_BUNDLE_ID={BUNDLE_ID}', txt)
    txt = re.sub(r'APP_SPECIFIC_URL_SCHEME=.*', f'APP_SPECIFIC_URL_SCHEME={URL_SCHEME}', txt)
    txt = re.sub(r'APP_CONFIG_API_ID=\S+',       f'APP_CONFIG_API_ID={API_ID}',    txt)
    txt = re.sub(r'APP_CONFIG_API_HASH="[^"]*"', f'APP_CONFIG_API_HASH=\\"{API_HASH}\\"', txt)
    with open(xcconfig, 'w') as f:
        f.write(txt)
    print(f"[OK] Patched {xcconfig}")

# 3 ── Info.plist display name
plist = os.path.join(REPO, "Telegram", "Telegram-iOS", "Info.plist")
if os.path.exists(plist):
    with open(plist) as f:
        txt = f.read()
    # CFBundleDisplayName
    txt = re.sub(
        r'(<key>CFBundleDisplayName</key>\s*<string>)[^<]*(</string>)',
        rf'\g<1>{APP_NAME}\g<2>', txt)
    # CFBundleName
    txt = re.sub(
        r'(<key>CFBundleName</key>\s*<string>)[^<]*(</string>)',
        rf'\g<1>{APP_NAME}\g<2>', txt)
    with open(plist, 'w') as f:
        f.write(txt)
    print(f"[OK] Patched {plist}")

# 4 ── Remove Swiftgram premium IAP references (keep UI intact, just disable payment flow)
# Find and patch SGPremiumIntroController or similar subscription controllers
sg_premium = os.path.join(REPO, "submodules", "TelegramUI", "Sources", "SGPremiumIntroController.swift")
if os.path.exists(sg_premium):
    os.remove(sg_premium)
    print(f"[OK] Removed {sg_premium}")

print("[DONE] Branding complete")
