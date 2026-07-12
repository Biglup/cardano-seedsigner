"""
Tests for the Cardano account export model and CBOR codec.

Covers CBOR round-trips for cardano-account-req and cardano-account, derivation
correctness (the exported account xpub, soft-derived by a client, reproduces a
known Yoroi/Eternl address), and that build_account_response carries the seed's
Bitcoin master fingerprint.
"""

import pytest

from cometa import BaseAddress, Bip32PublicKey, Credential

from seedsigner.models.seed import Seed
from seedsigner.models.cardano_account import (
    AccountKey,
    CardanoAccountRequest,
    CardanoAccountResponse,
    account_path,
    build_account_response,
    derive_account_keys,
    format_derivation_path,
    PURPOSE_CIP1852,
    HARDENED_OFFSET,
)


ABANDON_MNEMONIC = (
    "abandon abandon abandon abandon abandon abandon abandon abandon "
    "abandon abandon abandon about"
).split()

KNOWN_FIRST_ADDRESS = (
    "addr1qy8ac7qqy0vtulyl7wntmsxc6wex80gvcyjy33qffrhm7sh927ysx5sftuw0dlft05dz3c7revpf7jx0xnlcjz3g69mq4afdhv"
)


def test_request_roundtrip_minimal():
    req = CardanoAccountRequest(request_id="req-1", account_indices=[0])
    decoded = CardanoAccountRequest.from_cbor(req.to_cbor())
    assert decoded.request_id == "req-1"
    assert decoded.account_indices == [0]
    assert decoded.key_purpose == PURPOSE_CIP1852
    assert decoded.origin is None


def test_request_roundtrip_full():
    req = CardanoAccountRequest(
        request_id="abc-123",
        account_indices=[0, 1, 5],
        key_purpose=PURPOSE_CIP1852,
        origin="Eternl",
    )
    decoded = CardanoAccountRequest.from_cbor(req.to_cbor())
    assert decoded == req


def test_request_missing_required_fields_raises():
    from cometa import CborWriter
    w = CborWriter()
    w.write_start_map(1)
    w.write_int(2)
    w.write_str("OnlyOrigin")
    with pytest.raises(ValueError):
        CardanoAccountRequest.from_cbor(w.encode())


def test_response_roundtrip_single_account():
    keys = [AccountKey(account_index=0, xpub=b"\x11" * 64, path=account_path(0))]
    resp = CardanoAccountResponse(
        request_id="req-1",
        master_fingerprint=bytes.fromhex("a1b2c3d4"),
        keys=keys,
    )
    decoded = CardanoAccountResponse.from_cbor(resp.to_cbor())
    assert decoded == resp


def test_response_roundtrip_multi_account():
    keys = [
        AccountKey(account_index=i, xpub=bytes([i]) * 64, path=account_path(i))
        for i in (0, 1, 7)
    ]
    resp = CardanoAccountResponse(
        request_id="",
        master_fingerprint=bytes.fromhex("deadbeef"),
        keys=keys,
        device_label="Cardano SeedSigner",
    )
    decoded = CardanoAccountResponse.from_cbor(resp.to_cbor())
    assert decoded == resp
    assert [k.account_index for k in decoded.keys] == [0, 1, 7]
    assert all(len(k.xpub) == 64 for k in decoded.keys)


def test_account_path():
    assert account_path(0) == [
        PURPOSE_CIP1852 | HARDENED_OFFSET,
        1815 | HARDENED_OFFSET,
        0 | HARDENED_OFFSET,
    ]
    assert account_path(3)[2] == (3 | HARDENED_OFFSET)


def test_format_derivation_path():
    assert format_derivation_path(account_path(0)) == "m/1852'/1815'/0'"
    assert format_derivation_path(account_path(7)) == "m/1852'/1815'/7'"
    assert format_derivation_path([1852 | HARDENED_OFFSET, 1815 | HARDENED_OFFSET, 0 | HARDENED_OFFSET, 2, 0]) == "m/1852'/1815'/0'/2/0"


def test_derive_account_keys_reproduces_known_address():
    seed = Seed(mnemonic=ABANDON_MNEMONIC)
    keys = derive_account_keys(seed, [0])
    assert len(keys) == 1
    account_key = keys[0]
    assert account_key.account_index == 0
    assert len(account_key.xpub) == 64
    assert account_key.path == account_path(0)

    xpub = Bip32PublicKey.from_bytes(account_key.xpub)
    payment = xpub.derive([0, 0])
    stake = xpub.derive([2, 0])
    payment_cred = Credential.from_key_hash(payment.to_ed25519_key().to_hash())
    stake_cred = Credential.from_key_hash(stake.to_ed25519_key().to_hash())
    addr = BaseAddress.from_credentials(1, payment_cred, stake_cred)
    assert str(addr) == KNOWN_FIRST_ADDRESS


def test_derive_account_keys_multi_distinct():
    seed = Seed(mnemonic=ABANDON_MNEMONIC)
    keys = derive_account_keys(seed, [0, 1])
    assert [k.account_index for k in keys] == [0, 1]
    assert keys[0].xpub != keys[1].xpub


def test_build_account_response_carries_btc_fingerprint():
    seed = Seed(mnemonic=ABANDON_MNEMONIC)
    resp = build_account_response(seed, request_id="req-9", account_indices=[0, 2])
    assert resp.master_fingerprint == bytes.fromhex(seed.get_fingerprint())
    assert len(resp.master_fingerprint) == 4
    assert [k.account_index for k in resp.keys] == [0, 2]
    assert CardanoAccountResponse.from_cbor(resp.to_cbor()) == resp


def test_request_roundtrip_1854_purpose():
    from seedsigner.models.cardano_account import PURPOSE_CIP1854

    req = CardanoAccountRequest(request_id="ms-req", account_indices=[0],
                                key_purpose=PURPOSE_CIP1854)
    decoded = CardanoAccountRequest.from_cbor(req.to_cbor())
    assert decoded.key_purpose == PURPOSE_CIP1854


def test_build_account_response_1854_derives_distinct_key():
    from seedsigner.models.cardano_account import PURPOSE_CIP1854

    seed = Seed(mnemonic=ABANDON_MNEMONIC)
    ordinary = build_account_response(seed, "r", [0], PURPOSE_CIP1852)
    shared = build_account_response(seed, "r", [0], PURPOSE_CIP1854)

    assert shared.keys[0].path == [
        PURPOSE_CIP1854 | HARDENED_OFFSET,
        1815 | HARDENED_OFFSET,
        0 | HARDENED_OFFSET,
    ]
    assert shared.keys[0].xpub != ordinary.keys[0].xpub
    assert shared.master_fingerprint == ordinary.master_fingerprint


def test_account_xpub_hrp_by_purpose():
    from seedsigner.models.cardano_account import PURPOSE_CIP1854, account_xpub_hrp

    assert account_xpub_hrp(PURPOSE_CIP1852) == "acct_xvk"
    assert account_xpub_hrp(PURPOSE_CIP1854) == "acct_shared_xvk"


def test_request_unsupported_key_purpose_raises():
    for bad_purpose in (44, 1855, 2**40):
        req = CardanoAccountRequest(request_id="bad", account_indices=[0],
                                    key_purpose=bad_purpose)
        with pytest.raises(ValueError):
            CardanoAccountRequest.from_cbor(req.to_cbor())


def test_request_hardened_account_index_raises():
    for bad_index in (HARDENED_OFFSET, HARDENED_OFFSET + 1, 2**32):
        req = CardanoAccountRequest(request_id="bad", account_indices=[bad_index])
        with pytest.raises(ValueError):
            CardanoAccountRequest.from_cbor(req.to_cbor())


def test_request_max_soft_account_index_accepted():
    req = CardanoAccountRequest(request_id="max", account_indices=[HARDENED_OFFSET - 1])
    decoded = CardanoAccountRequest.from_cbor(req.to_cbor())
    assert decoded.account_indices == [HARDENED_OFFSET - 1]
