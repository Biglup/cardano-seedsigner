#!/usr/bin/env python3
"""End-to-end CIP-8 message signing over animated QR.

Flow: request the account key (STEP 1) -> derive the signing address -> send an
animated ``cardano-cip8-sig-req`` to the device -> device reviews + signs ->
receive the ``cardano-cip8-sig-res`` (COSE_Sign1 + COSE_Key) -> verify the
signature externally and dump the CBOR as milestone evidence.

    python examples/sign_message_e2e.py --simulator --message "Hello, Cardano!"
    python examples/sign_message_e2e.py   # real hardware over QR
"""

import argparse
import os

from cometa import NetworkId

from companion.device import SimulatedDevice, HardwareDevice
from companion.flows import request_account, new_request_id
from companion import messages
from companion.cip8_verify import verify_cose_sign1, signed_payload, cose_key_hash_hex

from seedsigner.models.cardano_tx import CardanoMessageSignRequest, SigningPath

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
    parser.add_argument("--simulator", action="store_true")
    parser.add_argument("--mnemonic", default=DEFAULT_MNEMONIC)
    parser.add_argument("--passphrase", default="")
    parser.add_argument("--account", type=int, default=0)
    parser.add_argument("--message", default="I attest ownership of this Cardano address.")
    parser.add_argument("--credential", choices=["payment", "stake", "drep", "all"], default="payment",
                        help="which key signs: payment (base addr), stake (reward addr), drep (key hash), or all")
    parser.add_argument("--mainnet", action="store_true")
    parser.add_argument("--evidence-dir", default=None, help="write request/response CBOR .txt here")
    parser.add_argument("--fragment", type=int, default=90)
    parser.add_argument("--fps", type=float, default=6.0)
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--focus", type=int, default=None, help="manual focus 0-255 (omit for autofocus)")
    args = parser.parse_args()

    network = NetworkId.MAINNET if args.mainnet else NetworkId.TESTNET
    device = build_device(args)

    print("STEP 1: requesting account key ...")
    wallet, _, _ = request_account(device, account_index=args.account, network=network)

    credentials = ["payment", "stake", "drep"] if args.credential == "all" else [args.credential]
    payload = args.message.encode("utf-8")

    all_ok = True
    for credential in credentials:
        print("\n" + "#" * 64)
        print(f"# Signing with {credential.upper()} key")
        print("#" * 64)
        all_ok &= sign_one(device, wallet, credential, payload, args.evidence_dir)

    if not all_ok:
        raise SystemExit("VERIFICATION FAILED")
    print("\nALL OK")


def _credential_params(wallet, credential):
    """(signing_path, address_bytes, expected_key_hash_hex, human_description)."""
    if credential == "stake":
        return (wallet.stake_signing_path(), wallet.reward_address_bytes(),
                wallet.stake_key_hash_hex(), f"reward address {wallet.reward_address().to_bech32()}")
    if credential == "drep":
        return (wallet.drep_signing_path(), wallet.drep_credential_bytes(),
                wallet.drep_key_hash_hex(), f"DRep key hash {wallet.drep_key_hash_hex()}")
    return (wallet.payment_signing_path(), wallet.base_address_bytes(),
            wallet.payment_key_hash_hex(), f"base address {wallet.address_bech32()}")


def sign_one(device, wallet, credential, payload, evidence_dir) -> bool:
    """Build, sign, and verify one CIP-8 message for the given credential. Returns
    whether all checks passed."""
    signing_path, address_bytes, expected_hash, bound_to = _credential_params(wallet, credential)
    print(f"  signing with {credential} key, bound to {bound_to}")

    request = CardanoMessageSignRequest(
        request_id=new_request_id(),
        origin="Companion",
        message_payload=payload,
        required_signing_path=SigningPath(index=0, path=signing_path),
        address_bytes=address_bytes,
        xfp=wallet.master_fingerprint,
    )
    request_cbor = request.to_cbor()

    print("  sending message to device for signing ...")
    response_cbor = device.exchange(messages.UR_CIP8_SIG_REQ, request_cbor, messages.UR_CIP8_SIG_RES)
    response = messages.parse_response(messages.UR_CIP8_SIG_RES, response_cbor)

    if response.request_id != request.request_id:
        print("  [FAIL] response request_id does not match the request")
        return False

    ok = verify_cose_sign1(response.cose_sign1, response.cose_key)
    payload_ok = signed_payload(response.cose_sign1) == payload
    key_ok = cose_key_hash_hex(response.cose_key) == expected_hash

    print(f"  cose_sign1 ({len(response.cose_sign1)} bytes): {response.cose_sign1.hex()}")
    print(f"  cose_key   ({len(response.cose_key)} bytes): {response.cose_key.hex()}")
    print(f"  signature valid                : {ok}")
    print(f"  signed payload == sent message : {payload_ok}")
    print(f"  signing key == {credential} key{' ' * (15 - len(credential))}: {key_ok}")

    if evidence_dir:
        os.makedirs(evidence_dir, exist_ok=True)
        _dump(evidence_dir, f"cip8_sig_req_{credential}.txt", request_cbor.hex())
        _dump(evidence_dir, f"cip8_sig_res_{credential}.txt", response_cbor.hex())

    passed = ok and payload_ok and key_ok
    print(f"  -> {credential.upper()}: {'OK' if passed else 'FAILED'}")
    return passed


def _dump(directory, name, text):
    with open(os.path.join(directory, name), "w") as f:
        f.write(text + "\n")


if __name__ == "__main__":
    main()
