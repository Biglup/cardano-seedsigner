"""
Test that Cardano address derivation from BIP-39 mnemonics produces
addresses compatible with standard Cardano wallets (Yoroi, Eternl, Lace).

Uses the well-known "abandon" test vector and verifies the first receive
address matches the expected bech32 address.
"""

from cometa import (
    Bip32PrivateKey,
    BaseAddress,
    RewardAddress,
    Credential,
    mnemonic_to_entropy,
)


def _derive_root_key(mnemonic: list[str], passphrase: str = "") -> Bip32PrivateKey:
    """Derive CIP-1852 root key from mnemonic."""
    entropy = mnemonic_to_entropy(mnemonic)
    passphrase_bytes = passphrase.encode('utf-8') if passphrase else b""
    return Bip32PrivateKey.from_bip39_entropy(passphrase_bytes, entropy)


def test_first_receive_address_matches_known_wallets():
    """
    The 'abandon x11 + about' mnemonic should produce the same first
    receive address as Yoroi, Eternl, and other CIP-1852 wallets.

    Path: m/1852'/1815'/0'/0/0 (payment) + m/1852'/1815'/0'/2/0 (staking)
    Network: mainnet (1)
    """
    mnemonic = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about".split()
    root_key = _derive_root_key(mnemonic)

    # Payment key: m/1852'/1815'/0'/0/0
    payment_key = root_key.derive([1852 | 0x80000000, 1815 | 0x80000000, 0x80000000, 0, 0])
    payment_cred = Credential.from_key_hash(
        payment_key.get_public_key().to_ed25519_key().to_hash()
    )

    # Staking key: m/1852'/1815'/0'/2/0
    stake_key = root_key.derive([1852 | 0x80000000, 1815 | 0x80000000, 0x80000000, 2, 0])
    stake_cred = Credential.from_key_hash(
        stake_key.get_public_key().to_ed25519_key().to_hash()
    )

    # Mainnet base address
    addr = BaseAddress.from_credentials(1, payment_cred, stake_cred)

    # This address is verifiable in Yoroi/Eternl with the same mnemonic
    expected = "addr1qy8ac7qqy0vtulyl7wntmsxc6wex80gvcyjy33qffrhm7sh927ysx5sftuw0dlft05dz3c7revpf7jx0xnlcjz3g69mq4afdhv"
    assert str(addr) == expected


def test_stake_address():
    """Verify the staking (reward) address derivation."""
    mnemonic = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about".split()
    root_key = _derive_root_key(mnemonic)

    # Staking key: m/1852'/1815'/0'/2/0
    stake_key = root_key.derive([1852 | 0x80000000, 1815 | 0x80000000, 0x80000000, 2, 0])
    stake_cred = Credential.from_key_hash(
        stake_key.get_public_key().to_ed25519_key().to_hash()
    )

    # Mainnet reward address
    reward_addr = RewardAddress.from_credentials(1, stake_cred)
    assert str(reward_addr).startswith("stake1")


def test_second_receive_address_differs():
    """Address at index 1 should be different from index 0."""
    mnemonic = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about".split()
    root_key = _derive_root_key(mnemonic)

    stake_key = root_key.derive([1852 | 0x80000000, 1815 | 0x80000000, 0x80000000, 2, 0])
    stake_cred = Credential.from_key_hash(
        stake_key.get_public_key().to_ed25519_key().to_hash()
    )

    addrs = []
    for index in [0, 1]:
        payment_key = root_key.derive([1852 | 0x80000000, 1815 | 0x80000000, 0x80000000, 0, index])
        payment_cred = Credential.from_key_hash(
            payment_key.get_public_key().to_ed25519_key().to_hash()
        )
        addr = BaseAddress.from_credentials(1, payment_cred, stake_cred)
        addrs.append(str(addr))

    assert addrs[0] != addrs[1]
    assert all(a.startswith("addr1") for a in addrs)


def test_15_word_mnemonic_produces_valid_address():
    """15-word Daedalus-style mnemonic should produce a valid Cardano address."""
    mnemonic = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon address".split()
    root_key = _derive_root_key(mnemonic)

    payment_key = root_key.derive([1852 | 0x80000000, 1815 | 0x80000000, 0x80000000, 0, 0])
    payment_cred = Credential.from_key_hash(
        payment_key.get_public_key().to_ed25519_key().to_hash()
    )

    stake_key = root_key.derive([1852 | 0x80000000, 1815 | 0x80000000, 0x80000000, 2, 0])
    stake_cred = Credential.from_key_hash(
        stake_key.get_public_key().to_ed25519_key().to_hash()
    )

    addr = BaseAddress.from_credentials(1, payment_cred, stake_cred)
    assert str(addr).startswith("addr1")


def test_passphrase_changes_address():
    """Same mnemonic with different passphrase should produce different addresses."""
    mnemonic = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about".split()

    root_no_pass = _derive_root_key(mnemonic, passphrase="")
    root_with_pass = _derive_root_key(mnemonic, passphrase="test")

    for root, label in [(root_no_pass, "no-pass"), (root_with_pass, "with-pass")]:
        payment_key = root.derive([1852 | 0x80000000, 1815 | 0x80000000, 0x80000000, 0, 0])
        stake_key = root.derive([1852 | 0x80000000, 1815 | 0x80000000, 0x80000000, 2, 0])

    # Derive addresses for both
    def _get_addr(root):
        pk = root.derive([1852 | 0x80000000, 1815 | 0x80000000, 0x80000000, 0, 0])
        sk = root.derive([1852 | 0x80000000, 1815 | 0x80000000, 0x80000000, 2, 0])
        pc = Credential.from_key_hash(pk.get_public_key().to_ed25519_key().to_hash())
        sc = Credential.from_key_hash(sk.get_public_key().to_ed25519_key().to_hash())
        return str(BaseAddress.from_credentials(1, pc, sc))

    addr_no_pass = _get_addr(root_no_pass)
    addr_with_pass = _get_addr(root_with_pass)

    assert addr_no_pass != addr_with_pass
