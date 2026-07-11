"""Watch-only wallet derived from an account extended public key.

Given only the 64-byte account xpub (m/1852'/1815'/account') the host soft-
derives payment/stake keys, builds addresses, and maps a transaction's required
signers to the full derivation paths the device must sign with. No private keys.
"""

from . import _paths  # noqa: F401

from cometa import (
    Bip32PublicKey,
    Credential,
    BaseAddress,
    EnterpriseAddress,
    RewardAddress,
    NetworkId,
)

HARDENED = 0x80000000
PURPOSE_CIP1852 = 1852
COIN_TYPE_ADA = 1815

ROLE_PAYMENT = 0
ROLE_STAKE = 2
ROLE_DREP = 3


class WatchOnlyWallet:
    def __init__(self, account_xpub: bytes, master_fingerprint: bytes,
                 account_index: int = 0, network: NetworkId = NetworkId.TESTNET,
                 purpose: int = PURPOSE_CIP1852):
        self.account_xpub = Bip32PublicKey.from_bytes(account_xpub)
        self.master_fingerprint = master_fingerprint
        self.account_index = account_index
        self.network = network
        self.purpose = purpose

        self._payment = self.account_xpub.derive([ROLE_PAYMENT, 0])
        self._stake = self.account_xpub.derive([ROLE_STAKE, 0])
        self._drep = self.account_xpub.derive([ROLE_DREP, 0])

        self._payment_hash = self._payment.to_ed25519_key().to_hash()
        self._stake_hash = self._stake.to_ed25519_key().to_hash()
        self._drep_hash = self._drep.to_ed25519_key().to_hash()

    def _full_path(self, role: int, index: int = 0):
        return [
            self.purpose | HARDENED,
            COIN_TYPE_ADA | HARDENED,
            self.account_index | HARDENED,
            role,
            index,
        ]

    def base_address(self) -> BaseAddress:
        return BaseAddress.from_credentials(
            self.network,
            Credential.from_key_hash(self._payment_hash),
            Credential.from_key_hash(self._stake_hash),
        )

    def enterprise_address(self) -> EnterpriseAddress:
        return EnterpriseAddress.from_credentials(
            self.network, Credential.from_key_hash(self._payment_hash))

    def reward_address(self) -> RewardAddress:
        return RewardAddress.from_credentials(
            self.network, Credential.from_key_hash(self._stake_hash))

    def address_bech32(self) -> str:
        return self.base_address().to_bech32()

    def base_address_bytes(self) -> bytes:
        return self.base_address().to_bytes()

    def payment_key_hash_hex(self) -> str:
        return self._payment_hash.to_hex()

    def stake_key_hash_hex(self) -> str:
        return self._stake_hash.to_hex()

    def drep_key_hash_hex(self) -> str:
        return self._drep_hash.to_hex()

    def reward_address_bytes(self) -> bytes:
        return self.reward_address().to_bytes()

    def drep_credential_bytes(self) -> bytes:
        return self._drep_hash.to_bytes()

    def stake_signing_path(self) -> list:
        return self._full_path(ROLE_STAKE, 0)

    def drep_signing_path(self) -> list:
        return self._full_path(ROLE_DREP, 0)

    def signing_paths_for(self, key_hashes) -> list:
        """Map a set of required signer key-hashes to derivation paths.

        Only hashes this wallet owns are returned; the rest belong to other
        keys/devices. NOTE: this example wallet only tracks the **index-0**
        payment (role 0) and stake (role 2) keys; a required signer at another
        address index, DRep (role 3), or another account would be missed.
        """
        owned = []
        payment_hex = self._payment_hash.to_hex()
        stake_hex = self._stake_hash.to_hex()
        for key_hash in key_hashes:
            h = key_hash.to_hex() if hasattr(key_hash, "to_hex") else key_hash
            if h == payment_hex:
                owned.append(self._full_path(ROLE_PAYMENT, 0))
            elif h == stake_hex:
                owned.append(self._full_path(ROLE_STAKE, 0))
        return owned

    def payment_signing_path(self) -> list:
        return self._full_path(ROLE_PAYMENT, 0)
