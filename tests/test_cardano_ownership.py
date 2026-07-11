"""
Tests for on-device ownership verification (helpers/cardano_utils.py):
collateral-return address verification via the request's optional
collateral_return_path, and the owned-key-hash set derived from the
request's declared paths (used to badge certificates, withdrawals,
required signers, and voters as own credentials).
"""

import pytest

from cometa import (
    CborReader,
    CborWriter,
    TransactionBody,
    NetworkId,
    Credential,
    EnterpriseAddress,
    BaseAddress,
)

from seedsigner.models.seed import Seed
from seedsigner.models.cardano_tx import (
    CardanoSignRequest,
    CardanoParsedTx,
    SigningInput,
    ChangeOutput,
    ExtraSigner,
)
from seedsigner.helpers.cardano_utils import (
    root_key_from_seed,
    verify_collateral_return,
    derive_owned_key_hashes,
)


H = 0x80000000
PATH_PAYMENT = [1852 + H, 1815 + H, H, 0, 0]
PATH_CHANGE = [1852 + H, 1815 + H, H, 1, 0]
PATH_STAKE = [1852 + H, 1815 + H, H, 2, 0]
OTHER_XFP = bytes.fromhex("deadbeef")
FOREIGN_ADDR = bytes.fromhex("61" + "11" * 28)


@pytest.fixture
def seed():
    return Seed(mnemonic=("abandon " * 11 + "about").split())


def _fingerprint(seed) -> bytes:
    return bytes.fromhex(seed.get_fingerprint())


def _key_hash(seed, path) -> bytes:
    key = root_key_from_seed(seed).derive(path)
    return key.get_public_key().to_ed25519_key().to_hash().to_bytes()


def _payment_credential(seed, path):
    return Credential.from_key_hash(_key_hash(seed, path))


def _enterprise_addr_bytes(seed, path) -> bytes:
    addr = EnterpriseAddress.from_credentials(
        NetworkId.TESTNET, _payment_credential(seed, path)
    )
    return addr.to_bytes()


def _base_addr_bytes(seed, path) -> bytes:
    addr = BaseAddress.from_credentials(
        NetworkId.TESTNET,
        _payment_credential(seed, path),
        _payment_credential(seed, PATH_STAKE),
    )
    return addr.to_bytes()


def _body_cbor(collateral_return_addr=None) -> bytes:
    w = CborWriter()
    w.write_start_map(4 if collateral_return_addr is not None else 3)
    w.write_int(0)
    w.write_start_array(1)
    w.write_start_array(2)
    w.write_bytes(b"\x00" * 32)
    w.write_int(0)
    w.write_int(1)
    w.write_start_array(1)
    w.write_start_array(2)
    w.write_bytes(FOREIGN_ADDR)
    w.write_int(1_000_000)
    w.write_int(2)
    w.write_int(180_000)
    if collateral_return_addr is not None:
        w.write_int(16)
        w.write_start_array(2)
        w.write_bytes(collateral_return_addr)
        w.write_int(5_000_000)
    return w.encode()


def _body(collateral_return_addr=None):
    cbor = _body_cbor(collateral_return_addr)
    return TransactionBody.from_cbor(CborReader.from_bytes(cbor))


def _request(sign_data=b"\xa0", inputs=None, change_outputs=None,
             extra_signers=None, collateral_return_path=None):
    return CardanoSignRequest(
        request_id="r",
        origin=None,
        sign_data=sign_data,
        inputs=inputs or [],
        change_outputs=change_outputs or [],
        network=NetworkId.TESTNET,
        extra_signers=extra_signers or [],
        collateral_return_path=collateral_return_path,
    )


def test_collateral_return_enterprise_address_verifies(seed):
    body = _body(_enterprise_addr_bytes(seed, PATH_CHANGE))
    req = _request(
        collateral_return_path=ExtraSigner(xfp=_fingerprint(seed), path=PATH_CHANGE)
    )
    assert verify_collateral_return(req, seed, body) is True


def test_collateral_return_base_address_verifies(seed):
    body = _body(_base_addr_bytes(seed, PATH_CHANGE))
    req = _request(
        collateral_return_path=ExtraSigner(xfp=_fingerprint(seed), path=PATH_CHANGE)
    )
    assert verify_collateral_return(req, seed, body) is True


def test_collateral_return_wrong_path_fails(seed):
    body = _body(_enterprise_addr_bytes(seed, PATH_CHANGE))
    req = _request(
        collateral_return_path=ExtraSigner(xfp=_fingerprint(seed), path=PATH_PAYMENT)
    )
    assert verify_collateral_return(req, seed, body) is False


def test_collateral_return_foreign_address_fails(seed):
    body = _body(FOREIGN_ADDR)
    req = _request(
        collateral_return_path=ExtraSigner(xfp=_fingerprint(seed), path=PATH_CHANGE)
    )
    assert verify_collateral_return(req, seed, body) is False


def test_collateral_return_absent_field_fails(seed):
    body = _body(_enterprise_addr_bytes(seed, PATH_CHANGE))
    assert verify_collateral_return(_request(), seed, body) is False


def test_collateral_return_absent_output_fails(seed):
    body = _body(None)
    req = _request(
        collateral_return_path=ExtraSigner(xfp=_fingerprint(seed), path=PATH_CHANGE)
    )
    assert verify_collateral_return(req, seed, body) is False


def test_collateral_return_xfp_mismatch_fails(seed):
    body = _body(_enterprise_addr_bytes(seed, PATH_CHANGE))
    req = _request(
        collateral_return_path=ExtraSigner(xfp=OTHER_XFP, path=PATH_CHANGE)
    )
    assert verify_collateral_return(req, seed, body) is False


def test_owned_key_hashes_cover_all_declared_path_sources(seed):
    fp = _fingerprint(seed)
    req = _request(
        inputs=[SigningInput(tx_hash=b"\x00" * 32, index=0, xfp=fp, path=PATH_PAYMENT)],
        extra_signers=[ExtraSigner(xfp=fp, path=PATH_STAKE)],
        change_outputs=[ChangeOutput(index=0, path=PATH_CHANGE, xfp=fp)],
    )
    owned = derive_owned_key_hashes(req, seed)
    assert _key_hash(seed, PATH_PAYMENT) in owned
    assert _key_hash(seed, PATH_STAKE) in owned
    assert _key_hash(seed, PATH_CHANGE) in owned


def test_owned_key_hashes_include_collateral_return_path(seed):
    fp = _fingerprint(seed)
    req = _request(collateral_return_path=ExtraSigner(xfp=fp, path=PATH_CHANGE))
    assert _key_hash(seed, PATH_CHANGE) in derive_owned_key_hashes(req, seed)


def test_owned_key_hashes_skip_foreign_xfp(seed):
    req = _request(
        inputs=[SigningInput(tx_hash=b"\x00" * 32, index=0, xfp=OTHER_XFP, path=PATH_PAYMENT)],
        extra_signers=[ExtraSigner(xfp=OTHER_XFP, path=PATH_STAKE)],
        collateral_return_path=ExtraSigner(xfp=OTHER_XFP, path=PATH_CHANGE),
    )
    assert derive_owned_key_hashes(req, seed) == set()


def test_owned_key_hashes_accept_unspecified_change_xfp(seed):
    req = _request(change_outputs=[ChangeOutput(index=0, path=PATH_CHANGE)])
    assert _key_hash(seed, PATH_CHANGE) in derive_owned_key_hashes(req, seed)


def test_owned_key_hashes_empty_without_declared_paths(seed):
    assert derive_owned_key_hashes(_request(), seed) == set()


def test_parsed_tx_defaults_are_safe(seed):
    req = _request(sign_data=_body_cbor(_enterprise_addr_bytes(seed, PATH_CHANGE)))
    parsed = CardanoParsedTx(req, verified_change_indices=[])
    assert parsed.collateral_return_verified is False
    assert parsed.owned_key_hashes == set()
