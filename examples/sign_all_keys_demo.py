#!/usr/bin/env python3
"""Sign with every key purpose and type the device supports.

Exercises the full signing-key matrix in one run:

* purposes: 1852' (ordinary), 1854' (CIP-1854 multisig), 1855' (CIP-1855 policy)
* roles:    payment (0), change (1), stake (2), DRep (3), CC Cold (4), CC Hot (5)

STEP 1 exports the 1852' and 1854' account xpubs so the host can soft-derive
the expected public keys (watch-only). STEP 2 sends ONE transaction sign
request whose extra_signers list every key, so the device pages through a
signing-key inspection screen per key before signing; every witness in the
partial witness set is then verified against the transaction hash and, where
the host can derive it, against the expected public key. STEP 3 repeats the
exercise for CIP-8 message signing, one request per key, each bound to the
key's own hash.

The 1855' policy key path (m/1855'/1815'/account') is hardened end to end, so
a watch-only host cannot predict its public key: its transaction witness is
verified cryptographically only, and it is skipped for CIP-8 (the host cannot
compute the key hash to bind to).

Fully offline: no Blockfrost, no broadcast, the transaction input is fake.

    python examples/sign_all_keys_demo.py --simulator
"""

import argparse

from cometa import (
    CborReader,
    CborWriter,
    Ed25519PublicKey,
    Ed25519Signature,
    NetworkId,
    TransactionBody,
    VkeyWitnessSet,
)

from companion.device import SimulatedDevice, HardwareDevice
from companion.flows import request_account, new_request_id
from companion.cip8_verify import (
    public_key_from_cose_key,
    signed_payload,
    verify_cose_sign1,
)
from companion import messages
from companion import console as ui

from seedsigner.models.cardano_tx import (
    CardanoSignRequest,
    CardanoMessageSignRequest,
    ExtraSigner,
    SigningPath,
)
from seedsigner.helpers.cardano_utils import HARDENED_OFFSET as HARDENED, COIN_TYPE_ADA

DEFAULT_MNEMONIC = (
    "abandon abandon abandon abandon abandon abandon abandon abandon "
    "abandon abandon abandon about"
)
ZERO_TX_HASH = b"\x00" * 32
FOREIGN_ADDR = bytes.fromhex("60" + "11" * 28)


def build_device(args):
    if args.simulator:
        return SimulatedDevice(args.mnemonic, passphrase=args.passphrase)
    return HardwareDevice(max_fragment_len=args.fragment, fps=args.fps,
                          camera=args.camera, width=args.width, height=args.height,
                          focus=args.focus)


def key_matrix(account_index, wallet_1852, wallet_1854):
    """Every (label, path, expected_pubkey) the demo signs with.

    expected_pubkey is soft-derived from the exported account xpub; None when
    the path is hardened beyond the account level (1855' policy key).
    """
    def full_path(purpose, role, index=0):
        return [purpose | HARDENED, COIN_TYPE_ADA | HARDENED,
                account_index | HARDENED, role, index]

    def soft_pubkey(wallet, role, index=0):
        return wallet.account_xpub.derive([role, index]).to_ed25519_key().to_bytes()

    keys = []
    for role, role_word in [(0, "payment"), (1, "payment"), (2, "stake"),
                            (3, "drep"), (4, "cc cold"), (5, "cc hot")]:
        keys.append((f"1852'/{role} {role_word}", full_path(1852, role),
                     soft_pubkey(wallet_1852, role)))
    for role, role_word in [(0, "payment"), (2, "stake")]:
        keys.append((f"1854'/{role} {role_word}", full_path(1854, role),
                     soft_pubkey(wallet_1854, role)))
    keys.append(("1855' policy",
                 [1855 | HARDENED, COIN_TYPE_ADA | HARDENED, account_index | HARDENED],
                 None))
    return keys


def minimal_body() -> bytes:
    """A minimal valid tx body: one fake input, one foreign output, a fee."""
    w = CborWriter()
    w.write_start_map(3)
    w.write_int(0)
    w.write_start_array(1)
    w.write_start_array(2)
    w.write_bytes(ZERO_TX_HASH)
    w.write_int(0)
    w.write_int(1)
    w.write_start_array(1)
    w.write_start_array(2)
    w.write_bytes(FOREIGN_ADDR)
    w.write_int(1_000_000)
    w.write_int(2)
    w.write_int(180_000)
    return w.encode()


def sign_tx_with_all_keys(device, fingerprint, keys) -> bool:
    body = minimal_body()
    request = CardanoSignRequest(
        request_id=new_request_id(),
        origin="Companion",
        sign_data=body,
        inputs=[],
        extra_signers=[ExtraSigner(xfp=fingerprint, path=path) for _, path, _ in keys],
        change_outputs=[],
        network=NetworkId.TESTNET,
    )

    ui.action("Scan the transaction QR with the device")
    ui.action(f"Page through the {len(keys)} signing-key screens, approve, then scan the witness QR")
    response_cbor = device.exchange(messages.UR_TX_SIG_REQ, request.to_cbor(), messages.UR_TX_SIG_RES)
    response = messages.parse_response(messages.UR_TX_SIG_RES, response_cbor)
    if response.request_id != request.request_id:
        ui.info("[FAIL] response request_id does not match the request")
        return False

    witnesses = VkeyWitnessSet.from_cbor(CborReader.from_bytes(response.vkey_witness_set))
    tx_hash = TransactionBody.from_cbor(CborReader.from_bytes(body)).hash.to_bytes()
    ui.ok(f"Received {len(witnesses)} witness(es) for {len(keys)} requested keys")

    by_vkey = {bytes(witness.vkey).hex(): witness for witness in witnesses}
    all_ok = len(witnesses) == len(keys)
    matched_vkeys = set()

    for label, _, expected_pubkey in keys:
        if expected_pubkey is None:
            continue
        witness = by_vkey.get(expected_pubkey.hex())
        if witness is None:
            ui.result(label, "FAIL (no witness for the expected public key)")
            all_ok = False
            continue
        matched_vkeys.add(expected_pubkey.hex())
        pub = Ed25519PublicKey.from_bytes(witness.vkey)
        sig_ok = pub.verify(Ed25519Signature.from_bytes(witness.signature), tx_hash)
        ui.result(label, "signature verified" if sig_ok else "FAIL (bad signature)")
        all_ok &= sig_ok

    for label, _, expected_pubkey in keys:
        if expected_pubkey is not None:
            continue
        unmatched = [w for vkey_hex, w in by_vkey.items() if vkey_hex not in matched_vkeys]
        if len(unmatched) != 1:
            ui.result(label, "FAIL (expected exactly one non-derivable witness)")
            all_ok = False
            continue
        witness = unmatched[0]
        pub = Ed25519PublicKey.from_bytes(witness.vkey)
        sig_ok = pub.verify(Ed25519Signature.from_bytes(witness.signature), tx_hash)
        ui.result(label, ("signature verified (pubkey not derivable watch-only)"
                          if sig_ok else "FAIL (bad signature)"))
        all_ok &= sig_ok

    return all_ok


def sign_message_with_key(device, fingerprint, label, path, expected_pubkey) -> bool:
    key_hash = Ed25519PublicKey.from_bytes(expected_pubkey).to_hash().to_bytes()
    payload = f"CIP-8 with {label} key".encode()

    request = CardanoMessageSignRequest(
        request_id=new_request_id(),
        origin="Companion",
        message_payload=payload,
        required_signing_path=SigningPath(index=0, path=path),
        address_bytes=key_hash,
        xfp=fingerprint,
    )

    ui.action("Scan the message QR with the device, approve, then scan the signature QR")
    response_cbor = device.exchange(messages.UR_CIP8_SIG_REQ, request.to_cbor(), messages.UR_CIP8_SIG_RES)
    response = messages.parse_response(messages.UR_CIP8_SIG_RES, response_cbor)
    if response.request_id != request.request_id:
        ui.result(label, "FAIL (request_id mismatch)")
        return False

    sig_ok = verify_cose_sign1(response.cose_sign1, response.cose_key)
    payload_ok = signed_payload(response.cose_sign1) == payload
    key_ok = public_key_from_cose_key(response.cose_key) == expected_pubkey

    passed = sig_ok and payload_ok and key_ok
    ui.result(label, "VERIFIED" if passed else
              f"FAIL (sig={sig_ok} payload={payload_ok} key={key_ok})")
    return passed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--simulator", action="store_true")
    parser.add_argument("--mnemonic", default=DEFAULT_MNEMONIC)
    parser.add_argument("--passphrase", default="")
    parser.add_argument("--account", type=int, default=0)
    parser.add_argument("--skip-cip8", action="store_true",
                        help="only run the transaction signing step")
    parser.add_argument("--fragment", type=int, default=90)
    parser.add_argument("--fps", type=float, default=6.0)
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--focus", type=int, default=None, help="manual focus 0-255 (omit for autofocus)")
    args = parser.parse_args()

    device = build_device(args)
    total_steps = 2 if args.skip_cip8 else 3

    ui.step(1, total_steps, "Export 1852' and 1854' Account Keys")
    ui.action("Approve both account key exports on the device")
    wallet_1852, _, _ = request_account(device, account_index=args.account,
                                        network=NetworkId.TESTNET, key_purpose=1852)
    wallet_1854, _, _ = request_account(device, account_index=args.account,
                                        network=NetworkId.TESTNET, key_purpose=1854)
    ui.ok("Received both account xpubs (watch-only)")
    ui.result("master fingerprint", wallet_1852.master_fingerprint.hex())

    keys = key_matrix(args.account, wallet_1852, wallet_1854)
    ui.info("Key matrix: " + ", ".join(label for label, _, _ in keys))

    ui.step(2, total_steps, "Sign One Transaction with Every Key")
    tx_ok = sign_tx_with_all_keys(device, wallet_1852.master_fingerprint, keys)
    ui.ok(f"Transaction signing: {'ALL VERIFIED' if tx_ok else 'FAILED'}")

    cip8_ok = True
    if not args.skip_cip8:
        ui.step(3, total_steps, "CIP-8 Sign a Message with Every Derivable Key")
        for label, path, expected_pubkey in keys:
            if expected_pubkey is None:
                ui.info(f"skipping {label}: hardened beyond the account level, "
                        "the watch-only host cannot compute the key hash to bind to")
                continue
            cip8_ok &= sign_message_with_key(
                device, wallet_1852.master_fingerprint, label, path, expected_pubkey)
        ui.ok(f"CIP-8 signing: {'ALL VERIFIED' if cip8_ok else 'FAILED'}")

    if not (tx_ok and cip8_ok):
        raise SystemExit(1)
    ui.ok("All purposes and key types signed and verified")


if __name__ == "__main__":
    main()
