<p align="center">
  <img align="middle" src=
  "assets/ada_seed_signer_logo.png"
  height="160" />
</p>


# Cardano SeedSigner

Use an air-gapped Raspberry Pi Zero to sign for Cardano transactions

# Project Summary

The goal of Cardano SeedSigner is to reduce the cost and operational complexity of using Cardano wallets. To achieve this, SeedSigner enables users to build a verifiably air-gapped, stateless Cardano signing device using inexpensive, widely available hardware components—typically costing less than $50.

Cardano SeedSigner supports trustless private key generation and secure transaction authorization by relying exclusively on an offline execution model and a QR-based data exchange mechanism. This design eliminates network connectivity and persistent secret storage, allowing users to sign Cardano transactions and messages without exposing private key material to online systems.

Additional information about the SeedSigner project is available at https://seedsigner.com

Cardano SeedSigner is a forked and derivative work based on the original SeedSigner project developed by the SeedSigner contributors and available at
https://github.com/SeedSigner/seedsigner

# SeedSigner OS

This repository contains the Cardano SeedSigner **application**. The operating system it runs on lives in a separate repository:

**https://github.com/Biglup/cardano-seedsigner-os**

Cardano SeedSigner OS is a [Buildroot](https://www.buildroot.org)-based Linux image, hardened and stripped down to the bare minimum needed to run the signing application. It is an order of magnitude smaller than Raspberry Pi OS and:

- Boots 100% from RAM — once the splash screen appears, the microSD card can be removed
- Ships as a single read-only image (kernel + filesystem) on one FAT32 partition
- Removes networking, Bluetooth, USB, serial, I2C, SWAP, and PWM kernel modules
- Has no HDMI or serial TTL support, and no software for any wireless or networking chips
- Bundles `libcardano-c` and `cometa` as proper Buildroot packages

# Development Setup

To run the application on your desktop (no Raspberry Pi hardware needed), use the Tkinter-based emulator:

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Launch the desktop emulator (requires Tkinter, e.g. apt install python3-tk)
python scripts/emulate.py                           # 240x240 (default)
python scripts/emulate.py --display st7789_320x240  # larger screen variant

# Run the test suite
pip install pytest && pytest tests/
```

The Tools menu includes mock transaction and message data for rapid prototyping without QR scanning.

## Iterating on real hardware

For faster iteration on a real device, build a **dev image** once — it bakes in all dependencies but loads the application source from the SD card's FAT partition:

```bash
./scripts/build-dev-image.sh pi0     # or pi02w | pi2 | pi4
# Flash the image, then after each code change:
./scripts/copy-to-sdcard.sh /media/$USER/CARDANOSSOS
```

Edit code, re-copy `src/`, and reboot the Pi to test.

# Building a Full Image

To build a bootable, production SD card image (requires Docker, ~20–30 GB of disk space, and roughly an hour on first run):

```bash
./scripts/build-image.sh pi0         # or pi02w | pi2 | pi4
```

The script clones [cardano-seedsigner-os](https://github.com/Biglup/cardano-seedsigner-os) into a sibling directory (`../cardano-seedsigner-os`), copies this repository's `src/` into the OS rootfs overlay, and runs the Buildroot cross-compilation inside Docker. The finished image lands in `../cardano-seedsigner-os/images/` and can be flashed with:

```bash
sudo dd if=../cardano-seedsigner-os/images/cardano_seedsigner_os.<tag>.<board>.img of=/dev/sdX bs=4M status=progress && sync
```

See the [OS repository's build documentation](https://github.com/Biglup/cardano-seedsigner-os/blob/main/docs/building.md) for board configs and reproducible-build details.

# Attribution and License Notice

This project builds upon the [SeedSigner](https://github.com/SeedSigner/seedsigner) codebase, architecture, and design principles, extending them to support the Cardano blockchain while preserving the original project’s air-gapped security model and hardware abstractions.

The original SeedSigner project is licensed under the MIT License, and this project complies fully with the terms of that license. All applicable copyright notices, license text, and attribution are retained in accordance with MIT licensing requirements. No endorsement by the original SeedSigner authors is implied.
