#!/usr/bin/env python3
"""
Patches Swiftgram source for AnyGram branding.

IMPORTANT:
  - bundle_id MUST stay "ph.telegra.Telegraph" (matches fake-codesigning profiles)
  - team_id MUST stay "C67CF9S4VU" (matches fake-codesigning certificates)
  - Only change: API keys, display name, iCloud/Siri off
  When the user installs via Sideloadly they can optionally change bundle ID there.
"""
import sys, os, json, re, shutil

REPO     = sys.argv[1]
API_ID   = sys.argv[2] if len(sys.argv) > 2 else "34053256"
API_HASH = sys.argv[3] if len(sys.argv) > 3 else "bc8984a70877b5768e5a6a80222da985"

APP_DISPLAY_NAME = "AnyGram"

# ── 1. Patch appstore-configuration.json in-place ─────────────────────────
# We KEEP bundle_id="ph.telegra.Telegraph" and team_id="C67CF9S4VU"
# so they match the fake-codesigning provisioning profiles.
cfg_path = os.path.join(REPO, "build-system", "appstore-configuration.json")
with open(cfg_path) as f:
    cfg = json.load(f)

cfg["api_id"]                = API_ID
cfg["api_hash"]              = API_HASH
cfg["is_appstore_build"]     = "false"
cfg["is_internal_build"]     = "false"
cfg["enable_siri"]           = False   # free Apple ID can't grant Siri entitlement
cfg["enable_icloud"]         = False   # free Apple ID can't grant iCloud entitlement
cfg["premium_iap_product_id"] = ""
cfg["sg_config"]             = ""

with open(cfg_path, "w") as f:
    json.dump(cfg, f, indent=2)
print(f"[OK] Patched {cfg_path}  (bundle_id={cfg['bundle_id']}, team_id={cfg['team_id']})")

# ── 2. Change display name in Info.plist ──────────────────────────────────
plist = os.path.join(REPO, "Telegram", "Telegram-iOS", "Info.plist")
if os.path.exists(plist):
    with open(plist) as f:
        txt = f.read()
    txt = re.sub(
        r'(<key>CFBundleDisplayName</key>\s*<string>)[^<]*(</string>)',
        rf'\g<1>{APP_DISPLAY_NAME}\g<2>', txt)
    txt = re.sub(
        r'(<key>CFBundleName</key>\s*<string>)[^<]*(</string>)',
        rf'\g<1>{APP_DISPLAY_NAME}\g<2>', txt)
    with open(plist, "w") as f:
        f.write(txt)
    print(f"[OK] Patched {plist}")
else:
    print(f"[WARN] {plist} not found")

# ── 3. Change APP_NAME in Config-Fork.xcconfig ────────────────────────────
xcconfig = os.path.join(REPO, "Telegram", "Telegram-iOS", "Config-Fork.xcconfig")
if os.path.exists(xcconfig):
    with open(xcconfig) as f:
        txt = f.read()
    txt = re.sub(r'APP_NAME=.*', f'APP_NAME={APP_DISPLAY_NAME}', txt)
    # Keep original bundle ID and scheme — they match fake-codesigning profiles!
    # Just update API keys
    txt = re.sub(r'APP_CONFIG_API_ID=\S+',       f'APP_CONFIG_API_ID={API_ID}',    txt)
    txt = re.sub(r'APP_CONFIG_API_HASH="[^"]*"', f'APP_CONFIG_API_HASH=\\"{API_HASH}\\"', txt)
    with open(xcconfig, "w") as f:
        f.write(txt)
    print(f"[OK] Patched {xcconfig}")

# ── 4. Disable iCloud & Siri in all entitlement files ────────────────────
# These cause crashes when installed via Sideloadly (free Apple ID)
def strip_entitlements(path):
    if not os.path.exists(path):
        return
    with open(path) as f:
        txt = f.read()
    changed = False
    # Remove iCloud-related entitlements
    for key in [
        "com.apple.developer.icloud-container-identifiers",
        "com.apple.developer.icloud-services",
        "com.apple.developer.ubiquity-container-identifiers",
        "com.apple.developer.ubiquity-kvstore-identifier",
    ]:
        pattern = rf'<key>{re.escape(key)}</key>\s*(<array>.*?</array>|<string>[^<]*</string>)'
        new_txt = re.sub(pattern, '', txt, flags=re.DOTALL)
        if new_txt != txt:
            txt = new_txt
            changed = True
    # Remove Siri entitlement
    for key in ["com.apple.developer.siri"]:
        pattern = rf'<key>{re.escape(key)}</key>\s*<true/>'
        new_txt = re.sub(pattern, '', txt)
        if new_txt != txt:
            txt = new_txt
            changed = True
    if changed:
        with open(path, "w") as f:
            f.write(txt)
        print(f"[OK] Stripped iCloud/Siri from {path}")

for root, dirs, files in os.walk(REPO):
    for fname in files:
        if fname.endswith(".entitlements"):
            strip_entitlements(os.path.join(root, fname))

# ── 5. Disable push notifications entitlement from the main app target ────
# Sideloadly / free Apple ID can't grant push notifications for APNS production
# (it can for development APNS, but let's keep it to avoid black screen)
main_entitlements = os.path.join(
    REPO, "Telegram", "Telegram-iOS", "Telegram-iOS.entitlements"
)
# If it exists, already handled above; else search
for root, dirs, files in os.walk(os.path.join(REPO, "Telegram")):
    for fname in files:
        if fname.endswith(".entitlements"):
            path = os.path.join(root, fname)
            with open(path) as f:
                txt = f.read()
            # Change production APNS to development (works with Sideloadly)
            new_txt = txt.replace(
                "<string>aps-environment</string>\n\t<string>production</string>",
                "<string>aps-environment</string>\n\t<string>development</string>"
            )
            if new_txt != txt:
                with open(path, "w") as f:
                    f.write(new_txt)
                print(f"[OK] Switched APNS production→development in {path}")

print("[DONE] Branding complete")
print(f"       Display name : {APP_DISPLAY_NAME}")
print(f"       Bundle ID    : ph.telegra.Telegraph  (unchanged — matches fake-codesigning)")
print(f"       API ID       : {API_ID}")
print(f"       iCloud/Siri  : disabled")
