#!/bin/bash
set -e

# Cardano SeedSigner Image Builder
# Builds bootable images for Raspberry Pi devices using cardano-seedsigner-os
# (which includes libcardano-c and cometa as proper Buildroot packages)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="${PROJECT_DIR}/../cardano-seedsigner-os"

# Default target
TARGET="${1:-pi0}"

# Validate target
case "$TARGET" in
    pi0)
        echo "Building for target: $TARGET (ARMv6)"
        ;;
    pi02w|pi2|pi4)
        echo "Building for target: $TARGET (ARMv7)"
        ;;
    *)
        echo "Usage: $0 [pi0|pi02w|pi2|pi4]"
        echo ""
        echo "Targets:"
        echo "  pi0    - Raspberry Pi Zero (ARMv6)"
        echo "  pi02w  - Raspberry Pi Zero 2 W (ARMv7)"
        echo "  pi2    - Raspberry Pi 2 (ARMv7)"
        echo "  pi4    - Raspberry Pi 4 (ARMv7)"
        exit 1
        ;;
esac

# Cardano SeedSigner OS version (fork with libcardano-c and cometa packages)
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

# Copy source into overlay
echo "Copying cardano-seedsigner source..."
mkdir -p opt/rootfs-overlay/opt
rm -rf opt/rootfs-overlay/opt/src
cp -r "$PROJECT_DIR/src" opt/rootfs-overlay/opt/src

# Remove any pycache directories to save space
find opt/rootfs-overlay/opt/src -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# Copy l10n translations if they exist
if [ -d "$PROJECT_DIR/l10n/translations" ]; then
    echo "Copying translations..."
    mkdir -p opt/rootfs-overlay/opt/l10n
    cp -r "$PROJECT_DIR/l10n/translations" opt/rootfs-overlay/opt/l10n/
fi

# Build Docker container if needed
if ! docker image inspect seedsigner-os-build &>/dev/null; then
    echo "Building Docker container..."
    docker build -t seedsigner-os-build .
fi

# Create cache directories
mkdir -p ~/.buildroot-ccache images buildroot_dl

# Build the image
echo "Starting build for $TARGET (this may take ~1 hour on first run)..."
docker run --rm \
    -e FORCE_UNSAFE_CONFIGURE=1 \
    -v "$(pwd)/opt:/opt" \
    -v "$(pwd)/images:/images" \
    -v "$(pwd)/buildroot_dl:/buildroot_dl" \
    -v "${HOME}/.buildroot-ccache:/root/.buildroot-ccache" \
    seedsigner-os-build \
    --${TARGET} --skip-repo --no-clean

# Find and report the built image
IMAGE=$(ls -t images/cardano_seedsigner_os*.img 2>/dev/null | head -1)
if [ -n "$IMAGE" ]; then
    echo ""
    echo "Build complete!"
    echo "Image: $IMAGE"
    echo "Size: $(du -h "$IMAGE" | cut -f1)"
    echo ""
    echo "To flash to SD card:"
    echo "  sudo dd if=$IMAGE of=/dev/sdX bs=4M status=progress && sync"
    echo ""
    echo "Replace /dev/sdX with your SD card device (use 'lsblk' to find it)"
else
    echo "Build may have failed - no image found"
    exit 1
fi
