# AnyGram

Custom Telegram iOS client based on [Swiftgram](https://github.com/Swiftgram/Telegram-iOS).

## What's different from Swiftgram
- App name: **AnyGram** (instead of Swiftgram)
- Custom app icon
- Swiftgram premium/subscription UI removed
- Default MTProto proxy pre-configured (for users in restricted regions)
- Custom API keys

## Build

Trigger via GitHub Actions → "Build AnyGram IPA" → Run workflow.

### Required GitHub Secrets
| Secret | Value |
|--------|-------|
| `TELEGRAM_API_ID` | Your Telegram API ID |
| `TELEGRAM_API_HASH` | Your Telegram API hash |

> If secrets are not set, the build falls back to hardcoded values in `patches/apply_branding.py`.

## Install
1. Download `AnyGram.ipa` from the workflow artifacts
2. Install via [Sideloadly](https://sideloadly.io/) with your Apple ID
