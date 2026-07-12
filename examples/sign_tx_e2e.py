#!/usr/bin/env python3
"""End-to-end Cardano transaction signing over animated QR (watch-only host).

Flow: request the account key (STEP 1) -> derive the wallet address -> fetch
preprod UTXOs + params from Blockfrost -> build a send-lovelace transaction
(no private keys) -> send the tx body to the device as an animated
``cardano-tx-sig-req`` -> device reviews + signs -> receive the
``cardano-tx-sig-res`` witness set -> apply it and optionally broadcast. The
request/witness CBOR is written to --evidence-dir.

Requires a Blockfrost preprod project id and (to broadcast) a funded address:

    export BLOCKFROST_PROJECT_ID=preprod...
    python examples/sign_tx_e2e.py --to addr_test1... --lovelace 2000000          # build+sign+apply
    python examples/sign_tx_e2e.py --to addr_test1... --lovelace 2000000 --broadcast

Use --simulator to have the in-process device sign (the abandon-seed address must
be funded on preprod for a real broadcast to succeed).
"""

import argparse
import os

from cometa import (
    NetworkId,
    NetworkMagic,
    BlockfrostProvider,
    TxBuilder,
    SlotConfig,
    CborWriter,
    CborReader,
    VkeyWitnessSet,
    UtxoList,
    Ed25519PublicKey,
    Ed25519Signature,
)

from companion.device import SimulatedDevice, HardwareDevice
from companion.flows import request_account, new_request_id
from companion import messages
from companion import console as ui

from seedsigner.models.cardano_tx import (
    CardanoSignRequest,
    ChangeOutput,
    ExtraSigner,
)

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


def body_cbor(transaction) -> bytes:
    writer = CborWriter()
    transaction.body.to_cbor(writer)
    return writer.encode()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--simulator", action="store_true")
    parser.add_argument("--mnemonic", default=DEFAULT_MNEMONIC)
    parser.add_argument("--passphrase", default="")
    parser.add_argument("--account", type=int, default=0)
    parser.add_argument("--to", required=True, help="recipient address (preprod)")
    parser.add_argument("--lovelace", type=int, default=2_000_000)
    parser.add_argument("--ttl-seconds", type=int, default=7200)
    parser.add_argument("--broadcast", action="store_true", help="submit the signed tx to preprod")
    parser.add_argument("--evidence-dir", default=None, help="write request/response CBOR .txt here")
    parser.add_argument("--fragment", type=int, default=90)
    parser.add_argument("--fps", type=float, default=6.0)
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--focus", type=int, default=None, help="manual focus 0-255 (omit for autofocus)")
    args = parser.parse_args()

    project_id = os.environ.get("BLOCKFROST_PROJECT_ID")
    if not project_id:
        raise SystemExit("Set BLOCKFROST_PROJECT_ID (preprod) to build a real transaction.")

    provider = BlockfrostProvider(network=NetworkMagic.PREPROD, project_id=project_id)
    device = build_device(args)

    ui.step(1, 5, "Export Extended Account Key")
    ui.action("Scan the request QR with the device, then approve the export on the device")
    wallet, _, _ = request_account(device, account_index=args.account, network=NetworkId.TESTNET)
    address = wallet.address_bech32()
    ui.ok("Received account extended public key")
    ui.result("master fingerprint", wallet.master_fingerprint.hex())
    ui.result("wallet address", address)

    ui.step(2, 5, "Build Transaction")
    ui.info("Fetching UTXOs and protocol parameters from Blockfrost (preprod) ...")
    utxos = UtxoList.from_list(provider.get_unspent_outputs(address))
    params = provider.get_parameters()

    builder = TxBuilder(params, SlotConfig.preprod())
    builder.set_utxos(utxos)
    builder.set_change_address(address)
    builder.send_lovelace(address=args.to, amount=args.lovelace)
    builder.expires_in(args.ttl_seconds)
    transaction = builder.build()

    required = transaction.get_unique_signers(utxos)
    paths = wallet.signing_paths_for(required)
    if not paths:
        raise SystemExit("This wallet owns none of the transaction's required signers.")

    # Tell the device which output is change (back to our own address) so it
    # labels it as change and shows the true net send amount, instead of
    # treating it as a foreign send.
    change_outputs = []
    for index, output in enumerate(transaction.body.outputs):
        if str(output.address) == address:
            change_outputs.append(ChangeOutput(
                index=index,
                path=wallet.payment_signing_path(),
                xfp=wallet.master_fingerprint,
            ))

    # Same declaration for the collateral return (tx body key 16), so a
    # Plutus transaction's collateral change is badged as an own address
    # instead of a foreign recipient.
    collateral_return_path = None
    collateral_return = transaction.body.collateral_return
    if collateral_return is not None and str(collateral_return.address) == address:
        collateral_return_path = ExtraSigner(
            xfp=wallet.master_fingerprint,
            path=wallet.payment_signing_path(),
        )

    # Every signer rides in extra_signers: the witness is a signature over the
    # whole body hash regardless of which field declared the path, and this is
    # also how script-locked (multisig) inputs are signed, since they have no
    # single owning key to attach to an input entry.
    request = CardanoSignRequest(
        request_id=new_request_id(),
        origin="Companion",
        sign_data=body_cbor(transaction),
        inputs=[],
        extra_signers=[ExtraSigner(xfp=wallet.master_fingerprint, path=p) for p in paths],
        change_outputs=change_outputs,
        network=NetworkId.TESTNET,
        collateral_return_path=collateral_return_path,
    )
    request_cbor = request.to_cbor()
    ui.ok(f"Built transaction (txid {transaction.id.to_hex()})")
    ui.result("sending", f"{args.lovelace} lovelace to {args.to}")

    ui.step(3, 5, "Sign Transaction on Device")
    ui.action("Scan the transaction QR with the device")
    ui.action("Review the details on the device, approve, then point the webcam at the witness QR")
    response_cbor = device.exchange(messages.UR_TX_SIG_REQ, request_cbor, messages.UR_TX_SIG_RES)
    response = messages.parse_response(messages.UR_TX_SIG_RES, response_cbor)
    ui.ok("Received witness data from the device")

    if response.request_id != request.request_id:
        raise SystemExit("response request_id does not match the request")

    ui.step(4, 5, "Verify and Apply Witness")
    witness_set = VkeyWitnessSet.from_cbor(CborReader.from_bytes(response.vkey_witness_set))
    # Don't broadcast device output blind: every witness must be from a required
    # signer and verify over this transaction's id (the body hash).
    required_hexes = {h.to_hex() for h in required}
    tx_id = transaction.id.to_bytes()
    for witness in witness_set:
        pub = Ed25519PublicKey.from_bytes(witness.vkey)
        if pub.to_hash().to_hex() not in required_hexes:
            raise SystemExit("device returned a witness for a non-required signer")
        if not pub.verify(Ed25519Signature.from_bytes(witness.signature), tx_id):
            raise SystemExit("device returned an invalid signature")

    ui.ok(f"All {len(witness_set)} witness signature(s) verified against the transaction")
    transaction.apply_vkey_witnesses(witness_set)
    signed_cbor = transaction.serialize_to_cbor()
    ui.result("txid", transaction.id.to_hex())

    if args.evidence_dir:
        os.makedirs(args.evidence_dir, exist_ok=True)
        _dump(args.evidence_dir, "tx_sig_req.txt", request_cbor.hex())
        _dump(args.evidence_dir, "tx_sig_res.txt", response.vkey_witness_set.hex())
        _dump(args.evidence_dir, "tx_signed.txt", signed_cbor)
        ui.ok(f"Evidence (request / witness / signed-tx CBOR) written to {args.evidence_dir}")

    ui.step(5, 5, "Broadcast Transaction")
    if args.broadcast:
        ui.info("Submitting the signed transaction to preprod ...")
        tx_id = provider.submit_transaction(signed_cbor)
        ui.ok(f"Submitted: {tx_id}")
        if provider.confirm_transaction(tx_id, 90000):
            ui.ok("Confirmed on-chain")
        else:
            ui.info("[warn] not confirmed within timeout")
    else:
        ui.info("Dry run — re-run with --broadcast to submit to the network")


def _dump(directory, name, text):
    with open(os.path.join(directory, name), "w") as f:
        f.write(text + "\n")


if __name__ == "__main__":
    main()
