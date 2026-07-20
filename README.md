<p align="center">
  <img align="middle" src=
  "assets/ada_seed_signer_logo.png"
  height="160" />
</p>


# Cardano SeedSigner

Use an air-gapped Raspberry Pi Zero to sign Cardano transactions and messages.

[![Latest release](https://img.shields.io/github/v/release/Biglup/cardano-seedsigner?sort=semver&label=latest%20release)](https://github.com/Biglup/cardano-seedsigner/releases/latest)
[![License: MIT](https://img.shields.io/github/license/Biglup/cardano-seedsigner)](https://github.com/Biglup/cardano-seedsigner/blob/main/LICENSE)

# Project Summary

Cardano SeedSigner lowers the cost and the operational complexity of holding Cardano keys offline. You build a stateless, air-gapped signing device out of cheap and widely available parts, usually for less than $50, and it never touches a network or writes a secret to disk.

Keys are generated and transactions are authorized entirely offline. Data in and out goes through QR codes, so there is no USB, no Bluetooth and no networking involved at any point, and private key material never leaves the device.

There is more about the upstream project at https://seedsigner.com. Cardano SeedSigner is a fork and derivative work based on SeedSigner (https://github.com/SeedSigner/seedsigner), adapted for Cardano.

# What it does

- Generate a BIP-39 seed phrase (12, 15 or 24 words) from dice rolls or camera entropy
- Load a seed instantly from a SeedQR or CompactSeedQR
- Export an account public key so a watch-only wallet can derive and track addresses
- Review and sign Cardano transactions received as animated QR codes (UR)
- Sign CIP-8 messages for a payment address, a stake address or a DRep credential
- Explore the payment addresses, the stake address and the DRep ID of a loaded seed
- Multisig signing following CIP-1854
- Mainnet and preprod/testnet

The device is stateless and holds nothing between reboots. Once the splash screen shows you can pull the microSD card out, since everything runs from RAM.

# Hardware

The parts list is the same as a standard SeedSigner build:

- Raspberry Pi Zero. The v1.3 has no wireless chip at all, which is what you want, but the Zero W, Zero 2 W and Pi 2/3/4 work too
- Waveshare 1.3 inch 240x240 pixel LCD HAT
- A Pi Zero compatible camera, an OV5647 based 5MP module works well

You either solder the 40 GPIO pins or use solderless hammer headers, and the screen has to be exactly 240x240.

# Download and verify

Get the image for your board from the [latest release](https://github.com/Biglup/cardano-seedsigner/releases/latest). Each release ships one image per board plus the files you need to verify it. The table below is regenerated automatically on every release.

<!-- BEGIN DOWNLOAD TABLE -->
Latest release: **[v1.1.0](https://github.com/Biglup/cardano-seedsigner/releases/tag/v1.1.0)**

| Board | Image | Signature |
|-------|-------|-----------|
| Raspberry Pi Zero 1.3 | [cardano_seedsigner_os.v1.1.0.pi0.img](https://github.com/Biglup/cardano-seedsigner/releases/download/v1.1.0/cardano_seedsigner_os.v1.1.0.pi0.img) | [.asc](https://github.com/Biglup/cardano-seedsigner/releases/download/v1.1.0/cardano_seedsigner_os.v1.1.0.pi0.img.asc) |
| Raspberry Pi Zero W | [cardano_seedsigner_os.v1.1.0.pi0.img](https://github.com/Biglup/cardano-seedsigner/releases/download/v1.1.0/cardano_seedsigner_os.v1.1.0.pi0.img) | [.asc](https://github.com/Biglup/cardano-seedsigner/releases/download/v1.1.0/cardano_seedsigner_os.v1.1.0.pi0.img.asc) |
| Raspberry Pi Zero 2 W | [cardano_seedsigner_os.v1.1.0.pi02w.img](https://github.com/Biglup/cardano-seedsigner/releases/download/v1.1.0/cardano_seedsigner_os.v1.1.0.pi02w.img) | [.asc](https://github.com/Biglup/cardano-seedsigner/releases/download/v1.1.0/cardano_seedsigner_os.v1.1.0.pi02w.img.asc) |
| Raspberry Pi 1 Model B/B+ (*) | [cardano_seedsigner_os.v1.1.0.pi0.img](https://github.com/Biglup/cardano-seedsigner/releases/download/v1.1.0/cardano_seedsigner_os.v1.1.0.pi0.img) | [.asc](https://github.com/Biglup/cardano-seedsigner/releases/download/v1.1.0/cardano_seedsigner_os.v1.1.0.pi0.img.asc) |
| Raspberry Pi 2 Model B | [cardano_seedsigner_os.v1.1.0.pi2.img](https://github.com/Biglup/cardano-seedsigner/releases/download/v1.1.0/cardano_seedsigner_os.v1.1.0.pi2.img) | [.asc](https://github.com/Biglup/cardano-seedsigner/releases/download/v1.1.0/cardano_seedsigner_os.v1.1.0.pi2.img.asc) |
| Raspberry Pi 3 Model B/B+ | [cardano_seedsigner_os.v1.1.0.pi02w.img](https://github.com/Biglup/cardano-seedsigner/releases/download/v1.1.0/cardano_seedsigner_os.v1.1.0.pi02w.img) | [.asc](https://github.com/Biglup/cardano-seedsigner/releases/download/v1.1.0/cardano_seedsigner_os.v1.1.0.pi02w.img.asc) |
| Raspberry Pi 4 Model B | [cardano_seedsigner_os.v1.1.0.pi4.img](https://github.com/Biglup/cardano-seedsigner/releases/download/v1.1.0/cardano_seedsigner_os.v1.1.0.pi4.img) | [.asc](https://github.com/Biglup/cardano-seedsigner/releases/download/v1.1.0/cardano_seedsigner_os.v1.1.0.pi4.img.asc) |
| Checksums (all images) | [SHA256SUMS](https://github.com/Biglup/cardano-seedsigner/releases/download/v1.1.0/SHA256SUMS) | [SHA256SUMS.asc](https://github.com/Biglup/cardano-seedsigner/releases/download/v1.1.0/SHA256SUMS.asc) |

(*) The Pi 1 needs a hardware modification to the Waveshare LCD HAT, see the [upstream legacy hardware notes](https://github.com/SeedSigner/seedsigner/blob/dev/docs/legacy_hardware.md).
<!-- END DOWNLOAD TABLE -->

Running a prepared image means trusting whoever built it. The releases are signed so you can at least confirm the image is the one that was published, and the builds are reproducible so you can rebuild from source and compare hashes (see [Building a Full Image](#building-a-full-image)).

## Verify the signature

A release contains the images, a detached `.img.asc` signature for each, and `SHA256SUMS` with its signature `SHA256SUMS.asc`. The signing key is not in the release: you fetch it from Keybase, where it is tied to a verified identity, and confirm its fingerprint there. That fingerprint check is what everything else rests on.

1. Fetch the key from Keybase:

   ```
   gpg --fetch-keys https://keybase.io/angelcastillob/pgp_keys.asc
   ```

2. Confirm its fingerprint against the one shown at https://keybase.io/angelcastillob:

   ```
   gpg --fingerprint "Cardano SeedSigner Release Signing"
   ```

   It should read `D8DA 9735 E65D 412F E8ED  2038 48A1 F6D6 07ED E9F9`.

3. Verify the signature over the checksums, then check your image against them:

   ```
   gpg --verify SHA256SUMS.asc SHA256SUMS
   sha256sum --ignore-missing --check SHA256SUMS      # use: shasum -a 256 ... on macOS
   ```

   The first command should print `Good signature`, the second `OK` for your image.

To check an image directly against its own signature instead:

```
gpg --verify cardano_seedsigner_os.<version>.<board>.img.asc cardano_seedsigner_os.<version>.<board>.img
```

This only shows the image was signed by the holder of that key, so it is worth checking the fingerprint out of band, and it is only as good as the private key not being compromised.

## Write it to the microSD card

Any of these work:

- Balena Etcher (Windows, macOS, Linux), verifies the write for you
- Raspberry Pi Imager (Windows, macOS, Linux), also verifies
- `dd`, on Linux or macOS if you are comfortable with it:

  ```
  sudo dd if=cardano_seedsigner_os.<version>.<board>.img of=/dev/sdX bs=4M status=progress && sync
  ```

  Make sure `/dev/sdX` is the card and not one of your own disks.

# SeedSigner OS

This repository contains the Cardano SeedSigner **application**. The operating system it runs on lives in a separate repository:

**https://github.com/Biglup/cardano-seedsigner-os**

Cardano SeedSigner OS is a [Buildroot](https://www.buildroot.org)-based Linux image, hardened and stripped down to the bare minimum needed to run the signing application. It is an order of magnitude smaller than Raspberry Pi OS and:

- Boots 100% from RAM, so once the splash screen appears the microSD card can be removed
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

For faster iteration on a real device, build a **dev image** once. It bakes in all dependencies but loads the application source from the SD card's FAT partition:

```bash
./scripts/build-dev-image.sh pi0     # or pi02w | pi2 | pi4
# Flash the image, then after each code change:
./scripts/copy-to-sdcard.sh /media/$USER/CARDANOSSOS
```

Edit code, re-copy `src/`, and reboot the Pi to test.

# Building a Full Image

To build a bootable, production SD card image (requires Docker, 20 to 30 GB of free disk space, and roughly an hour on the first run):

```bash
./scripts/build-image.sh pi0         # or pi02w | pi2 | pi4
```

The script clones [cardano-seedsigner-os](https://github.com/Biglup/cardano-seedsigner-os) into a sibling directory (`../cardano-seedsigner-os`), copies this repository's `src/` into the OS rootfs overlay, and runs the Buildroot cross-compilation inside Docker. The finished image lands in `../cardano-seedsigner-os/images/` and can be flashed with:

```bash
sudo dd if=../cardano-seedsigner-os/images/cardano_seedsigner_os.<tag>.<board>.img of=/dev/sdX bs=4M status=progress && sync
```

The build is reproducible, so you can build the image yourself and compare its `sha256sum` against the one published in the release to confirm they match. See the [OS repository's build documentation](https://github.com/Biglup/cardano-seedsigner-os/blob/main/docs/building.md) for board configs and reproducible-build details.

# Attribution and License Notice

This project builds upon the [SeedSigner](https://github.com/SeedSigner/seedsigner) codebase, architecture, and design principles, extending them to support the Cardano blockchain while preserving the original project's air-gapped security model and hardware abstractions.

The original SeedSigner project is licensed under the MIT License, and this project complies fully with the terms of that license. All applicable copyright notices, license text, and attribution are retained in accordance with MIT licensing requirements. No endorsement by the original SeedSigner authors is implied.
