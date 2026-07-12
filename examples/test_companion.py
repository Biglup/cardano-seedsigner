"""Offline end-to-end tests for the host companion.

These run the real on-device codecs + signing core through the in-process
``SimulatedDevice`` — no hardware, no webcam, no network — proving the full
request -> sign -> response -> verify loop and that the companion's watch-only
derivation matches the device's signing keys.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pytest

from cometa import NetworkId

from companion.device import SimulatedDevice
from companion.flows import request_account, new_request_id
from companion import messages
from companion.cip8_verify import verify_cose_sign1, signed_payload, cose_key_hash_hex

from seedsigner.models.cardano_tx import CardanoMessageSignRequest, SigningPath


MNEMONIC = (
    "abandon abandon abandon abandon abandon abandon abandon abandon "
    "abandon abandon abandon about"
)
KNOWN_TESTNET_BASE_ADDR = (
    "addr_test1qq8ac7qqy0vtulyl7wntmsxc6wex80gvcyjy33qffrhm7sh927ysx5sftuw0dlft05dz3c7revpf7jx0xnlcjz3g69mqkt5dmn"
)


@pytest.fixture
def device():
    return SimulatedDevice(MNEMONIC)


def test_account_export_derives_known_address(device):
    wallet, response, _ = request_account(device, account_index=0, network=NetworkId.TESTNET)
    assert response.master_fingerprint == bytes.fromhex("73c5da0a")
    assert wallet.address_bech32() == KNOWN_TESTNET_BASE_ADDR


def _credential_params(wallet, credential):
    if credential == "stake":
        return (wallet.stake_signing_path(), wallet.reward_address_bytes(), wallet.stake_key_hash_hex())
    if credential == "drep":
        return (wallet.drep_signing_path(), wallet.drep_credential_bytes(), wallet.drep_key_hash_hex())
    return (wallet.payment_signing_path(), wallet.base_address_bytes(), wallet.payment_key_hash_hex())


@pytest.mark.parametrize("credential", ["payment", "stake", "drep"])
def test_cip8_message_signing_verifies(device, credential):
    wallet, _, _ = request_account(device, account_index=0, network=NetworkId.TESTNET)
    path, address_bytes, expected_hash = _credential_params(wallet, credential)
    payload = b"Hello, Cardano!"
    request = CardanoMessageSignRequest(
        request_id=new_request_id(), origin="Companion",
        message_payload=payload,
        required_signing_path=SigningPath(index=0, path=path),
        address_bytes=address_bytes,
        xfp=wallet.master_fingerprint,
    )
    response_cbor = device.exchange(messages.UR_CIP8_SIG_REQ, request.to_cbor(), messages.UR_CIP8_SIG_RES)
    response = messages.parse_response(messages.UR_CIP8_SIG_RES, response_cbor)

    assert verify_cose_sign1(response.cose_sign1, response.cose_key)
    assert signed_payload(response.cose_sign1) == payload
    # the device signed with the key that owns the host-derived credential
    assert cose_key_hash_hex(response.cose_key) == expected_hash
    assert response.request_id == request.request_id


def test_cip8_self_consistent_signature_from_other_key_is_caught_by_pinning(device):
    """verify_cose_sign1 only proves the signature matches the embedded key, so
    a valid signature made with a different wallet key still passes it; the
    key-hash pinning comparison is what rejects the substitution."""
    wallet, _, _ = request_account(device, account_index=0, network=NetworkId.TESTNET)
    path, address_bytes, _ = _credential_params(wallet, "stake")
    request = CardanoMessageSignRequest(
        request_id=new_request_id(), origin="Companion",
        message_payload=b"Hello, Cardano!",
        required_signing_path=SigningPath(index=0, path=path),
        address_bytes=address_bytes,
        xfp=wallet.master_fingerprint,
    )
    response_cbor = device.exchange(messages.UR_CIP8_SIG_REQ, request.to_cbor(), messages.UR_CIP8_SIG_RES)
    response = messages.parse_response(messages.UR_CIP8_SIG_RES, response_cbor)

    assert verify_cose_sign1(response.cose_sign1, response.cose_key)
    assert cose_key_hash_hex(response.cose_key) != wallet.payment_key_hash_hex()


def test_cip8_wrong_address_is_rejected_by_device(device):
    # Bind the message to a base address but ask the device to sign with the
    # STAKE path: the device must refuse (its address<->key guard), so the
    # companion can never obtain a mis-bound signature.
    wallet, _, _ = request_account(device, account_index=0, network=NetworkId.TESTNET)
    H = 0x80000000
    stake_path = [1852 + H, 1815 + H, 0 + H, 2, 0]
    request = CardanoMessageSignRequest(
        request_id=new_request_id(), origin="Companion",
        message_payload=b"hi",
        required_signing_path=SigningPath(index=0, path=stake_path),
        address_bytes=wallet.base_address_bytes(),
        xfp=wallet.master_fingerprint,
    )
    with pytest.raises(ValueError):
        device.exchange(messages.UR_CIP8_SIG_REQ, request.to_cbor(), messages.UR_CIP8_SIG_RES)


def test_tx_signing_through_simulator(device):
    from cometa import (CborReader, TransactionBody, VkeyWitnessSet,
                        Ed25519PublicKey, Ed25519Signature)
    from seedsigner.models.cardano_tx import CardanoSignRequest, SigningInput

    wallet, _, _ = request_account(device, account_index=0, network=NetworkId.TESTNET)
    body = bytes.fromhex(
        "a3"
        "00" "81" "82" "5820" + "00" * 32 + "00"
        "01" "81" "82" "581d61" + "11" * 28 + "1a000f4240"
        "02" "1a0002bf20"
    )
    request = CardanoSignRequest(
        request_id="tx", origin="Companion", sign_data=body,
        inputs=[SigningInput(tx_hash=b"\x00" * 32, index=0,
                             xfp=wallet.master_fingerprint, path=wallet.payment_signing_path())],
        change_outputs=[], network=NetworkId.TESTNET,
    )
    response_cbor = device.exchange(messages.UR_TX_SIG_REQ, request.to_cbor(), messages.UR_TX_SIG_RES)
    response = messages.parse_response(messages.UR_TX_SIG_RES, response_cbor)
    assert response.request_id == "tx"

    ws = VkeyWitnessSet.from_cbor(CborReader.from_bytes(response.vkey_witness_set))
    assert len(ws) == 1
    tx_hash = TransactionBody.from_cbor(CborReader.from_bytes(body)).hash.to_bytes()
    pub = Ed25519PublicKey.from_bytes(ws[0].vkey)
    assert pub.verify(Ed25519Signature.from_bytes(ws[0].signature), tx_hash)
    # the witness key is the wallet's own payment key
    assert pub.to_hash().to_hex() == wallet.payment_key_hash_hex()


def test_message_request_roundtrips_through_ur(device):
    wallet, _, _ = request_account(device, account_index=0, network=NetworkId.TESTNET)
    request = CardanoMessageSignRequest(
        request_id="rt", origin="Companion", message_payload=b"data",
        required_signing_path=SigningPath(index=0, path=wallet.payment_signing_path()),
        address_bytes=wallet.base_address_bytes(),
        xfp=wallet.master_fingerprint,
    )
    encoder = messages.make_encoder(messages.UR_CIP8_SIG_REQ, request.to_cbor(), max_fragment_len=20)
    parts = []
    from seedsigner.helpers.ur2.ur_decoder import URDecoder
    decoder = URDecoder()
    while not decoder.is_complete():
        part = encoder.next_part()
        parts.append(part)
        decoder.receive_part(part)
    ur_type, cbor = messages.decode_ur_parts(parts)
    assert ur_type == messages.UR_CIP8_SIG_REQ
    parsed = messages.parse_request(ur_type, cbor)
    assert parsed == request
