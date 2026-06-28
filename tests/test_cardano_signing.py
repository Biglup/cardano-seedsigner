"""
Tests for the on-device signing core (helpers/cardano_signing.py).

Verifies that the produced vkey witnesses cryptographically verify against the
derived key over the transaction-body hash, that only signers matching the
seed's fingerprint are signed (partial witness set), duplicate paths collapse to
one witness, and that CIP-8 signing matches a direct cometa call and enforces the
signer/address guards.
"""

import pytest

from cometa import (
    CborReader,
    TransactionBody,
    VkeyWitnessSet,
    Ed25519PublicKey,
    Ed25519Signature,
    Address,
    NetworkId,
    cip8_sign,
)

from seedsigner.models.seed import Seed
from seedsigner.models.cardano_tx import (
    CardanoSignRequest,
    SigningInput,
    ExtraSigner,
    CardanoMessageSignRequest,
    SigningPath,
)
import hashlib

from cometa import Credential, EnterpriseAddress

from seedsigner.helpers.cardano_utils import root_key_from_seed
from seedsigner.helpers.cardano_signing import (
    build_tx_sign_response,
    build_cip8_sign_response,
    matching_signing_paths,
    _seed_fingerprint,
)


H = 0x80000000
PATH_0 = [1852 + H, 1815 + H, 0 + H, 0, 0]
PATH_STAKE = [1852 + H, 1815 + H, 0 + H, 2, 0]
OTHER_XFP = bytes.fromhex("deadbeef")

# minimal valid tx body: {0:[input], 1:[output], 2:fee}
BODY_CBOR = bytes.fromhex(
    "a3"
    "00" "81" "82" "5820" + "00" * 32 + "00"
    "01" "81" "82" "581d61" + "11" * 28 + "1a000f4240"
    "02" "1a0002bf20"
)


@pytest.fixture
def seed():
    return Seed(mnemonic=("abandon " * 11 + "about").split())


def _decode_witnesses(cbor: bytes):
    return VkeyWitnessSet.from_cbor(CborReader.from_bytes(cbor))


def _tx_hash(body_cbor: bytes) -> bytes:
    return TransactionBody.from_cbor(CborReader.from_bytes(body_cbor)).hash.to_bytes()


def test_tx_witness_verifies(seed):
    fp = _seed_fingerprint(seed)
    req = CardanoSignRequest(
        request_id="r1", origin=None, sign_data=BODY_CBOR,
        inputs=[SigningInput(tx_hash=b"\x00" * 32, index=0, xfp=fp, path=PATH_0)],
        change_outputs=[], network=NetworkId.TESTNET,
    )
    resp = build_tx_sign_response(seed, req)
    assert resp.request_id == "r1"

    ws = _decode_witnesses(resp.vkey_witness_set)
    assert len(ws) == 1

    # the witness verifies against its own vkey over the tx hash
    w = ws[0]
    pub = Ed25519PublicKey.from_bytes(w.vkey)
    sig = Ed25519Signature.from_bytes(w.signature)
    assert pub.verify(sig, _tx_hash(BODY_CBOR))

    # and that vkey is exactly the key derived from PATH_0
    expected_vkey = root_key_from_seed(seed).derive(PATH_0).get_public_key().to_ed25519_key().to_bytes()
    assert w.vkey == expected_vkey


def test_partial_witness_skips_mismatched_xfp(seed):
    fp = _seed_fingerprint(seed)
    req = CardanoSignRequest(
        request_id="r2", origin=None, sign_data=BODY_CBOR,
        inputs=[SigningInput(tx_hash=b"\x00" * 32, index=0, xfp=fp, path=PATH_0)],
        change_outputs=[], network=NetworkId.TESTNET,
        extra_signers=[ExtraSigner(xfp=OTHER_XFP, path=PATH_STAKE)],
    )
    ws = _decode_witnesses(build_tx_sign_response(seed, req).vkey_witness_set)
    assert len(ws) == 1  # the OTHER_XFP extra signer belongs to a different seed


def test_no_matching_signer_yields_empty_witness_set(seed):
    req = CardanoSignRequest(
        request_id="r3", origin=None, sign_data=BODY_CBOR,
        inputs=[SigningInput(tx_hash=b"\x00" * 32, index=0, xfp=OTHER_XFP, path=PATH_0)],
        change_outputs=[], network=NetworkId.TESTNET,
    )
    assert matching_signing_paths(req, seed) == []
    ws = _decode_witnesses(build_tx_sign_response(seed, req).vkey_witness_set)
    assert len(ws) == 0


def test_duplicate_paths_collapse_to_one_witness(seed):
    fp = _seed_fingerprint(seed)
    req = CardanoSignRequest(
        request_id="r4", origin=None, sign_data=BODY_CBOR,
        inputs=[
            SigningInput(tx_hash=b"\x00" * 32, index=0, xfp=fp, path=PATH_0),
            SigningInput(tx_hash=b"\x11" * 32, index=1, xfp=fp, path=PATH_0),
        ],
        change_outputs=[], network=NetworkId.TESTNET,
    )
    assert matching_signing_paths(req, seed) == [PATH_0]
    ws = _decode_witnesses(build_tx_sign_response(seed, req).vkey_witness_set)
    assert len(ws) == 1


def test_two_distinct_signers_two_witnesses(seed):
    fp = _seed_fingerprint(seed)
    req = CardanoSignRequest(
        request_id="r5", origin=None, sign_data=BODY_CBOR,
        inputs=[SigningInput(tx_hash=b"\x00" * 32, index=0, xfp=fp, path=PATH_0)],
        change_outputs=[], network=NetworkId.TESTNET,
        extra_signers=[ExtraSigner(xfp=fp, path=PATH_STAKE)],
    )
    ws = _decode_witnesses(build_tx_sign_response(seed, req).vkey_witness_set)
    assert len(ws) == 2


def _enterprise_addr_bytes(seed, path):
    """The real enterprise (mainnet) address bytes for a seed's derived key."""
    from cometa import NetworkId as _N
    key = root_key_from_seed(seed).derive(path)
    cred = Credential.from_key_hash(key.get_public_key().to_ed25519_key().to_hash())
    return EnterpriseAddress.from_credentials(_N.MAINNET, cred).to_address().to_bytes()


def test_cip8_payment_uses_ledger_2field_format(seed):
    # All CIP-8 signing uses the Ledger/Keystone 2-field protected header
    # {1: alg, "address": address_bytes} with NO kid — including payment.
    import cbor2
    fp = _seed_fingerprint(seed)
    addr_bytes = _enterprise_addr_bytes(seed, PATH_0)
    msg = b"I attest ownership of this address."
    req = CardanoMessageSignRequest(
        request_id="m1", origin=None, message_payload=msg,
        required_signing_path=SigningPath(index=0, path=PATH_0),
        address_bytes=addr_bytes, xfp=fp,
    )
    resp = build_cip8_sign_response(seed, req)
    assert resp.request_id == "m1"

    cose_sign1 = cbor2.loads(resp.cose_sign1)
    protected = cbor2.loads(cose_sign1[0])
    assert protected == {1: -8, "address": addr_bytes}      # 2-field, no kid
    assert cose_sign1[1] == {"hashed": False}
    assert cbor2.loads(resp.cose_key)[2] == addr_bytes      # COSE_Key kid = address

    # signature verifies over the Sig_structure
    sig_structure = cbor2.dumps(["Signature1", cose_sign1[0], b"", msg])
    pub = cbor2.loads(resp.cose_key)[-2]
    assert Ed25519PublicKey.from_bytes(pub).verify(
        Ed25519Signature.from_bytes(cose_sign1[3]), sig_structure)


def test_cip8_rejects_wrong_seed(seed):
    req = CardanoMessageSignRequest(
        request_id="m2", origin=None, message_payload=b"hi",
        required_signing_path=SigningPath(index=0, path=PATH_0),
        address_bytes=_enterprise_addr_bytes(seed, PATH_0), xfp=OTHER_XFP,
    )
    with pytest.raises(ValueError):
        build_cip8_sign_response(seed, req)


PATH_DREP = [1852 + H, 1815 + H, 0 + H, 3, 0]


def _reward_addr_bytes(seed):
    from cometa import RewardAddress, NetworkId as _N
    key = root_key_from_seed(seed).derive(PATH_STAKE)
    cred = Credential.from_key_hash(key.get_public_key().to_ed25519_key().to_hash())
    return RewardAddress.from_credentials(_N.MAINNET, cred).to_address().to_bytes()


def _drep_hash_bytes(seed):
    key = root_key_from_seed(seed).derive(PATH_DREP)
    return key.get_public_key().to_ed25519_key().to_hash().to_bytes()


def test_cip8_sign_with_stake_key(seed):
    import cbor2
    fp = _seed_fingerprint(seed)
    req = CardanoMessageSignRequest(
        request_id="stake", origin=None, message_payload=b"delegate",
        required_signing_path=SigningPath(index=0, path=PATH_STAKE),
        address_bytes=_reward_addr_bytes(seed), xfp=fp,
    )
    resp = build_cip8_sign_response(seed, req)
    assert len(resp.cose_sign1) > 0 and len(resp.cose_key) > 0

    pub = cbor2.loads(resp.cose_key)[-2]
    derived = root_key_from_seed(seed).derive(PATH_STAKE).get_public_key().to_ed25519_key()
    assert pub == derived.to_bytes()


def test_cip8_sign_with_drep_key(seed):
    # DRep binds to a bare 28-byte key hash. The COSE must use the CIP-95 /
    # Ledger wire format: 2-field protected header {1: alg, "address": hash},
    # NO kid (label 4), and the signature must verify.
    import cbor2
    fp = _seed_fingerprint(seed)
    drep_hash = _drep_hash_bytes(seed)
    req = CardanoMessageSignRequest(
        request_id="drep", origin=None, message_payload=b"vote",
        required_signing_path=SigningPath(index=0, path=PATH_DREP),
        address_bytes=drep_hash, xfp=fp,
    )
    resp = build_cip8_sign_response(seed, req)

    cose_sign1 = cbor2.loads(resp.cose_sign1)
    protected = cbor2.loads(cose_sign1[0])
    assert protected == {1: -8, "address": drep_hash}   # 2-field, "address", no kid
    assert cose_sign1[1] == {"hashed": False}
    assert cose_sign1[2] == b"vote"

    # signature verifies over the Sig_structure
    sig_structure = cbor2.dumps(["Signature1", cose_sign1[0], b"", b"vote"])
    pub = cbor2.loads(resp.cose_key)[-2]
    assert cbor2.loads(resp.cose_key)[2] == drep_hash   # COSE_Key kid = key hash
    assert Ed25519PublicKey.from_bytes(pub).to_hash().to_bytes() == drep_hash
    assert Ed25519PublicKey.from_bytes(pub).verify(
        Ed25519Signature.from_bytes(cose_sign1[3]), sig_structure)


def test_cip8_requires_address(seed):
    fp = _seed_fingerprint(seed)
    req = CardanoMessageSignRequest(
        request_id="m3", origin=None, message_payload=b"hi",
        required_signing_path=SigningPath(index=0, path=PATH_0),
        address_bytes=None, xfp=fp,
    )
    with pytest.raises(ValueError):
        build_cip8_sign_response(seed, req)


def test_cip8_rejects_address_key_mismatch(seed):
    # Address bound to PATH_0's key, but the signing path is PATH_STAKE — the
    # signature would not correspond to the reviewed address. Must be rejected.
    fp = _seed_fingerprint(seed)
    req = CardanoMessageSignRequest(
        request_id="m4", origin=None, message_payload=b"hi",
        required_signing_path=SigningPath(index=0, path=PATH_STAKE),
        address_bytes=_enterprise_addr_bytes(seed, PATH_0), xfp=fp,
    )
    with pytest.raises(ValueError):
        build_cip8_sign_response(seed, req)


def test_signed_hash_equals_blake2b_of_sign_data(seed):
    # Fidelity: the device signs blake2b-256 of the exact bytes it received.
    fp = _seed_fingerprint(seed)
    req = CardanoSignRequest(
        request_id="r6", origin=None, sign_data=BODY_CBOR,
        inputs=[SigningInput(tx_hash=b"\x00" * 32, index=0, xfp=fp, path=PATH_0)],
        change_outputs=[], network=NetworkId.TESTNET,
    )
    expected = hashlib.blake2b(BODY_CBOR, digest_size=32).digest()
    assert _tx_hash(BODY_CBOR) == expected

    ws = _decode_witnesses(build_tx_sign_response(seed, req).vkey_witness_set)
    pub = Ed25519PublicKey.from_bytes(ws[0].vkey)
    sig = Ed25519Signature.from_bytes(ws[0].signature)
    assert pub.verify(sig, expected)


def test_passphrase_seed_signs_with_distinct_key(seed):
    # A passphrase changes both the Cardano signing key and the BTC fingerprint.
    pp_seed = Seed(mnemonic=("abandon " * 11 + "about").split(), passphrase="pass123")
    assert _seed_fingerprint(pp_seed) != _seed_fingerprint(seed)

    fp = _seed_fingerprint(pp_seed)
    req = CardanoSignRequest(
        request_id="r7", origin=None, sign_data=BODY_CBOR,
        inputs=[SigningInput(tx_hash=b"\x00" * 32, index=0, xfp=fp, path=PATH_0)],
        change_outputs=[], network=NetworkId.TESTNET,
    )
    ws = _decode_witnesses(build_tx_sign_response(pp_seed, req).vkey_witness_set)
    assert len(ws) == 1
    pub = Ed25519PublicKey.from_bytes(ws[0].vkey)
    sig = Ed25519Signature.from_bytes(ws[0].signature)
    assert pub.verify(sig, _tx_hash(BODY_CBOR))

    # the passphrase key differs from the no-passphrase key for the same path
    plain_vkey = root_key_from_seed(seed).derive(PATH_0).get_public_key().to_ed25519_key().to_bytes()
    assert ws[0].vkey != plain_vkey
