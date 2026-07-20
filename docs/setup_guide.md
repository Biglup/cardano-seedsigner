# Setup Guide

This guide takes you from a pile of parts to a working Cardano SeedSigner with a seed loaded. If you already have a device running and want to know how to use it day to day, jump to the [operation guide](operation_guide.md). If you are integrating a wallet with the device, see the [integration guide](integration_guide.md).

## What you need

Same hardware as the original Bitcoin SeedSigner, we didnt change anything on that front:

- A Raspberry Pi. The Pi Zero 1.3 is the recommended board because it has no WiFi/Bluetooth hardware at all, but the Zero W, Zero 2 W and Pi 2/3/4 work too (you can [disable the wireless hardware](https://github.com/DesobedienteTecnologico/rpi_disable_wifi_and_bt_by_hardware) on those if you want).
- A Waveshare 1.3 inch 240x240 LCD HAT. The screen has to be exactly 240x240 for the default display type, tho ST7789 320x240 and ILI9341 panels are also supported under Settings > Hardware.
- A Pi Zero compatible camera. An OV5647 based 5MP module works well, both v1.3 and v2 camera modules are supported.
- A MicroSD card, 8GB is more than enough.

You either solder the 40 GPIO pins or use solderless hammer headers. If you have an old 26-pin Pi 1 laying around, it can work too but needs a hardware modification to the HAT, see [legacy hardware](legacy_hardware.md).

Enclosures are optional but nice, the upstream SeedSigner project maintains several 3D printable designs (Open Pill, Orange Pill, etc.) that fit this build exactly, see their [enclosures folder](https://github.com/SeedSigner/seedsigner/tree/dev/enclosures).

## Get and verify the image

Download the image for your exact board from the [latest release](https://github.com/Biglup/cardano-seedsigner/releases/latest), the download table in the README maps every supported Pi model to its image. Dont guess the image, a Pi 3 needs the pi02w image, not the pi4 one.

Every release ships detached GPG signatures and SHA256SUMS. Please actually verify them, this is a signing device, the whole point is not trusting things blindly. The full walkthrough (fetching the key from Keybase, checking the fingerprint, verifying the signature) is in the [README](https://github.com/Biglup/cardano-seedsigner#verify-the-signature). The builds are also reproducible, so if you want the strongest guarantee you can build from source and compare hashes.

## Flash and first boot

Flash with Raspberry Pi Imager, Etcher, or plain dd:

```bash
sudo dd if=cardano_seedsigner_os.<version>.<board>.img of=/dev/sdX bs=4M status=progress && sync
```

Insert the SD card, connect the camera ribbon, seat the HAT on the GPIO header and power the device over micro USB. First boot takes a few seconds, the OS is a stripped down Buildroot image (no networking stack, no SSH, nothing listening), it boots straight into the app.

First things to do on the device:

1. Settings > I/O Test, press every button and confirm the screen responds. If buttons feel mirrored or rotated your HAT is fine, just check it is seated on the right pins.
2. If you are not on the default 240x240 panel, set Settings > Hardware > Display Type accordingly.
3. If the camera preview shows upside down when you scan something later, change Settings > Camera Rotation (default is 180).

The device is stateless: it keeps no secrets after power off. Settings can optionally persist to the SD card (Settings > Persist Settings), seeds never do.

## Create or load a seed

You have three options:

- **Scan a SeedQR.** If you already have a seed backed up as a [SeedQR or CompactSeedQR](seed_qr/README.md), Scan it from the main menu and it loads straight in.
- **Enter words.** Seeds > Enter 12/15/24-word seed, type the BIP-39 words with the joystick. Tedious but works, the keyboard predicts and narrows as you type.
- **Create a new one on-device.** Tools > New seed, either from camera entropy (a photograph's sensor noise) or from dice rolls (99 rolls for 24 words, 50 for 12). Both flows end with the seed words on screen for you to back up, and optionally a SeedQR you can transcribe by hand onto one of the [printable templates](seed_qr/printable_templates/).

You can add a BIP-39 passphrase before finalizing. Remember the passphrase is part of the wallet identity, same words with a different passphrase is a completely different wallet with a different fingerprint.

When the seed is loaded the device shows its fingerprint (8 hex characters, e.g. `A1B2C3D4`). That fingerprint is how you recognize this seed everywhere: in the seed list, in the account export, and is what wallets echo back in signing requests. Write it down next to your backup, is handy to confirm you restored the right thing.

## Connect a wallet

To use the device with an online wallet you export the account public key: load your seed, Seeds > your seed > Export account key, and scan the animated QR with the host. The host gets the account xpub and the master fingerprint, from those it derives all your addresses (public derivation only, no keys ever leave the device).

If your wallet does not speak the protocol yet, the repo ships a reference companion under `examples/` that does the full flow from the command line, see the [integration guide](integration_guide.md).

Thats it. Day to day usage (signing transactions, signing messages, the review screens and what the badges mean) is covered in the [operation guide](operation_guide.md).
