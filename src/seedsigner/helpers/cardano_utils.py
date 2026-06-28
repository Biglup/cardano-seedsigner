"""
Cardano-specific utilities for key derivation, change output verification,
and CIP-8 message signing address verification.
"""


def root_key_from_seed(seed):
    """Derive the Cardano CIP-1852 BIP32 root private key from a loaded Seed.

    Single source of truth for seed -> root key (entropy + optional passphrase),
    shared by change-output verification, message-address verification, and the
    signing core, so the derivation can never drift between them.
    """
    from cometa import Bip32PrivateKey, mnemonic_to_entropy

    entropy = mnemonic_to_entropy(seed.mnemonic_list)
    passphrase_bytes = seed.passphrase.encode("utf-8") if seed.passphrase else b""
    return Bip32PrivateKey.from_bip39_entropy(passphrase_bytes, entropy)


ROLE_STAKE = 2
ROLE_DREP = 3


def drep_id_from_key_hash(key_hash: bytes) -> str:
    """The CIP-129 DRep ID (``drep1...``) for a 28-byte DRep key hash."""
    from cometa import Blake2bHash, Credential, DRep, DRepType

    cred = Credential.from_key_hash(Blake2bHash.from_bytes(key_hash))
    return DRep.new(DRepType.KEY_HASH, cred).to_cip129_string()


# Short type label shown on the overview screen, keyed by credential kind.
CREDENTIAL_SHORT_LABEL = {
    "payment": "Payment",
    "stake": "Stake",
    "drep": "DRep",
    "unknown": "Unknown",
}


def classify_signing_credential(address_bytes, signing_path=None) -> str:
    """Classify a CIP-8 signing credential as ``payment`` / ``stake`` / ``drep``
    / ``unknown``.

    The derivation-path role is the primary signal (the signing intent), so a
    DRep (role 3) or stake key (role 2) is identified even when the credential is
    supplied as a type-6 enterprise wrapper that would otherwise look like a
    payment address. Falls back to the address structure when no path is given.
    """
    from cometa import Address, AddressType

    role = signing_path[3] if signing_path and len(signing_path) > 3 else None

    if role == ROLE_DREP and _credential_key_hash(address_bytes) is not None:
        return "drep"
    if role == ROLE_STAKE:
        return "stake"

    try:
        addr = Address.from_bytes(address_bytes)
        if addr.type in (AddressType.REWARD_KEY, AddressType.REWARD_SCRIPT):
            return "stake"
        return "payment"
    except Exception:
        pass

    if len(address_bytes) == 28:
        return "drep"

    return "unknown"


def describe_signing_credential(address_bytes, signing_path=None) -> tuple:
    """Classify the CIP-8 signing credential for display as ``(label, value)``,
    e.g. ``("DRep ID:", "drep1...")``. Role-aware (see
    :func:`classify_signing_credential`)."""
    from cometa import Address

    kind = classify_signing_credential(address_bytes, signing_path)

    if kind == "drep":
        return "DRep ID:", drep_id_from_key_hash(_credential_key_hash(address_bytes))
    if kind == "stake":
        return "Stake Address:", str(Address.from_bytes(address_bytes))
    if kind == "payment":
        return "Payment Address:", str(Address.from_bytes(address_bytes))

    return "Address:", address_bytes.hex()


def _credential_key_hash(address_bytes):
    """The 28-byte credential key hash from a bare hash or a type-6 enterprise
    address wrapper; ``None`` if it can't be extracted."""
    if len(address_bytes) == 28:
        return address_bytes
    try:
        from cometa import Address
        enterprise = Address.from_bytes(address_bytes).to_enterprise_address()
        if enterprise is not None:
            return enterprise.payment_credential.hash.to_bytes()
    except Exception:
        pass
    return None


def verify_change_outputs(sign_request, seed, body) -> list[int]:
    """Verify which claimed change outputs actually belong to this wallet.

    Derives addresses from the paths in sign_request.change_outputs using
    the seed's mnemonic and the sign request's declared network, then
    compares against the actual output addresses in the transaction body.

    Supports BaseAddress (payment + staking key) and EnterpriseAddress
    (payment key only). The actual output address type is detected and
    the matching derivation is used for comparison.

    If an output's address doesn't match the derived address (wrong network,
    wrong keys, etc.), it is not included — safe failure mode: unverified
    outputs are treated as external (user sees inflated spending amount).

    Returns a list of output indices that are verified as change.
    """
    from cometa import (
        Address,
        AddressType,
        BaseAddress,
        EnterpriseAddress,
        Credential,
    )

    # Address types we can verify
    BASE_TYPES = {
        AddressType.BASE_PAYMENT_KEY_STAKE_KEY,
        AddressType.BASE_PAYMENT_KEY_STAKE_SCRIPT,
    }
    ENTERPRISE_TYPES = {
        AddressType.ENTERPRISE_KEY,
    }

    root_key = root_key_from_seed(seed)
    network_id = sign_request.network
    verified = []

    for change_output in sign_request.change_outputs:
        path = change_output.path
        # Derive payment key from full path
        key = root_key.derive(path)
        payment_cred = Credential.from_key_hash(
            key.get_public_key().to_ed25519_key().to_hash()
        )

        actual_output = body.outputs[change_output.index]
        actual_addr = str(actual_output.address)

        # Detect the address type to choose the right derivation
        try:
            parsed = Address.from_string(actual_addr)
            addr_type = AddressType(parsed.type)
        except Exception:
            continue

        if addr_type in BASE_TYPES:
            # Base address: needs payment + staking credentials
            stake_path = list(path[:3]) + [2, 0]
            stake_key = root_key.derive(stake_path)
            stake_cred = Credential.from_key_hash(
                stake_key.get_public_key().to_ed25519_key().to_hash()
            )
            derived_addr = BaseAddress.from_credentials(network_id, payment_cred, stake_cred)
            if str(derived_addr) == actual_addr:
                verified.append(change_output.index)

        elif addr_type in ENTERPRISE_TYPES:
            # Enterprise address: payment credential only
            derived_addr = EnterpriseAddress.from_credentials(network_id, payment_cred)
            if str(derived_addr) == actual_addr:
                verified.append(change_output.index)

        # Other types (pointer, reward, script-based, byron) are not
        # verifiable as change — they are treated as external sends.

    return verified


def verify_message_signing_address(msg_request, seed) -> bool:
    """Verify that the signing path matches the address in a CIP-8 request.

    For base/enterprise addresses, derives the payment key from the signing
    path and verifies it matches the payment credential in the address.
    For reward addresses, derives the staking key and verifies the stake
    credential.
    For DRep credentials (28-byte raw key hash), compares directly against
    the derived key hash.

    Returns True if the address matches or if no address is provided.
    Returns False if verification fails (wrong key, unknown address type).
    """
    from cometa import (
        Address,
        AddressType,
        BaseAddress,
        EnterpriseAddress,
        RewardAddress,
        Credential,
    )

    if msg_request.address_bytes is None:
        return True

    root_key = root_key_from_seed(seed)
    path = msg_request.required_signing_path.path

    # Try standard Cardano address first
    try:
        addr = Address.from_bytes(msg_request.address_bytes)
        addr_type = AddressType(addr.type)
        network_id = addr.network_id
    except Exception:
        # Not a standard address — try DRep credential (28-byte key hash)
        if len(msg_request.address_bytes) == 28:
            return _verify_drep_credential(root_key, path, msg_request.address_bytes)
        return False

    BASE_TYPES = {
        AddressType.BASE_PAYMENT_KEY_STAKE_KEY,
        AddressType.BASE_PAYMENT_KEY_STAKE_SCRIPT,
    }
    ENTERPRISE_TYPES = {
        AddressType.ENTERPRISE_KEY,
    }
    REWARD_TYPES = {
        AddressType.REWARD_KEY,
    }

    try:
        key = root_key.derive(path)
        derived_cred = Credential.from_key_hash(
            key.get_public_key().to_ed25519_key().to_hash()
        )

        if addr_type in BASE_TYPES:
            # Payment credential from signing path + stake from same account
            stake_path = list(path[:3]) + [2, 0]
            stake_key = root_key.derive(stake_path)
            stake_cred = Credential.from_key_hash(
                stake_key.get_public_key().to_ed25519_key().to_hash()
            )
            derived_addr = BaseAddress.from_credentials(network_id, derived_cred, stake_cred)
            return str(derived_addr) == str(addr)

        elif addr_type in ENTERPRISE_TYPES:
            derived_addr = EnterpriseAddress.from_credentials(network_id, derived_cred)
            return str(derived_addr) == str(addr)

        elif addr_type in REWARD_TYPES:
            derived_addr = RewardAddress.from_credentials(network_id, derived_cred)
            return str(derived_addr) == str(addr)

    except Exception:
        return False

    return False


def _verify_drep_credential(root_key, path, credential_bytes):
    """Verify a 28-byte DRep credential matches the derived key."""
    try:
        key = root_key.derive(path)
        derived_hash = key.get_public_key().to_ed25519_key().to_hash()
        return derived_hash.to_bytes() == credential_bytes
    except Exception:
        return False
