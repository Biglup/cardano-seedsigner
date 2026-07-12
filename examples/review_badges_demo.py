#!/usr/bin/env python3
"""Exercises every ownership badge on the review screens.

Builds one hand-crafted transaction per case — collateral return (own and
foreign variants), certificate credentials (stake registration / stake
delegation / DRep registration, plus a foreign one), withdrawals, required
signers, and DRep votes — each mixing the wallet's own credentials with
foreign ones, and sends each to the device as a normal ``cardano-tx-sig-req``
so the review screens can be checked visually:

* Collateral Return  -> green "Address (Own):" + "Verified Address" badge,
                        or red "Address (Foreign):" with no badge
* Certificates       -> "Own Key" / "Unknown Key" badge under each credential
* Withdrawals        -> "Own Reward Account" / "Unknown Reward Account" badge
* Required Signers   -> "Own Key" / "Unknown Key" badge
* Votes              -> "Own Key" / "Unknown Key" badge under the DRep voter

Fully offline: no Blockfrost, no broadcast, inputs are fake. With --simulator
the in-process device signs blind (no GUI), so the script instead verifies the
badge flags with the real device-side helpers and checks the witnesses.

    python examples/review_badges_demo.py --simulator
    python examples/review_badges_demo.py --scenario collateral-return
"""

import argparse

from cometa import CborWriter, NetworkId

from companion.device import SimulatedDevice, HardwareDevice
from companion.flows import request_account, new_request_id
from companion import messages
from companion import console as ui

from seedsigner.models.cardano_tx import (
    CardanoSignRequest,
    SigningInput,
    ExtraSigner,
)

DEFAULT_MNEMONIC = (
    "abandon abandon abandon abandon abandon abandon abandon abandon "
    "abandon abandon abandon about"
)
ZERO_TX_HASH = b"\x00" * 32
FOREIGN_ADDR = bytes.fromhex("60" + "11" * 28)
FOREIGN_KEY_HASH = b"\x22" * 28
FAKE_POOL_KEY_HASH = b"\x33" * 28
FAKE_GOV_ACTION_TX = b"\x44" * 32
FEE = 180_000


def build_device(args):
    if args.simulator:
        return SimulatedDevice(args.mnemonic, passphrase=args.passphrase)
    return HardwareDevice(max_fragment_len=args.fragment, fps=args.fps,
                          camera=args.camera, width=args.width, height=args.height,
                          focus=args.focus)


def _write_output(w, addr_bytes, coin):
    w.write_start_array(2)
    w.write_bytes(addr_bytes)
    w.write_int(coin)


def _body(wallet, certificates=None, withdrawals=None, required_signers=None,
          voters=None, collateral_return_coin=None,
          collateral_return_foreign=False) -> bytes:
    """A minimal valid tx body: one fake input, one foreign output, a fee,
    plus whichever optional sections the scenario needs.

    `withdrawals` is a list of (reward_address_bytes, coin); `voters` a list
    of DRep voter key hashes.
    """
    sections = 3
    for present in (certificates, withdrawals, required_signers, voters,
                    collateral_return_coin):
        if present is not None:
            sections += 1
    if collateral_return_coin is not None:
        sections += 2  # collateral inputs (13) + total collateral (17)

    w = CborWriter()
    w.write_start_map(sections)

    w.write_int(0)
    w.write_start_array(1)
    w.write_start_array(2)
    w.write_bytes(ZERO_TX_HASH)
    w.write_int(0)

    w.write_int(1)
    w.write_start_array(1)
    _write_output(w, FOREIGN_ADDR, 1_000_000)

    w.write_int(2)
    w.write_int(FEE)

    if certificates is not None:
        w.write_int(4)
        w.write_start_array(len(certificates))
        for cert in certificates:
            cert(w)

    if withdrawals is not None:
        w.write_int(5)
        w.write_start_map(len(withdrawals))
        for reward_addr_bytes, coin in withdrawals:
            w.write_bytes(reward_addr_bytes)
            w.write_int(coin)

    if collateral_return_coin is not None:
        w.write_int(13)
        w.write_start_array(1)
        w.write_start_array(2)
        w.write_bytes(ZERO_TX_HASH)
        w.write_int(1)

        w.write_int(16)
        return_addr = FOREIGN_ADDR if collateral_return_foreign else wallet.base_address_bytes()
        _write_output(w, return_addr, collateral_return_coin)

        w.write_int(17)
        w.write_int(2_000_000)

    if required_signers is not None:
        w.write_int(14)
        w.write_start_array(len(required_signers))
        for key_hash in required_signers:
            w.write_bytes(key_hash)

    if voters is not None:
        w.write_int(19)
        w.write_start_map(len(voters))
        for voter_key_hash in voters:
            w.write_start_array(2)
            w.write_int(2)  # voter: DRep key hash
            w.write_bytes(voter_key_hash)
            w.write_start_map(1)
            w.write_start_array(2)
            w.write_bytes(FAKE_GOV_ACTION_TX)
            w.write_int(0)
            w.write_start_array(2)
            w.write_int(1)  # vote: yes
            w.write_null()

    return w.encode()


def _key_hash_credential(w, key_hash):
    w.write_start_array(2)
    w.write_int(0)
    w.write_bytes(key_hash)


def _stake_registration(wallet):
    def write(w):
        w.write_start_array(2)
        w.write_int(0)
        _key_hash_credential(w, bytes.fromhex(wallet.stake_key_hash_hex()))
    return write


def _stake_delegation(wallet):
    def write(w):
        w.write_start_array(3)
        w.write_int(2)
        _key_hash_credential(w, bytes.fromhex(wallet.stake_key_hash_hex()))
        w.write_bytes(FAKE_POOL_KEY_HASH)
    return write


def _drep_registration(wallet):
    def write(w):
        w.write_start_array(4)
        w.write_int(16)
        _key_hash_credential(w, wallet.drep_credential_bytes())
        w.write_int(500_000_000)
        w.write_null()
    return write


def _foreign_stake_registration():
    def write(w):
        w.write_start_array(2)
        w.write_int(0)
        _key_hash_credential(w, FOREIGN_KEY_HASH)
    return write


def _request(wallet, sign_data, extra_paths=(), collateral_return=False):
    return CardanoSignRequest(
        request_id=new_request_id(),
        origin="BadgeDemo",
        sign_data=sign_data,
        inputs=[SigningInput(tx_hash=ZERO_TX_HASH, index=0,
                             xfp=wallet.master_fingerprint,
                             path=wallet.payment_signing_path())],
        change_outputs=[],
        network=NetworkId.TESTNET,
        extra_signers=[ExtraSigner(xfp=wallet.master_fingerprint, path=list(p))
                       for p in extra_paths],
        collateral_return_path=ExtraSigner(
            xfp=wallet.master_fingerprint,
            path=wallet.payment_signing_path()) if collateral_return else None,
    )


def build_scenarios(wallet):
    foreign_reward_account = b"\xe0" + FOREIGN_KEY_HASH
    return [
        (
            "collateral-return",
            _request(wallet, _body(wallet, collateral_return_coin=5_000_000),
                     collateral_return=True),
            ['Collateral Return page: green "Address (Own):" + "Verified Address" badge'],
        ),
        (
            "collateral-return-foreign",
            _request(wallet, _body(wallet, collateral_return_coin=5_000_000,
                                   collateral_return_foreign=True)),
            ['Collateral Return page: red "Address (Foreign):", no badge'],
        ),
        (
            "certificates",
            _request(
                wallet,
                _body(wallet, certificates=[
                    _stake_registration(wallet),
                    _stake_delegation(wallet),
                    _drep_registration(wallet),
                    _foreign_stake_registration(),
                ]),
                extra_paths=[wallet.stake_signing_path(), wallet.drep_signing_path()],
            ),
            ['Certificate 1/4 (Stake Registration): green check "Own Key" under the credential',
             'Certificate 2/4 (Stake Delegation): green check "Own Key" under the credential, pool unbadged',
             'Certificate 3/4 (DRep Registration): green check "Own Key" under the DRep ID',
             'Certificate 4/4 (Stake Registration): red "Unknown Key" under the credential'],
        ),
        (
            "withdrawal",
            _request(wallet, _body(wallet, withdrawals=[
                (wallet.reward_address_bytes(), 3_000_000),
                (foreign_reward_account, 1_000_000),
            ]), extra_paths=[wallet.stake_signing_path()]),
            ['Withdrawal 1/2: green check "Own Reward Account" badge',
             'Withdrawal 2/2: red "Unknown Reward Account" text'],
        ),
        (
            "required-signers",
            _request(wallet, _body(wallet, required_signers=[
                bytes.fromhex(wallet.payment_key_hash_hex()),
                FOREIGN_KEY_HASH,
            ])),
            ['Required Signer 1/2 (wallet key): green check "Own Key" badge',
             'Required Signer 2/2 (foreign key): red "Unknown Key" text'],
        ),
        (
            "voting",
            _request(wallet, _body(wallet, voters=[
                wallet.drep_credential_bytes(),
                FOREIGN_KEY_HASH,
            ]), extra_paths=[wallet.drep_signing_path()]),
            ['Vote 1/2: green check "Own Key" badge under the DRep voter',
             'Vote 2/2: red "Unknown Key" text under the DRep voter'],
        ),
    ]


def check_badges_offline(device, request, name):
    """What the real device will compute for this request (simulator only)."""
    from seedsigner.models.cardano_tx import CardanoParsedTx
    from seedsigner.helpers.cardano_utils import (
        verify_change_outputs,
        verify_collateral_return,
        derive_owned_key_hashes,
    )

    seed = device.seed
    parsed = CardanoParsedTx(request, verified_change_indices=[])
    parsed.verified_change_indices = verify_change_outputs(request, seed, parsed.body)
    parsed.collateral_return_verified = verify_collateral_return(request, seed, parsed.body)
    parsed.owned_key_hashes = derive_owned_key_hashes(request, seed)

    if name == "collateral-return":
        assert parsed.collateral_return_verified, "collateral return did not verify"
    else:
        assert not parsed.collateral_return_verified
    if request.extra_signers or name == "required-signers":
        assert parsed.owned_key_hashes, "no owned key hashes derived"

    pages = parsed.build_review_pages()
    ui.ok(f"device logic: collateral_return_verified={parsed.collateral_return_verified}, "
          f"{len(parsed.owned_key_hashes)} owned key hash(es), {len(pages)} review page(s)")


def verify_witnesses(request, response):
    from cometa import CborReader, TransactionBody, VkeyWitnessSet, Ed25519PublicKey, Ed25519Signature

    if response.request_id != request.request_id:
        raise SystemExit("response request_id does not match the request")
    body = TransactionBody.from_cbor(CborReader.from_bytes(request.sign_data))
    tx_id = body.hash.to_bytes()
    witness_set = VkeyWitnessSet.from_cbor(CborReader.from_bytes(response.vkey_witness_set))
    for witness in witness_set:
        pub = Ed25519PublicKey.from_bytes(witness.vkey)
        if not pub.verify(Ed25519Signature.from_bytes(witness.signature), tx_id):
            raise SystemExit("device returned an invalid signature")
    return len(witness_set)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--simulator", action="store_true")
    parser.add_argument("--mnemonic", default=DEFAULT_MNEMONIC)
    parser.add_argument("--passphrase", default="")
    parser.add_argument("--account", type=int, default=0)
    parser.add_argument("--scenario", default="all",
                        help="all, or one of: collateral-return, "
                             "collateral-return-foreign, certificates, "
                             "withdrawal, required-signers, voting")
    parser.add_argument("--fragment", type=int, default=90)
    parser.add_argument("--fps", type=float, default=6.0)
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--focus", type=int, default=None)
    parser.add_argument("--probe-cameras", action="store_true",
                        help="list working camera indices and exit")
    args = parser.parse_args()

    if args.probe_cameras:
        from companion import transport
        transport.probe_cameras()
        return

    device = build_device(args)

    ui.step(1, 2, "Export Extended Account Key")
    if not args.simulator:
        ui.action("Scan the request QR with the device, then approve the export")
    wallet, _, _ = request_account(device, account_index=args.account,
                                   network=NetworkId.TESTNET)
    ui.ok("Received account extended public key")
    ui.result("wallet address", wallet.address_bech32())

    scenarios = build_scenarios(wallet)
    if args.scenario != "all":
        scenarios = [s for s in scenarios if s[0] == args.scenario]
        if not scenarios:
            raise SystemExit(f"unknown scenario: {args.scenario}")

    ui.step(2, 2, "Review Badge Scenarios")
    for name, request, expected in scenarios:
        print()
        ui.info(f"--- scenario: {name} ---")
        for line in expected:
            ui.info(f"expect: {line}")

        if args.simulator:
            check_badges_offline(device, request, name)

        if not args.simulator:
            ui.action("Scan the transaction QR, step through the review screens "
                      "and check the badges above, then approve")
        response_cbor = device.exchange(messages.UR_TX_SIG_REQ, request.to_cbor(),
                                        messages.UR_TX_SIG_RES)
        response = messages.parse_response(messages.UR_TX_SIG_RES, response_cbor)
        count = verify_witnesses(request, response)
        ui.ok(f"{count} witness signature(s) verified over the tx body hash")


if __name__ == "__main__":
    main()
