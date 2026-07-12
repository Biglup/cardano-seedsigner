"""
Tests for CIP-8 signing-credential display classification.

The device must accurately label what the user is signing with (a payment
address, a stake (reward) address, or a DRep ID) using the derivation-path
role as the primary signal so a DRep is never mislabelled as a payment address
(the type-6 enterprise wrapper ambiguity).
"""

from cometa import (
    NetworkId,
    Credential,
    BaseAddress,
    EnterpriseAddress,
    RewardAddress,
    Blake2bHash,
)

from seedsigner.helpers.cardano_utils import (
    describe_signing_credential,
    classify_signing_credential,
    CREDENTIAL_SHORT_LABEL,
    root_key_from_seed,
    drep_id_from_key_hash,
)
from seedsigner.models.seed import Seed


H = 0x80000000
PATH_PAYMENT = [1852 + H, 1815 + H, 0 + H, 0, 0]
PATH_STAKE = [1852 + H, 1815 + H, 0 + H, 2, 0]
PATH_DREP = [1852 + H, 1815 + H, 0 + H, 3, 0]
PATH_MULTISIG = [1854 + H, 1815 + H, 0 + H, 0, 0]
PATH_MULTISIG_STAKE = [1854 + H, 1815 + H, 0 + H, 2, 0]
PATH_MINTING = [1855 + H, 1815 + H, 0 + H, 0, 0]


def _seed():
    return Seed(mnemonic=("abandon " * 11 + "about").split())


def _cred(seed, path):
    key = root_key_from_seed(seed).derive(path)
    return Credential.from_key_hash(key.get_public_key().to_ed25519_key().to_hash())


def _key_hash_bytes(seed, path):
    key = root_key_from_seed(seed).derive(path)
    return key.get_public_key().to_ed25519_key().to_hash().to_bytes()


def test_payment_address_labelled_payment():
    seed = _seed()
    addr = BaseAddress.from_credentials(
        NetworkId.TESTNET, _cred(seed, PATH_PAYMENT), _cred(seed, PATH_STAKE)).to_bytes()
    label, value = describe_signing_credential(addr, PATH_PAYMENT)
    assert label == "Payment Address:"
    assert value.startswith("addr_test1")


def test_reward_address_labelled_stake():
    seed = _seed()
    addr = RewardAddress.from_credentials(NetworkId.TESTNET, _cred(seed, PATH_STAKE)).to_bytes()
    label, value = describe_signing_credential(addr, PATH_STAKE)
    assert label == "Stake Address:"
    assert value.startswith("stake_test1")


def test_drep_bare_hash_labelled_drep_cip129():
    seed = _seed()
    key_hash = _key_hash_bytes(seed, PATH_DREP)
    label, value = describe_signing_credential(key_hash, PATH_DREP)
    assert label == "DRep ID:"
    assert value.startswith("drep1")
    assert value == drep_id_from_key_hash(key_hash)


def test_drep_enterprise_wrapper_not_mislabelled():
    """A type-6 enterprise address holding the DRep key hash must still be
    shown as a DRep ID when the signing role is 3, not as a payment address."""
    seed = _seed()
    wrapped = EnterpriseAddress.from_credentials(
        NetworkId.TESTNET, _cred(seed, PATH_DREP)).to_bytes()
    label, value = describe_signing_credential(wrapped, PATH_DREP)
    assert label == "DRep ID:"
    assert value.startswith("drep1")
    assert value == drep_id_from_key_hash(_key_hash_bytes(seed, PATH_DREP))


def test_enterprise_payment_address_not_drep():
    """The same byte shape (type-6 enterprise) with a payment role classifies
    as a payment address."""
    seed = _seed()
    addr = EnterpriseAddress.from_credentials(
        NetworkId.TESTNET, _cred(seed, PATH_PAYMENT)).to_bytes()
    label, value = describe_signing_credential(addr, PATH_PAYMENT)
    assert label == "Payment Address:"
    assert value.startswith("addr_test1")


def test_drep_fallback_without_path():
    """With no signing path, a bare 28-byte hash still classifies as a DRep
    ID."""
    seed = _seed()
    key_hash = _key_hash_bytes(seed, PATH_DREP)
    label, value = describe_signing_credential(key_hash, None)
    assert label == "DRep ID:"
    assert value.startswith("drep1")


def test_classify_kinds_match_overview_short_labels():
    """The overview short label and the Sign-With page must agree on the
    credential kind."""
    seed = _seed()
    base = BaseAddress.from_credentials(
        NetworkId.TESTNET, _cred(seed, PATH_PAYMENT), _cred(seed, PATH_STAKE)).to_bytes()
    reward = RewardAddress.from_credentials(NetworkId.TESTNET, _cred(seed, PATH_STAKE)).to_bytes()
    drep_wrapped = EnterpriseAddress.from_credentials(NetworkId.TESTNET, _cred(seed, PATH_DREP)).to_bytes()

    assert classify_signing_credential(base, PATH_PAYMENT) == "payment"
    assert classify_signing_credential(reward, PATH_STAKE) == "stake"
    assert classify_signing_credential(drep_wrapped, PATH_DREP) == "drep"
    assert classify_signing_credential(_key_hash_bytes(seed, PATH_DREP), PATH_DREP) == "drep"

    assert CREDENTIAL_SHORT_LABEL["payment"] == "Payment"
    assert CREDENTIAL_SHORT_LABEL["stake"] == "Stake"
    assert CREDENTIAL_SHORT_LABEL["drep"] == "DRep"


def test_multisig_key_shown_as_shared_key_hash_not_address():
    seed = _seed()
    key_hash = _key_hash_bytes(seed, PATH_MULTISIG)
    label, value = describe_signing_credential(key_hash, PATH_MULTISIG)
    assert label == "Key Hash:"
    assert value == key_hash.hex()


def test_multisig_stake_key_shown_as_hex_key_hash():
    seed = _seed()
    key_hash = _key_hash_bytes(seed, PATH_MULTISIG_STAKE)
    label, value = describe_signing_credential(key_hash, PATH_MULTISIG_STAKE)
    assert label == "Key Hash:"
    assert value == key_hash.hex()


def test_multisig_enterprise_wrapper_not_mislabelled_as_payment():
    seed = _seed()
    wrapped = EnterpriseAddress.from_credentials(
        NetworkId.TESTNET, _cred(seed, PATH_MULTISIG)).to_bytes()
    label, value = describe_signing_credential(wrapped, PATH_MULTISIG)
    assert label == "Key Hash:"
    assert value == _key_hash_bytes(seed, PATH_MULTISIG).hex()


def test_minting_key_shown_as_hex_key_hash():
    seed = _seed()
    key_hash = _key_hash_bytes(seed, PATH_MINTING)
    label, value = describe_signing_credential(key_hash, PATH_MINTING)
    assert label == "Key Hash:"
    assert value == key_hash.hex()


def test_classify_multisig_and_minting_kinds():
    seed = _seed()
    key_hash = _key_hash_bytes(seed, PATH_MULTISIG)
    assert classify_signing_credential(key_hash, PATH_MULTISIG) == "multisig"
    assert classify_signing_credential(key_hash, PATH_MINTING) == "minting"
    assert CREDENTIAL_SHORT_LABEL["multisig"] == "Multisig"
    assert CREDENTIAL_SHORT_LABEL["minting"] == "Minting"








def test_stake_bare_key_hash_shows_key_hash_not_crash():
    seed = _seed()
    key_hash = _key_hash_bytes(seed, PATH_STAKE)
    label, value = describe_signing_credential(key_hash, PATH_STAKE)
    assert label == "Key Hash:"
    assert value == key_hash.hex()


def test_payment_bare_key_hash_not_mislabelled_drep():
    seed = _seed()
    key_hash = _key_hash_bytes(seed, PATH_PAYMENT)
    label, value = describe_signing_credential(key_hash, PATH_PAYMENT)
    assert label == "Key Hash:"
    assert value == key_hash.hex()



def test_base_wrapped_multisig_key_shows_shared_key_hash():
    seed = _seed()
    base = BaseAddress.from_credentials(
        NetworkId.TESTNET, _cred(seed, PATH_MULTISIG), _cred(seed, PATH_MULTISIG_STAKE)).to_bytes()

    label, value = describe_signing_credential(base, PATH_MULTISIG)
    assert label == "Key Hash:"
    assert value == _key_hash_bytes(seed, PATH_MULTISIG).hex()

    label, value = describe_signing_credential(base, PATH_MULTISIG_STAKE)
    assert label == "Key Hash:"
    assert value == _key_hash_bytes(seed, PATH_MULTISIG_STAKE).hex()


def test_reward_wrapped_stake_credential_unwraps():
    seed = _seed()
    reward = RewardAddress.from_credentials(NetworkId.TESTNET, _cred(seed, PATH_MULTISIG_STAKE)).to_bytes()
    label, value = describe_signing_credential(reward, PATH_MULTISIG_STAKE)
    assert label == "Key Hash:"
    assert value == _key_hash_bytes(seed, PATH_MULTISIG_STAKE).hex()
