#!/usr/bin/env python3
"""
Injects a hardcoded default MTProto proxy into AppDelegate.swift.
The proxy is set on first launch via updateProxySettingsInteractively.

Proxy:  server=78.17.154.32  port=443
Secret: ee012c78136de96da97a3b0c9b5dc635fd6966636f6e6669672e6d65  (FakeTLS/MTProto)
"""
import sys, os, re

REPO = sys.argv[1]

PROXY_SERVER = "78.17.154.32"
PROXY_PORT   = 443
PROXY_SECRET = "ee012c78136de96da97a3b0c9b5dc635fd6966636f6e6669672e6d65"

# Swift code to inject (placed right before the closing brace of didFinishLaunchingWithOptions)
PROXY_SWIFT = f'''
        // AnyGram: inject default MTProto proxy on first launch
        AnyGramProxySetup.injectDefaultProxy(
            accountManager: accountManager,
            server: "{PROXY_SERVER}",
            port: {PROXY_PORT},
            secretHex: "{PROXY_SECRET}"
        )
'''

# File to create: AnyGramProxySetup.swift
PROXY_SETUP_SWIFT = '''import Foundation
import TelegramCore
import Postbox
import SwiftSignalKit

struct AnyGramProxySetup {
    static func injectDefaultProxy(
        accountManager: AccountManager<TelegramAccountManagerTypes>,
        server: String,
        port: Int32,
        secretHex: String
    ) {
        let key = "anygram_default_proxy_v2"
        guard !UserDefaults.standard.bool(forKey: key) else { return }

        // Convert hex secret to Data
        var secretData = Data()
        var index = secretHex.startIndex
        while index < secretHex.endIndex {
            let nextIndex = secretHex.index(index, offsetBy: 2)
            if let byte = UInt8(secretHex[index..<nextIndex], radix: 16) {
                secretData.append(byte)
            }
            index = nextIndex
        }

        let proxyServer = ProxyServerSettings(
            host: server,
            port: port,
            connection: .mtp(secret: secretData)
        )

        let _ = (updateProxySettingsInteractively(accountManager: accountManager) { settings in
            var settings = settings
            // Add only if not already present
            if !settings.servers.contains(where: { $0.host == server && $0.port == port }) {
                settings.servers.append(proxyServer)
            }
            settings.activeServer = proxyServer
            settings.enabled = true
            return settings
        } |> deliverOnMainQueue).start(next: { _ in
            UserDefaults.standard.set(true, forKey: key)
        })
    }
}
'''

# Write AnyGramProxySetup.swift next to AppDelegate
app_delegate_dir = os.path.join(REPO, "submodules", "TelegramUI", "Sources")
proxy_setup_path = os.path.join(app_delegate_dir, "AnyGramProxySetup.swift")

with open(proxy_setup_path, 'w') as f:
    f.write(PROXY_SETUP_SWIFT)
print(f"[OK] Created {proxy_setup_path}")

# Patch AppDelegate.swift: find where accountManager is first stored and inject our call
app_delegate_path = os.path.join(app_delegate_dir, "AppDelegate.swift")
if not os.path.exists(app_delegate_path):
    print(f"[WARN] AppDelegate.swift not found at {app_delegate_path}, skipping injection")
    sys.exit(0)

with open(app_delegate_path) as f:
    content = f.read()

# Find a stable injection point: right after SharedAccountContext is created
# Look for the pattern "SharedAccountContext(" and inject after its line
injection_marker = "let sharedContext = SharedAccountContext("
if injection_marker in content:
    # Find the block — the SharedAccountContext init likely spans multiple lines
    # Find where the line ends (find the closing paren of the SharedAccountContext call)
    idx = content.index(injection_marker)
    # Count open parens to find end of constructor call
    depth = 0
    i = idx
    found_end = -1
    while i < len(content):
        if content[i] == '(':
            depth += 1
        elif content[i] == ')':
            depth -= 1
            if depth == 0:
                found_end = i
                break
        i += 1

    if found_end >= 0:
        # Insert after the closing ) and its line
        newline_after = content.index('\n', found_end)
        injection_point = newline_after + 1
        patched = (
            content[:injection_point]
            + PROXY_SWIFT
            + content[injection_point:]
        )
        with open(app_delegate_path, 'w') as f:
            f.write(patched)
        print(f"[OK] Injected proxy call into {app_delegate_path}")
    else:
        print("[WARN] Could not find end of SharedAccountContext constructor, trying fallback")
else:
    # Fallback: inject near 'self.accountManager ='
    fallback_marker = "self.accountManager = accountManager"
    if fallback_marker in content:
        idx = content.index(fallback_marker)
        newline_after = content.index('\n', idx)
        injection_point = newline_after + 1
        patched = (
            content[:injection_point]
            + PROXY_SWIFT
            + content[injection_point:]
        )
        with open(app_delegate_path, 'w') as f:
            f.write(patched)
        print(f"[OK] Injected proxy call via fallback marker into {app_delegate_path}")
    else:
        print("[WARN] No injection point found. Proxy must be configured manually on first launch.")
        print(f"      URL: tg://proxy?server={PROXY_SERVER}&port={PROXY_PORT}&secret={PROXY_SECRET}")

# Register AnyGramProxySetup.swift in the TelegramUI BUILD file
build_file = os.path.join(app_delegate_dir, "..", "BUILD")
if os.path.exists(build_file):
    with open(build_file) as f:
        build_content = f.read()
    if "AnyGramProxySetup.swift" not in build_content:
        # Add to swift_sources list — look for AppDelegate.swift entry and add after it
        build_content = build_content.replace(
            '"Sources/AppDelegate.swift"',
            '"Sources/AppDelegate.swift",\n        "Sources/AnyGramProxySetup.swift"'
        )
        with open(build_file, 'w') as f:
            f.write(build_content)
        print(f"[OK] Registered AnyGramProxySetup.swift in BUILD")

print("[DONE] Proxy injection complete")
