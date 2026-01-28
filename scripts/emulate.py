#!/usr/bin/env python3
"""
Cardano SeedSigner Emulator

This script sets up and launches the SeedSigner emulator for desktop testing.
It creates a build/emulation folder with the patched source code and runs it.

Based on seedsigner-emulator by @EnteroPositivo
https://github.com/enteropositivo/seedsigner-emulator

Usage:
    python emulate.py [--clean]

Options:
    --clean     Force rebuild of the emulation folder
"""

import os
import sys
import shutil
import argparse
from pathlib import Path


def get_project_root():
    """Get the project root directory (parent of scripts folder)."""
    return Path(__file__).parent.parent.resolve()


def setup_emulation_folder(project_root: Path, force_clean: bool = False):
    """
    Create the build/emulation folder with patched source code.

    This copies the src/seedsigner folder and applies emulator patches.
    """
    build_dir = project_root / "build" / "emulation"
    src_dir = project_root / "src"
    emulator_dir = project_root / "emulator"

    # Check if we need to rebuild
    if build_dir.exists():
        if force_clean:
            print("Cleaning existing build/emulation folder...")
            shutil.rmtree(build_dir)
        else:
            print("Using existing build/emulation folder. Use --clean to rebuild.")
            return build_dir

    print("Setting up emulation environment...")

    # Create build directory
    build_dir.mkdir(parents=True, exist_ok=True)

    # Copy the entire src folder
    print("  Copying source files...")
    src_dest = build_dir / "seedsigner"
    if (src_dir / "seedsigner").exists():
        shutil.copytree(src_dir / "seedsigner", src_dest)
    else:
        print(f"Error: Source folder not found at {src_dir / 'seedsigner'}")
        sys.exit(1)

    # Copy main.py
    main_src = src_dir / "main.py"
    if main_src.exists():
        shutil.copy(main_src, build_dir / "main.py")

    # Copy l10n translations folder
    l10n_src = project_root / "l10n"
    if l10n_src.exists():
        print("  Copying translations...")
        l10n_dest = build_dir / "l10n"
        if l10n_dest.exists():
            shutil.rmtree(l10n_dest)
        shutil.copytree(l10n_src, l10n_dest)

    # Create emulator folder in build
    print("  Adding emulator components...")
    emulator_dest = src_dest / "emulator"
    emulator_dest.mkdir(exist_ok=True)

    # Copy emulator core files
    for file in ["desktopDisplay.py", "virtualGPIO.py", "webcamvideostream.py"]:
        src_file = emulator_dir / file
        if src_file.exists():
            shutil.copy(src_file, emulator_dest / file)

    # Create __init__.py for emulator module
    (emulator_dest / "__init__.py").write_text("")

    # Apply patches (replace hardware-specific files)
    print("  Applying emulator patches...")
    patches_dir = emulator_dir / "patches"

    # Patch hardware/buttons.py
    buttons_patch = patches_dir / "buttons.py"
    if buttons_patch.exists():
        shutil.copy(buttons_patch, src_dest / "hardware" / "buttons.py")

    # Patch hardware/camera.py
    camera_patch = patches_dir / "camera.py"
    if camera_patch.exists():
        shutil.copy(camera_patch, src_dest / "hardware" / "camera.py")

    # Patch gui/renderer.py
    renderer_patch = patches_dir / "renderer.py"
    if renderer_patch.exists():
        shutil.copy(renderer_patch, src_dest / "gui" / "renderer.py")

    # Patch hardware/pivideostream.py
    pivideostream_patch = patches_dir / "pivideostream.py"
    if pivideostream_patch.exists():
        shutil.copy(pivideostream_patch, src_dest / "hardware" / "pivideostream.py")

    # Copy emulator icon to resources
    icon_src = emulator_dir / "emulator_icon.png"
    if icon_src.exists():
        icons_dest = src_dest / "resources" / "icons"
        icons_dest.mkdir(parents=True, exist_ok=True)
        shutil.copy(icon_src, icons_dest / "emulator_icon.png")

    print("  Emulation environment ready!")
    return build_dir


def check_dependencies():
    """Check if required dependencies are installed."""
    missing = []

    try:
        import PIL
    except ImportError:
        missing.append("Pillow")

    try:
        import tkinter
    except ImportError:
        missing.append("tkinter (python3-tk)")

    # OpenCV is optional (for camera)
    try:
        import cv2
    except ImportError:
        print("Note: OpenCV not installed. Camera/QR scanning will be disabled.")
        print("      Install with: pip install opencv-python")

    if missing:
        print("Error: Missing required dependencies:")
        for dep in missing:
            print(f"  - {dep}")
        print("\nInstall with:")
        print("  pip install Pillow")
        print("  sudo apt-get install python3-tk  # On Debian/Ubuntu")
        sys.exit(1)


def run_emulator(build_dir: Path):
    """Run the emulator."""
    print("\nStarting Cardano SeedSigner Emulator...")
    print("=" * 60)
    print("Controls:")
    print("  Arrow Keys  : Navigate (Up/Down/Left/Right)")
    print("  Enter       : Select/Press")
    print("  1, 2, 3     : Side buttons")
    print("=" * 60)
    print()

    # Change to build directory
    os.chdir(build_dir)

    # Add build directory to Python path
    sys.path.insert(0, str(build_dir))

    # Import and run main
    try:
        # Import main module and call main()
        import main
        main.main([])
    except Exception as e:
        print(f"Error starting emulator: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Cardano SeedSigner Desktop Emulator"
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Force rebuild of the emulation folder"
    )
    args = parser.parse_args()

    project_root = get_project_root()

    print("Cardano SeedSigner Emulator")
    print("Based on seedsigner-emulator by @EnteroPositivo")
    print()

    # Check dependencies
    check_dependencies()

    # Setup emulation folder
    build_dir = setup_emulation_folder(project_root, force_clean=args.clean)

    # Run emulator
    run_emulator(build_dir)


if __name__ == "__main__":
    main()
