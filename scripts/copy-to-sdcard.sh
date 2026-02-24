#!/bin/bash
set -e

# Copy Cardano SeedSigner source code to SD card for development
#
# Usage:
#   ./scripts/copy-to-sdcard.sh /path/to/mounted/sdcard
#
# Example:
#   ./scripts/copy-to-sdcard.sh /media/$USER/SEEDSIGNDEV
#   ./scripts/copy-to-sdcard.sh /media/$USER/CARDANOSSOS

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

if [ -z "$1" ]; then
    echo "Usage: $0 /path/to/mounted/sdcard"
    echo ""
    echo "Example:"
    echo "  $0 /media/\$USER/SEEDSIGNDEV"
    echo "  $0 /media/\$USER/CARDANOSSOS"
    echo ""
    echo "The SD card should be mounted (after flashing the dev image)."
    echo "Use 'lsblk' or 'mount' to find the mount point."
    exit 1
fi

SDCARD_PATH="$1"

# Verify the path exists and is a directory
if [ ! -d "$SDCARD_PATH" ]; then
    echo "Error: $SDCARD_PATH is not a directory or doesn't exist"
    echo ""
    echo "Make sure the SD card is mounted. After inserting, it should appear at:"
    echo "  /media/\$USER/SEEDSIGNDEV  (dev image)"
    echo "  /media/\$USER/CARDANOSSOS  (regular image)"
    exit 1
fi

# Verify source exists
if [ ! -d "$PROJECT_DIR/src" ]; then
    echo "Error: Source directory not found at $PROJECT_DIR/src"
    exit 1
fi

echo "Copying source code to SD card..."
echo "  From: $PROJECT_DIR/src"
echo "  To:   $SDCARD_PATH/src"
echo ""

# Remove old source if it exists
if [ -d "$SDCARD_PATH/src" ]; then
    echo "Removing old source..."
    rm -rf "$SDCARD_PATH/src"
fi

# Copy source
cp -r "$PROJECT_DIR/src" "$SDCARD_PATH/src"

# Remove __pycache__ directories to save space
find "$SDCARD_PATH/src" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# Copy l10n translations if they exist
if [ -d "$PROJECT_DIR/l10n/translations" ]; then
    echo "Copying translations..."
    rm -rf "$SDCARD_PATH/l10n" 2>/dev/null || true
    mkdir -p "$SDCARD_PATH/l10n"
    cp -r "$PROJECT_DIR/l10n/translations" "$SDCARD_PATH/l10n/"
fi

# Sync to ensure all data is written
echo "Syncing..."
sync

echo ""
echo "Done! Source code copied to SD card."
echo ""
echo "Files on SD card:"
ls -la "$SDCARD_PATH/"
echo ""
echo "You can now safely eject the SD card and boot the Pi."
echo "To update code later, just run this script again."
