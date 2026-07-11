"""
Cardano Account Public Key Export — request/response models and CBOR codec.

A host wallet requests one or more CIP-1852 account extended public keys over an
animated QR (UR type ``cardano-account-req``); the device replies with the
account xpub(s) plus the seed's master fingerprint over an animated QR (UR type
``cardano-account``).

The response mirrors the shape of Blockchain Commons ``crypto-multi-accounts``:
a single shared master fingerprint and a list of per-account key entries. The
master fingerprint is the **Bitcoin secp256k1 BIP-32** fingerprint
(``Seed.get_fingerprint()``) — chosen for parity with existing SeedSigners.
The client cannot compute it itself (it only ever sees the Ed25519 Cardano
xpub), so this export is how the client first learns it and can then stamp it
on future signing requests.

CDDL
----
    CardanoAccountRequest = {
        1: tstr,            ; request_id (UUID, echoed in the response)
      ? 2: tstr,            ; origin (wallet name, e.g. "Eternl")
        3: [* uint],        ; account_indices (one or more)
      ? 4: uint             ; key_purpose (default 1852 = CIP-1852)
    }

    CardanoAccountResponse = {
        1: tstr,            ; request_id (echoed; "" for menu-initiated export)
        2: bstr,            ; master_fingerprint (4 bytes, BTC BIP-32)
        3: [* AccountKey],  ; one entry per exported account
      ? 4: tstr             ; device_label
    }

    AccountKey = {
        1: uint,            ; account index
        2: bstr,            ; account xpub (64 bytes: 32 pubkey || 32 chaincode)
        3: [* uint]         ; derivation path, e.g. [1852', 1815', account']
    }
"""

from dataclasses import dataclass, field
from typing import Optional

from cometa import CborReader, CborWriter


PURPOSE_CIP1852 = 1852
COIN_TYPE_ADA = 1815
HARDENED_OFFSET = 0x80000000

DEFAULT_DEVICE_LABEL = "Cardano SeedSigner"


@dataclass
class CardanoAccountRequest:
    """A host request for one or more account extended public keys.

    UR type: ``cardano-account-req``.
    """
    request_id: str
    account_indices: list[int]
    key_purpose: int = PURPOSE_CIP1852
    origin: Optional[str] = None

    def to_cbor(self) -> bytes:
        w = CborWriter()
        num_entries = 3 + (1 if self.origin is not None else 0)
        w.write_start_map(num_entries)
        w.write_int(1)
        w.write_str(self.request_id)
        if self.origin is not None:
            w.write_int(2)
            w.write_str(self.origin)
        w.write_int(3)
        w.write_start_array(len(self.account_indices))
        for index in self.account_indices:
            w.write_int(index)
        w.write_int(4)
        w.write_int(self.key_purpose)
        return w.encode()

    @classmethod
    def from_cbor(cls, data: bytes) -> "CardanoAccountRequest":
        r = CborReader.from_bytes(data)
        request_id = None
        account_indices = None
        key_purpose = PURPOSE_CIP1852
        origin = None

        num_entries = r.read_map_len()
        for _ in range(num_entries):
            key = r.read_uint()
            if key == 1:
                request_id = r.read_str()
            elif key == 2:
                origin = r.read_str()
            elif key == 3:
                count = r.read_array_len()
                account_indices = [r.read_uint() for _ in range(count)]
                r.read_array_end()
            elif key == 4:
                key_purpose = r.read_uint()
            else:
                r.skip_value()
        r.read_map_end()

        if request_id is None:
            raise ValueError("cardano-account-req missing request_id (key 1)")
        if not account_indices:
            raise ValueError("cardano-account-req missing/empty account_indices (key 3)")

        return cls(
            request_id=request_id,
            account_indices=account_indices,
            key_purpose=key_purpose,
            origin=origin,
        )


@dataclass
class AccountKey:
    """One exported account: its index, 64-byte xpub, and derivation path."""
    account_index: int
    xpub: bytes
    path: list[int]


@dataclass
class CardanoAccountResponse:
    """The device's reply carrying account xpub(s) + master fingerprint.

    UR type: ``cardano-account``.
    """
    request_id: str
    master_fingerprint: bytes
    keys: list[AccountKey] = field(default_factory=list)
    device_label: str = DEFAULT_DEVICE_LABEL

    def to_cbor(self) -> bytes:
        w = CborWriter()
        w.write_start_map(4)
        w.write_int(1)
        w.write_str(self.request_id)
        w.write_int(2)
        w.write_bytes(self.master_fingerprint)
        w.write_int(3)
        w.write_start_array(len(self.keys))
        for account_key in self.keys:
            w.write_start_map(3)
            w.write_int(1)
            w.write_int(account_key.account_index)
            w.write_int(2)
            w.write_bytes(account_key.xpub)
            w.write_int(3)
            w.write_start_array(len(account_key.path))
            for component in account_key.path:
                w.write_int(component)
        w.write_int(4)
        w.write_str(self.device_label)
        return w.encode()

    @classmethod
    def from_cbor(cls, data: bytes) -> "CardanoAccountResponse":
        r = CborReader.from_bytes(data)
        request_id = ""
        master_fingerprint = None
        keys: list[AccountKey] = []
        device_label = DEFAULT_DEVICE_LABEL

        num_entries = r.read_map_len()
        for _ in range(num_entries):
            key = r.read_uint()
            if key == 1:
                request_id = r.read_str()
            elif key == 2:
                master_fingerprint = r.read_bytes()
            elif key == 3:
                count = r.read_array_len()
                for _ in range(count):
                    keys.append(cls._read_account_key(r))
                r.read_array_end()
            elif key == 4:
                device_label = r.read_str()
            else:
                r.skip_value()
        r.read_map_end()

        if master_fingerprint is None:
            raise ValueError("cardano-account missing master_fingerprint (key 2)")

        return cls(
            request_id=request_id,
            master_fingerprint=master_fingerprint,
            keys=keys,
            device_label=device_label,
        )

    @staticmethod
    def _read_account_key(r: CborReader) -> AccountKey:
        account_index = None
        xpub = None
        path = None
        num_entries = r.read_map_len()
        for _ in range(num_entries):
            key = r.read_uint()
            if key == 1:
                account_index = r.read_uint()
            elif key == 2:
                xpub = r.read_bytes()
            elif key == 3:
                count = r.read_array_len()
                path = [r.read_uint() for _ in range(count)]
                r.read_array_end()
            else:
                r.skip_value()
        r.read_map_end()
        if account_index is None or xpub is None or path is None:
            raise ValueError("cardano-account AccountKey missing a required field")
        return AccountKey(account_index=account_index, xpub=xpub, path=path)


def account_path(account_index: int, key_purpose: int = PURPOSE_CIP1852) -> list[int]:
    """CIP-1852 account derivation path: m/purpose'/1815'/account'."""
    return [
        key_purpose | HARDENED_OFFSET,
        COIN_TYPE_ADA | HARDENED_OFFSET,
        account_index | HARDENED_OFFSET,
    ]


def format_derivation_path(path: list[int]) -> str:
    """Render a derivation path list as text, e.g. ``m/1852'/1815'/0'``."""
    components = []
    for component in path:
        if component & HARDENED_OFFSET:
            components.append(f"{component ^ HARDENED_OFFSET}'")
        else:
            components.append(str(component))
    return "m/" + "/".join(components)


def derive_account_keys(seed, account_indices: list[int],
                        key_purpose: int = PURPOSE_CIP1852) -> list[AccountKey]:
    """Derive the account extended public key for each requested account.

    Returns one :class:`AccountKey` per index, with the 64-byte account xpub
    (``m/purpose'/1815'/account'``). A client soft-derives payment (role 0),
    stake (role 2), DRep (role 3) and addresses from these.
    """
    from seedsigner.helpers.cardano_utils import root_key_from_seed

    root_key = root_key_from_seed(seed)

    keys = []
    for account_index in account_indices:
        path = account_path(account_index, key_purpose)
        account_key = root_key.derive(path)
        xpub = account_key.get_public_key().to_bytes()
        keys.append(AccountKey(account_index=account_index, xpub=xpub, path=path))
    return keys


def build_account_response(seed, request_id: str, account_indices: list[int],
                           key_purpose: int = PURPOSE_CIP1852) -> CardanoAccountResponse:
    """Build a full response for a seed: derived account keys + master fingerprint.

    The master fingerprint is the Bitcoin BIP-32 fingerprint
    (``Seed.get_fingerprint()`` returns 8 hex chars = 4 bytes).
    """
    keys = derive_account_keys(seed, account_indices, key_purpose)
    master_fingerprint = bytes.fromhex(seed.get_fingerprint())
    return CardanoAccountResponse(
        request_id=request_id,
        master_fingerprint=master_fingerprint,
        keys=keys,
    )
