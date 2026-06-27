# Cardano SeedSigner — Host Companion (air-gapped demo)

A watch-only host companion that drives the full air-gapped signing loop with a
Cardano SeedSigner device, over animated QR codes:

1. **Request the account key** — the device exports its account xpub + master
   fingerprint (`cardano-account` UR). No private keys ever leave the device.
2. **Derive the wallet** — the companion soft-derives payment/stake keys and
   addresses from the account xpub (watch-only).
3. **Build** a transaction (Blockfrost preprod) or a CIP-8 message.
4. **Hand it to the device** as an animated `cardano-tx-sig-req` /
   `cardano-cip8-sig-req` QR.
5. **Collect the result** — the device reviews, signs, and returns an animated
   `cardano-tx-sig-res` (witness set) / `cardano-cip8-sig-res` (COSE) QR.
6. **Apply + broadcast** the transaction, or **verify** the message signature.

The companion reuses the device's own UR transport and CBOR codecs
(`seedsigner.helpers.ur2`, `seedsigner.models.cardano_*`) so the two sides can
never drift on the wire format.

## Two modes

- `--simulator` runs an **in-process device** (`companion.SimulatedDevice`) that
  executes the real on-device signing core from a known mnemonic. No hardware,
  webcam, or network needed (except Blockfrost for the tx flow). This is how the
  scripts are tested and how you validate the flow before touching hardware.
- Default (no `--simulator`) talks to a **real SeedSigner** in a single Tkinter
  window: the request QR animates on the **left** while the **right** shows the
  live webcam watching for the device's animated QR response (modelled on
  `scripts/cardano_companion_test.py`). Tkinter is used instead of OpenCV's GUI
  so it works with headless OpenCV builds. Press `q`/`Esc` to abort.

  Hardware tuning flags (all scripts): `--camera N` (webcam index),
  `--width/--height` (capture resolution — higher reads dense QRs better),
  `--focus 0-255` (manual focus; omit for autofocus), `--fps`, `--fragment`.
  Run it WITHOUT `sudo` and make sure you're in the `video` group.

## Install

```
pip install -r examples/requirements.txt   # cbor2 (+ opencv/pyzbar/qrcode for hardware)
pip install biglup-cometa                  # if cometa isn't already importable
```

## Scripts

```
# STEP 1 only — export the account key and show derived addresses
python examples/request_account_key.py --simulator

# CIP-8 message signing, fully offline, with external COSE verification
python examples/sign_message_e2e.py --simulator --message "Hello, Cardano!" \
    --evidence-dir ./evidence

# Sign the same message with the payment, stake AND DRep keys in one run
# (--credential payment | stake | drep | all ; default payment)
python examples/sign_message_e2e.py --simulator --credential all \
    --message "Hello, Cardano!" --evidence-dir ./evidence

# Transaction signing on preprod (needs a Blockfrost project id; --broadcast to submit)
export BLOCKFROST_PROJECT_ID=preprod...
python examples/sign_tx_e2e.py --to addr_test1... --lovelace 2000000 \
    --evidence-dir ./evidence            # add --broadcast to submit, drop --simulator for hardware
```

Each `*_e2e` script writes the request and result CBOR to `--evidence-dir` as
`.txt` files for the milestone evidence.

## Layout

```
examples/
  request_account_key.py     STEP 1 demo
  sign_message_e2e.py        CIP-8 end-to-end (+ verify)
  sign_tx_e2e.py             transaction end-to-end (+ broadcast)
  test_companion.py          offline e2e tests (pytest)
  companion/
    device.py                SimulatedDevice / HardwareDevice (exchange API)
    transport.py             animated-QR display + webcam scan (hardware)
    messages.py              build/parse the six UR messages (reuses device codecs)
    wallet.py                watch-only wallet from an account xpub
    cip8_verify.py           external COSE_Sign1 verification (cbor2 + Ed25519)
    flows.py                 STEP 1 helper
```

## Notes

- The transaction flow needs real preprod UTXOs, so a Blockfrost project id is
  required; `--broadcast` additionally needs the wallet address to be funded.
  The `--simulator` abandon-seed address will not be funded on preprod.
- cometa exposes CIP-8 signing but no verification, so `cip8_verify.py`
  reconstructs the COSE `Sig_structure` and checks the Ed25519 signature itself.
