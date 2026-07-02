#!/usr/bin/env bash
# Replaces Swiftgram's app icon with the AnyGram icon.
# Requires: ImageMagick (brew install imagemagick) or sips (built into macOS)
set -euo pipefail

REPO_DIR="$1"
ICON_SRC="$2"   # 1024×1024 PNG

ASSETS_DIR="$REPO_DIR/Telegram/Telegram-iOS/DefaultAppIcon.xcassets"
ICONS_DIR="$REPO_DIR/Telegram/Telegram-iOS/Icons.xcassets"

# Sizes needed for iOS app icon (xcassets)
declare -a SIZES=(20 29 40 58 60 76 80 87 120 152 167 180 1024)

copy_icon() {
    local dst_dir="$1"
    local name="$2"
    local size="$3"
    # Use sips (always available on macOS) to resize
    sips -z "$size" "$size" "$ICON_SRC" --out "${dst_dir}/${name}" > /dev/null 2>&1 || true
}

# Find all AppIcon appiconset directories and replace images
find "$REPO_DIR/Telegram" -name "*.appiconset" -type d | while read -r iconset; do
    echo "[icon] Processing $iconset"
    # Create all size variants
    for size in "${SIZES[@]}"; do
        fname="Icon-${size}.png"
        copy_icon "$iconset" "$fname" "$size"
    done
    
    # Update Contents.json to point to our files
    contents_json="$iconset/Contents.json"
    if [ -f "$contents_json" ]; then
        # Replace all existing filenames with our icon files
        python3 - "$contents_json" "$iconset" "${SIZES[@]}" <<'PYEOF'
import json, sys, os

path = sys.argv[1]
iconset = sys.argv[2]
sizes = [int(x) for x in sys.argv[3:]]

with open(path) as f:
    data = json.load(f)

new_images = []
for img in data.get("images", []):
    scale_str = img.get("scale", "1x")
    scale = int(scale_str.rstrip("x"))
    size_str = img.get("size", "1024x1024")
    pt_size = int(size_str.split("x")[0])
    px_size = pt_size * scale
    
    # Find closest available size
    closest = min(sizes, key=lambda s: abs(s - px_size))
    img["filename"] = f"Icon-{closest}.png"
    new_images.append(img)

data["images"] = new_images
with open(path, 'w') as f:
    json.dump(data, f, indent=2)
print(f"[OK] Updated {path}")
PYEOF
    fi
done

# Also replace the default icon in SGDefault.alticon
default_icon="$REPO_DIR/Telegram/Telegram-iOS/SGDefault.alticon"
if [ -d "$default_icon" ]; then
    for size in "${SIZES[@]}"; do
        copy_icon "$default_icon" "Icon-${size}.png" "$size"
    done
    echo "[OK] Updated SGDefault.alticon"
fi

echo "[DONE] Icon replacement complete"
