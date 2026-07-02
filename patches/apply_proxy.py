#!/usr/bin/env python3
"""
Injects a default MTProto proxy into Telegram iOS.

Proxy: server=78.17.154.32 port=443
Secret: ee012c78136de96da97a3b0c9b5dc635fd6966636f6e6669672e6d65 (FakeTLS)

Strategy: Creates AnyGramProxySetup.swift and patches AppDelegate.swift
to call it right after the accountManager is available.

Imports used: TelegramCore (contains ProxyServerSettings, updateProxySettingsInteractively)
              SwiftSignalKit (contains deliverOnMainQueue, Signal .start())
"""
import sys, os, re

REPO = sys.argv[1]

PROXY_SERVER = "78.17.154.32"
PROXY_PORT   = 443
PROXY_SECRET = "ee012c78136de96da97a3b0c9b5dc635fd6966636f6e6669672e6d65"

# ── Swift helper file ─────────────────────────────────────────────────────────
PROXY_SETUP_SWIFT = f'''// AnyGramProxySetup.swift — auto-generated, do not edit
import Foundation
import TelegramCore
import SwiftSignalKit

public func anygramInjectDefaultProxy(accountManager: AccountManager<TelegramAccountManagerTypes>) {{
    let key = "anygram_proxy_v2"
    guard !UserDefaults.standard.bool(forKey: key) else {{ return }}

    // Convert hex secret → Data
    let hex = "{PROXY_SECRET}"
    var secretBytes = [UInt8]()
    var idx = hex.startIndex
    while idx < hex.endIndex {{
        let next = hex.index(idx, offsetBy: 2)
        if let byte = UInt8(hex[idx..<next], radix: 16) {{ secretBytes.append(byte) }}
        idx = next
    }}
    let secretData = Data(secretBytes)

    let server = ProxyServerSettings(
        host: "{PROXY_SERVER}",
        port: {PROXY_PORT},
        connection: .mtp(secret: secretData)
    )

    let _ = (updateProxySettingsInteractively(accountManager: accountManager) {{ current in
        var s = current
        if !s.servers.contains(where: {{ $0.host == "{PROXY_SERVER}" && $0.port == {PROXY_PORT} }}) {{
            s.servers.append(server)
        }}
        s.activeServer = server
        s.enabled = true
        return s
    }} |> deliverOnMainQueue).start(next: {{ _ in
        UserDefaults.standard.set(true, forKey: key)
        print("[AnyGram] Default proxy set")
    }})
}}
'''

# ── Write AnyGramProxySetup.swift ─────────────────────────────────────────────
sources_dir = os.path.join(REPO, "submodules", "TelegramUI", "Sources")
proxy_file  = os.path.join(sources_dir, "AnyGramProxySetup.swift")

os.makedirs(sources_dir, exist_ok=True)
with open(proxy_file, 'w') as f:
    f.write(PROXY_SETUP_SWIFT)
print(f"[OK] Created {proxy_file}")

# ── Patch AppDelegate.swift ───────────────────────────────────────────────────
app_delegate = os.path.join(sources_dir, "AppDelegate.swift")
if not os.path.exists(app_delegate):
    print(f"[WARN] AppDelegate.swift not found, skipping injection")
    sys.exit(0)

with open(app_delegate) as f:
    content = f.read()

INJECTION = f'''
        // AnyGram: enable default MTProto proxy on first launch
        anygramInjectDefaultProxy(accountManager: accountManager)
'''

MARKERS = [
    "let sharedContext = SharedAccountContext(",
    "self.accountManager = accountManager",
    "SharedAccountContext.init(",
    "self.sharedContext =",
]

injected = False
for marker in MARKERS:
    if marker in content:
        # Find end of that line
        idx = content.index(marker)
        # If it's a constructor spanning multiple lines, find the end paren
        if marker.endswith("("):
            depth, i = 0, idx
            while i < len(content):
                if content[i] == '(':   depth += 1
                elif content[i] == ')': depth -= 1
                if depth == 0: break
                i += 1
            eol = content.find('\n', i) + 1
        else:
            eol = content.find('\n', idx) + 1

        patched = content[:eol] + INJECTION + content[eol:]
        with open(app_delegate, 'w') as f:
            f.write(patched)
        print(f"[OK] Injected proxy call after marker: {marker[:60]!r}")
        injected = True
        break

if not injected:
    print("[WARN] No injection marker found in AppDelegate.swift")
    print(f"       Add the proxy URL manually: tg://proxy?server={PROXY_SERVER}&port={PROXY_PORT}&secret={PROXY_SECRET}")

# ── Register in TelegramUI BUILD file ────────────────────────────────────────
build_file = os.path.join(sources_dir, "..", "BUILD")
if os.path.exists(build_file):
    with open(build_file) as f:
        build = f.read()
    if "AnyGramProxySetup.swift" not in build:
        # Look for AppDelegate.swift entry in swift_sources
        for target in ['"Sources/AppDelegate.swift"', "'Sources/AppDelegate.swift'"]:
            if target in build:
                replacement = target + ',\n        "Sources/AnyGramProxySetup.swift"'
                build = build.replace(target, replacement, 1)
                with open(build_file, 'w') as f:
                    f.write(build)
                print(f"[OK] Registered AnyGramProxySetup.swift in TelegramUI BUILD")
                break
        else:
            print("[WARN] Could not find AppDelegate.swift in BUILD, skipping registration")
            print("       Build may fail if AnyGramProxySetup.swift is not in BUILD sources")
else:
    print(f"[WARN] BUILD file not found at {build_file}")

print("[DONE] Proxy injection complete")
print(f"       Proxy: {PROXY_SERVER}:{PROXY_PORT} (MTProto FakeTLS)")
