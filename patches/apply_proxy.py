#!/usr/bin/env python3
"""
Injects a default MTProto proxy into Swiftgram's AppDelegate.swift.

Strategy:
  1. Creates AnyGramProxySetup.swift in TelegramUI/Sources/
  2. Registers it in the TelegramUI BUILD file
  3. Adds a call in AppDelegate.swift after accountManager is initialized

Proxy:  server=78.17.154.32  port=443
Secret: ee012c78136de96da97a3b0c9b5dc635fd6966636f6e6669672e6d65  (FakeTLS)
"""
import sys, os, re

REPO = sys.argv[1]

PROXY_SERVER = "78.17.154.32"
PROXY_PORT   = 443
PROXY_SECRET = "ee012c78136de96da97a3b0c9b5dc635fd6966636f6e6669672e6d65"

SOURCES_DIR = os.path.join(REPO, "submodules", "TelegramUI", "Sources")

# ── 1. Create AnyGramProxySetup.swift ────────────────────────────────────
SETUP_SWIFT = f'''\
import Foundation
import TelegramCore
import Postbox
import SwiftSignalKit

// AnyGram: auto-configure default MTProto proxy on first launch
public struct AnyGramProxySetup {{
    public static func injectIfNeeded(accountManager: AccountManager<TelegramAccountManagerTypes>) {{
        let udKey = "anygram_proxy_v3"
        guard !UserDefaults.standard.bool(forKey: udKey) else {{ return }}

        // Decode hex secret
        let hex = "{PROXY_SECRET}"
        var secretData = Data()
        var i = hex.startIndex
        while i < hex.endIndex {{
            let j = hex.index(i, offsetBy: 2)
            if let b = UInt8(hex[i..<j], radix: 16) {{ secretData.append(b) }}
            i = j
        }}

        let proxy = ProxyServerSettings(
            host: "{PROXY_SERVER}",
            port: {PROXY_PORT},
            connection: .mtp(secret: secretData)
        )

        let _ = (updateProxySettingsInteractively(accountManager: accountManager) {{ current in
            var s = current
            if !s.servers.contains(where: {{ $0.host == proxy.host && $0.port == proxy.port }}) {{
                s.servers.append(proxy)
            }}
            s.activeServer = proxy
            s.enabled = true
            return s
        }} |> deliverOnMainQueue).start(next: {{ _ in
            UserDefaults.standard.set(true, forKey: udKey)
        }})
    }}
}}
'''

setup_path = os.path.join(SOURCES_DIR, "AnyGramProxySetup.swift")
with open(setup_path, "w") as f:
    f.write(SETUP_SWIFT)
print(f"[OK] Created {setup_path}")

# ── 2. Register in TelegramUI BUILD file ─────────────────────────────────
build_path = os.path.join(REPO, "submodules", "TelegramUI", "BUILD")
if os.path.exists(build_path):
    with open(build_path) as f:
        build_txt = f.read()
    if "AnyGramProxySetup.swift" not in build_txt:
        # Insert after AppDelegate.swift entry
        for marker in ['"Sources/AppDelegate.swift"', '"Sources/SharedAccountContext.swift"']:
            if marker in build_txt:
                build_txt = build_txt.replace(
                    marker,
                    marker + ',\n        "Sources/AnyGramProxySetup.swift"'
                )
                with open(build_path, "w") as f:
                    f.write(build_txt)
                print(f"[OK] Registered in BUILD (after {marker})")
                break
        else:
            print("[WARN] Could not find marker in BUILD — adding manually")
    else:
        print("[OK] AnyGramProxySetup.swift already in BUILD")

# ── 3. Inject call into AppDelegate.swift ─────────────────────────────────
delegate_path = os.path.join(SOURCES_DIR, "AppDelegate.swift")
if not os.path.exists(delegate_path):
    print(f"[WARN] AppDelegate.swift not found at {delegate_path}")
    sys.exit(0)

with open(delegate_path) as f:
    src = f.read()

if "AnyGramProxySetup" in src:
    print("[OK] Proxy already injected into AppDelegate.swift")
    sys.exit(0)

INJECT_CALL = """
        // AnyGram: inject default proxy on first launch
        AnyGramProxySetup.injectIfNeeded(accountManager: accountManager)
"""

INJECTION_MARKERS = [
    # Try to find a stable point after accountManager is ready
    "let sharedContext = SharedAccountContext(",
    "self.sharedContext = SharedAccountContext(",
    "SharedAccountContext(mainWindow:",
    # Fallbacks
    "self.accountManager = accountManager",
    "accountManager: accountManager",
]

injected = False
for marker in INJECTION_MARKERS:
    if marker in src:
        # Find the end of the line containing the marker
        idx = src.index(marker)
        # If it's a multi-line constructor, skip to the end of the statement
        if marker.endswith("(") or "SharedAccountContext(" in marker:
            # Walk forward to find closing paren at depth 0
            depth = 0
            i = idx
            end_stmt = -1
            while i < len(src):
                if src[i] == '(': depth += 1
                elif src[i] == ')':
                    depth -= 1
                    if depth == 0:
                        end_stmt = i
                        break
                i += 1
            if end_stmt >= 0:
                nl = src.find('\n', end_stmt)
                if nl >= 0:
                    src = src[:nl+1] + INJECT_CALL + src[nl+1:]
                    injected = True
                    print(f"[OK] Injected after '{marker[:60]}...'")
                    break
        else:
            nl = src.find('\n', idx)
            if nl >= 0:
                src = src[:nl+1] + INJECT_CALL + src[nl+1:]
                injected = True
                print(f"[OK] Injected after '{marker}'")
                break

if not injected:
    # Last resort: inject before the last closing brace of didFinishLaunchingWithOptions
    pattern = r'(func application\(_[^{]+\{)'
    m = re.search(pattern, src)
    if m:
        # Find the corresponding closing brace
        start = m.end()
        depth = 1
        i = start
        while i < len(src) and depth > 0:
            if src[i] == '{': depth += 1
            elif src[i] == '}': depth -= 1
            i += 1
        if depth == 0:
            # Insert before the closing brace
            src = src[:i-1] + INJECT_CALL + src[i-1:]
            injected = True
            print("[OK] Injected before closing brace of didFinishLaunchingWithOptions")

if not injected:
    print("[WARN] Could not inject proxy call into AppDelegate.swift")
    print(f"       Add manually: AnyGramProxySetup.injectIfNeeded(accountManager: accountManager)")
else:
    with open(delegate_path, "w") as f:
        f.write(src)

print("[DONE] Proxy injection complete")
