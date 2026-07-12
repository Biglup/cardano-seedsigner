"""
Tests for on-device ownership verification (helpers/cardano_utils.py):
collateral-return and change-output address verification via the request's
declared paths, CIP-8 message signing address verification, and the
owned-key-hash set derived from the request's declared paths (used to badge
certificates, withdrawals, required signers, and voters as own credentials).
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
    CardanoMessageSignRequest,
    SigningInput,
    SigningPath,
    ChangeOutput,
    ExtraSigner,
)
from seedsigner.helpers.cardano_utils import (
    root_key_from_seed,
    verify_change_outputs,
    verify_collateral_return,
    verify_message_signing_address,
    derive_owned_key_hashes,
)


H = 0x80000000
PATH_PAYMENT = [1852 + H, 1815 + H, H, 0, 0]
PATH_CHANGE = [1852 + H, 1815 + H, H, 1, 0]
PATH_STAKE = [1852 + H, 1815 + H, H, 2, 0]
OTHER_XFP = bytes.fromhex("deadbeef")
FOREIGN_ADDR = bytes.fromhex("61" + "11" * 28)
FOREIGN_KEY_HASH = bytes.fromhex("33" * 28)
SCRIPT_HASH = bytes.fromhex("22" * 28)


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


def _stake_script_base_addr_bytes(payment_cred, network_id=NetworkId.TESTNET) -> bytes:
    addr = BaseAddress.from_credentials(
        network_id,
        payment_cred,
        Credential.from_script_hash(SCRIPT_HASH),
    )
    return addr.to_bytes()


def _body_cbor(collateral_return_addr=None, output_addr=FOREIGN_ADDR) -> bytes:
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
    w.write_bytes(output_addr)
    w.write_int(1_000_000)
    w.write_int(2)
    w.write_int(180_000)
    if collateral_return_addr is not None:
        w.write_int(16)
        w.write_start_array(2)
        w.write_bytes(collateral_return_addr)
        w.write_int(5_000_000)
    return w.encode()


def _body(collateral_return_addr=None, output_addr=FOREIGN_ADDR):
    cbor = _body_cbor(collateral_return_addr, output_addr)
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


def test_change_output_stake_script_base_address_verifies(seed):
    addr = _stake_script_base_addr_bytes(_payment_credential(seed, PATH_CHANGE))
    body = _body(output_addr=addr)
    req = _request(
        change_outputs=[ChangeOutput(index=0, path=PATH_CHANGE, xfp=_fingerprint(seed))]
    )
    assert verify_change_outputs(req, seed, body) == [0]


def test_change_output_stake_script_foreign_payment_key_fails(seed):
    addr = _stake_script_base_addr_bytes(Credential.from_key_hash(FOREIGN_KEY_HASH))
    body = _body(output_addr=addr)
    req = _request(
        change_outputs=[ChangeOutput(index=0, path=PATH_CHANGE, xfp=_fingerprint(seed))]
    )
    assert verify_change_outputs(req, seed, body) == []


def test_change_output_stake_script_wrong_network_fails(seed):
    addr = _stake_script_base_addr_bytes(
        _payment_credential(seed, PATH_CHANGE), network_id=NetworkId.MAINNET
    )
    body = _body(output_addr=addr)
    req = _request(
        change_outputs=[ChangeOutput(index=0, path=PATH_CHANGE, xfp=_fingerprint(seed))]
    )
    assert verify_change_outputs(req, seed, body) == []


def test_change_output_out_of_range_index_is_unverified(seed):
    body = _body(output_addr=_enterprise_addr_bytes(seed, PATH_CHANGE))
    req = _request(
        change_outputs=[ChangeOutput(index=5, path=PATH_CHANGE, xfp=_fingerprint(seed))]
    )
    assert verify_change_outputs(req, seed, body) == []


def test_change_output_mixed_valid_and_out_of_range_verifies_valid(seed):
    body = _body(output_addr=_enterprise_addr_bytes(seed, PATH_CHANGE))
    fp = _fingerprint(seed)
    req = _request(
        change_outputs=[
            ChangeOutput(index=0, path=PATH_CHANGE, xfp=fp),
            ChangeOutput(index=5, path=PATH_CHANGE, xfp=fp),
        ]
    )
    assert verify_change_outputs(req, seed, body) == [0]


def test_change_output_negative_index_is_unverified(seed):
    body = _body(output_addr=_enterprise_addr_bytes(seed, PATH_CHANGE))
    req = _request(
        change_outputs=[ChangeOutput(index=-1, path=PATH_CHANGE, xfp=_fingerprint(seed))]
    )
    assert verify_change_outputs(req, seed, body) == []


def test_collateral_return_stake_script_base_address_verifies(seed):
    addr = _stake_script_base_addr_bytes(_payment_credential(seed, PATH_CHANGE))
    body = _body(addr)
    req = _request(
        collateral_return_path=ExtraSigner(xfp=_fingerprint(seed), path=PATH_CHANGE)
    )
    assert verify_collateral_return(req, seed, body) is True


def _msg_request(seed, path, address_bytes):
    return CardanoMessageSignRequest(
        request_id="m",
        origin=None,
        message_payload=b"hi",
        required_signing_path=SigningPath(index=0, path=path),
        address_bytes=address_bytes,
        xfp=_fingerprint(seed),
    )


def test_message_address_stake_script_base_address_verifies(seed):
    addr = _stake_script_base_addr_bytes(_payment_credential(seed, PATH_PAYMENT))
    req = _msg_request(seed, PATH_PAYMENT, addr)
    assert verify_message_signing_address(req, seed) is True


def test_message_address_stake_script_foreign_payment_key_fails(seed):
    addr = _stake_script_base_addr_bytes(Credential.from_key_hash(FOREIGN_KEY_HASH))
    req = _msg_request(seed, PATH_PAYMENT, addr)
    assert verify_message_signing_address(req, seed) is False


def test_message_address_stake_script_wrong_path_fails(seed):
    addr = _stake_script_base_addr_bytes(_payment_credential(seed, PATH_PAYMENT))
    req = _msg_request(seed, PATH_CHANGE, addr)
    assert verify_message_signing_address(req, seed) is False


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
