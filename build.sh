#!/usr/bin/env bash
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "=== Kouprey-Zip Build Script (Linux) ==="

# Step 1: Ensure config directory and default settings
mkdir -p "$ROOT/config"
if [ ! -f "$ROOT/config/settings.json" ]; then
    echo '{"theme": "light", "language": "km", "recent_files": []}' > "$ROOT/config/settings.json"
    echo "Created default config/settings.json"
fi

# Step 2: Clean old build artifacts
echo "Cleaning old build artifacts..."
rm -rf "$ROOT/build" "$ROOT/dist/Kouprey-Zip"

# Step 3: Check for PyInstaller
if ! command -v pyinstaller &>/dev/null; then
    echo "PyInstaller not found. Installing..."
    pip install pyinstaller
fi

# Step 4: Run PyInstaller
echo "Running PyInstaller..."
pyinstaller "$ROOT/Kouprey-Zip.spec" --clean --noconfirm

echo ""
echo "Build complete!"
echo "Output: dist/Kouprey-Zip/"
echo ""
echo "To package for distribution:"
echo "  tar -czf kouprey-zip-linux-\$(uname -m).tar.gz -C dist Kouprey-Zip"
