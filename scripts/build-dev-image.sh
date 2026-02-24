#!/bin/bash
set -e

# Cardano SeedSigner Development Image Builder
# Builds a dev image that loads app code from SD card for faster iteration.
#
# Usage:
#   ./scripts/build-dev-image.sh [pi0|pi02w|pi2|pi4]
#
# Dev workflow:
#   1. Run this script once to build the dev image
#   2. Flash image to SD card
#   3. Copy src/ folder to SD card's FAT partition
#   4. Boot Pi, edit code on SD card, reboot to test
#
# The dev image:
#   - Checks /mnt/microsd/src first, falls back to /opt/src
#   - Waits for SD card mount before starting app (S50 instead of S02)
#   - Includes all dependencies (cometa, etc.) baked in
#   - Does NOT include app source code (comes from SD card)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="${PROJECT_DIR}/../cardano-seedsigner-os"

# Default target
TARGET="${1:-pi0}"

# Validate target
case "$TARGET" in
    pi0)
        echo "Building DEV image for target: $TARGET (ARMv6)"
        ;;
    pi02w|pi2|pi4)
        echo "Building DEV image for target: $TARGET (ARMv7)"
        ;;
    *)
        echo "Usage: $0 [pi0|pi02w|pi2|pi4]"
        echo ""
        echo "Targets:"
        echo "  pi0    - Raspberry Pi Zero (ARMv6)"
        echo "  pi02w  - Raspberry Pi Zero 2 W (ARMv7)"
        echo "  pi2    - Raspberry Pi 2 (ARMv7)"
        echo "  pi4    - Raspberry Pi 4 (ARMv7)"
        echo ""
        echo "This builds a DEVELOPMENT image that loads app code from SD card."
        echo "After flashing, copy your src/ folder to the SD card's FAT partition."
        exit 1
        ;;
esac

# Cardano SeedSigner OS version
SEEDSIGNER_OS_VERSION="${SEEDSIGNER_OS_VERSION:-v0.0.1}"

# Clone cardano-seedsigner-os if not present
if [ ! -d "$BUILD_DIR" ]; then
    echo "Cloning cardano-seedsigner-os..."
    git clone --recurse-submodules https://github.com/Biglup/cardano-seedsigner-os.git "$BUILD_DIR"
fi

cd "$BUILD_DIR"

# Checkout the correct version
echo "Checking out cardano-seedsigner-os version $SEEDSIGNER_OS_VERSION..."
git fetch --tags origin
git checkout "$SEEDSIGNER_OS_VERSION" 2>/dev/null || git checkout "tags/$SEEDSIGNER_OS_VERSION" 2>/dev/null || {
    echo "Warning: Could not checkout version $SEEDSIGNER_OS_VERSION, using current branch"
}

# Ensure submodules are at correct version
git submodule update --init --recursive

# Create overlay directories
mkdir -p opt/rootfs-overlay/opt
mkdir -p opt/rootfs-overlay/etc/init.d

# =============================================================================
# PATCH 1: Modify start.sh to check SD card first
# =============================================================================
echo "Patching start.sh for SD card loading..."
cat > opt/rootfs-overlay/start.sh << 'EOF'
#!/bin/sh

# Development start script - checks SD card first for app code
# This allows editing code on the SD card without rebuilding the image

# Wait a moment for SD card to be mounted by mdev
sleep 1

# Check if app code exists on SD card
if [ -d "/mnt/microsd/src" ] && [ -f "/mnt/microsd/src/main.py" ]; then
    echo "DEV MODE: Loading app from SD card (/mnt/microsd/src)"
    cd /mnt/microsd/src
else
    echo "Loading app from built-in location (/opt/src)"
    cd /opt/src/
fi

# Start the application
/usr/bin/python3 main.py &
EOF
chmod +x opt/rootfs-overlay/start.sh

# =============================================================================
# PATCH 2: Rename S02seedsigner to S50seedsigner (run after S10mdev)
# =============================================================================
echo "Patching init script order..."

# Remove the original S02seedsigner if it exists
rm -f opt/rootfs-overlay/etc/init.d/S02seedsigner

# Create S50seedsigner (runs after S10mdev which mounts SD card)
cat > opt/rootfs-overlay/etc/init.d/S50seedsigner << 'EOF'
#!/bin/sh
# Provides: SeedSigner (Development)
# Runs after S10mdev to ensure SD card is mounted

start() {
    /start.sh &
    echo "SeedSigner (dev) starting up"
}

stop() {
    echo "SeedSigner (dev) shutting down"
}

status() {
    echo "SeedSigner (dev) status check"
}

case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    status)
        status
        ;;
    *)
        echo $"Usage: $0 {start|stop|status}"
        exit 5
esac
exit $?
EOF
chmod +x opt/rootfs-overlay/etc/init.d/S50seedsigner

# =============================================================================
# NOTE: We do NOT copy src/ or l10n/ - they will come from SD card
# The app's l10n path resolution looks for:
#   1. <source_root>/l10n/translations (4 parents up from settings.py)
#   2. <cwd>/l10n/translations
# When running from /mnt/microsd/src, it finds /mnt/microsd/l10n/translations
# =============================================================================
echo "Skipping src/ and l10n/ copy (will be loaded from SD card)"
echo ""
echo "IMPORTANT: After flashing, use copy-to-sdcard.sh to copy both src/ and l10n/"

# Remove any existing src/l10n in overlay to ensure clean state
rm -rf opt/rootfs-overlay/opt/src
rm -rf opt/rootfs-overlay/opt/l10n

# =============================================================================
# Build Docker container if needed
# =============================================================================
if ! docker image inspect seedsigner-os-build &>/dev/null; then
    echo "Building Docker container..."
    docker build -t seedsigner-os-build .
fi

# Create cache directories
mkdir -p ~/.buildroot-ccache images buildroot_dl

# =============================================================================
# Build the image using -dev board config
# =============================================================================
echo "Starting DEV build for $TARGET (this may take ~1 hour on first run)..."
docker run --rm \
    -e FORCE_UNSAFE_CONFIGURE=1 \
    -v "$(pwd)/opt:/opt" \
    -v "$(pwd)/images:/images" \
    -v "$(pwd)/buildroot_dl:/buildroot_dl" \
    -v "${HOME}/.buildroot-ccache:/root/.buildroot-ccache" \
    seedsigner-os-build \
    --${TARGET} --dev --skip-repo --no-clean

# Find and report the built image
IMAGE=$(ls -t images/cardano_seedsigner_os*.img 2>/dev/null | head -1)
if [ -n "$IMAGE" ]; then
    echo ""
    echo "=========================================="
    echo "DEV Build complete!"
    echo "=========================================="
    echo ""
    echo "Image: $IMAGE"
    echo "Size: $(du -h "$IMAGE" | cut -f1)"
    echo ""
    echo "To flash to SD card:"
    echo "  sudo dd if=$IMAGE of=/dev/sdX bs=4M status=progress && sync"
    echo ""
    echo "After flashing, copy your app source to the SD card:"
    echo "  # Mount the SD card (it will appear as SEEDSIGNDEV or CARDANOSSOS)"
    echo "  ./scripts/copy-to-sdcard.sh /media/\$USER/SEEDSIGNDEV"
    echo ""
    echo "  Or manually:"
    echo "  cp -r ${PROJECT_DIR}/src /media/\$USER/SEEDSIGNDEV/"
    echo "  cp -r ${PROJECT_DIR}/l10n /media/\$USER/SEEDSIGNDEV/"
    echo ""
    echo "Development workflow:"
    echo "  1. Edit code in src/ on the SD card (or in repo, then re-copy)"
    echo "  2. Reboot the Pi to test changes"
    echo "  3. No image rebuild needed!"
    echo ""
    echo "To update code on SD card:"
    echo "  ./scripts/copy-to-sdcard.sh /media/\$USER/SEEDSIGNDEV"
    echo ""
    echo "Replace /dev/sdX with your SD card device (use 'lsblk' to find it)"
else
    echo "Build may have failed - no image found"
    exit 1
fi
