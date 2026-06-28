#!/usr/bin/env python3
"""STEP 1 of the air-gapped flow: request an account public key from the device.

The companion sends an animated ``cardano-account-req`` QR; the device shows the
account/derivation path, the user approves, and the device returns an animated
``cardano-account`` QR carrying the account xpub + master fingerprint. From that
the companion derives the wallet's address — with no private keys.

    # offline, against the in-process device simulator:
    python examples/request_account_key.py --simulator

    # against real hardware over QR (needs a webcam + the demo extras):
    python examples/request_account_key.py
"""

import argparse

from cometa import NetworkId

from companion.device import SimulatedDevice, HardwareDevice
from companion.flows import request_account
from companion import console as ui

DEFAULT_MNEMONIC = (
    "abandon abandon abandon abandon abandon abandon abandon abandon "
    "abandon abandon abandon about"
)


def build_device(args):
    if args.simulator:
        return SimulatedDevice(args.mnemonic, passphrase=args.passphrase)
    return HardwareDevice(max_fragment_len=args.fragment, fps=args.fps,
                          camera=args.camera, width=args.width, height=args.height,
                          focus=args.focus)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--simulator", action="store_true", help="use the in-process device simulator")
    parser.add_argument("--mnemonic", default=DEFAULT_MNEMONIC, help="simulator seed mnemonic")
    parser.add_argument("--passphrase", default="", help="simulator seed passphrase")
    parser.add_argument("--account", type=int, default=0, help="CIP-1852 account index")
    parser.add_argument("--mainnet", action="store_true", help="derive a mainnet address")
    parser.add_argument("--fragment", type=int, default=90, help="max UR fragment length (hardware)")
    parser.add_argument("--fps", type=float, default=6.0, help="animated QR frames/sec (hardware)")
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--focus", type=int, default=None, help="manual focus 0-255 (omit for autofocus)")
    args = parser.parse_args()

    network = NetworkId.MAINNET if args.mainnet else NetworkId.TESTNET
    device = build_device(args)

    ui.step(1, 1, "Export Extended Account Key")
    ui.action("Scan the request QR with the device, then approve the export on the device")
    wallet, response, _ = request_account(device, account_index=args.account, network=network)
    ui.ok("Received account extended public key (watch-only, no private keys)")

    ui.result("device label", response.device_label)
    ui.result("master fingerprint", response.master_fingerprint.hex())
    ui.result("account index", args.account)
    ui.result("account xpub", wallet.account_xpub.to_bytes().hex())
    ui.result("network", "mainnet" if args.mainnet else "testnet/preprod")
    ui.result("base address", wallet.address_bech32())
    ui.result("enterprise address", wallet.enterprise_address().to_bech32())
    ui.result("reward address", wallet.reward_address().to_bech32())


if __name__ == "__main__":
    main()
