"""
Cardano-specific utilities for key derivation, change output verification,
and CIP-8 message signing address verification.

``CREDENTIAL_SHORT_LABEL`` maps a credential kind to the short type label
shown on the message signing overview screen.
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


HARDENED_OFFSET = 0x80000000

PURPOSE_CIP1852 = 1852
PURPOSE_CIP1854 = 1854
PURPOSE_MINTING = 1855

COIN_TYPE_ADA = 1815

ROLE_PAYMENT = 0
ROLE_CHANGE = 1
ROLE_STAKE = 2
ROLE_DREP = 3


def seed_fingerprint(seed) -> bytes:
    """The seed's 4-byte BTC BIP-32 master fingerprint.

    Matches the ``xfp`` values a host stamps on signing requests (from the
    account export), so a request's signer can be tied back to a loaded seed.
    """
    return bytes.fromhex(seed.get_fingerprint())


def asset_fingerprint(policy_id, asset_name) -> str:
    """The CIP-14 asset fingerprint (``asset1...``) for a native token.

    Computed as ``bech32("asset", blake2b_160(policy_id || asset_name))``.
    """
    from cometa import Blake2bHash, Bech32

    data = policy_id.to_bytes() + asset_name.to_bytes()
    h = Blake2bHash.compute(data, hash_size=20)
    return Bech32.encode("asset", h.to_bytes())


def format_percent(value) -> str:
    """Render a rational value as a percentage string.

    Whole percents drop the decimals (``5%``); fractional ones show two
    places (``2.75%``).
    """
    pct = float(value) * 100
    if pct == int(pct):
        return f"{int(pct)}%"
    return f"{pct:.2f}%"


def sanitize_origin(origin):
    """Strip non-printable chars and cap at 20 characters."""
    if not origin:
        return origin
    cleaned = "".join(c for c in origin if c.isprintable())
    if len(cleaned) > 20:
        cleaned = cleaned[:20] + "..."
    return cleaned or None


def path_purpose(path) -> int:
    """The unhardened purpose component of a derivation path, or ``None``."""
    if not path:
        return None
    return path[0] & ~HARDENED_OFFSET


def path_role(path) -> int:
    """The role component of a 5-component CIP-1852-style path, or ``None``.

    Unhardened: a hardened role (nonstandard, but host-controlled) still
    classifies by its role number rather than falling through to a default.
    """
    if path and len(path) > 3:
        return path[3] & ~HARDENED_OFFSET
    return None


def account_stake_path(path):
    """The account's standard stake key path for `path` (CIP-1852 role 2,
    index 0).

    Keeps the purpose/coin-type/account prefix of `path` and appends the
    fixed staking components (``ROLE_STAKE``, ``0``), so a base address is
    always verified against the account's default stake key. A base address
    using a non-default stake index therefore does not verify.
    """
    return list(path[:3]) + [ROLE_STAKE, 0]


def drep_id_from_key_hash(key_hash: bytes) -> str:
    """The CIP-129 DRep ID (``drep1...``) for a 28-byte DRep key hash."""
    from cometa import Blake2bHash, Credential, DRep, DRepType

    cred = Credential.from_key_hash(Blake2bHash.from_bytes(key_hash))
    return DRep.new(DRepType.KEY_HASH, cred).to_cip129_string()


CREDENTIAL_SHORT_LABEL = {
    "payment": "Payment",
    "stake": "Stake",
    "drep": "DRep",
    "multisig": "Multisig",
    "minting": "Minting",
    "unknown": "Unknown",
}


def classify_signing_credential(address_bytes, signing_path=None) -> str:
    """Classify a CIP-8 signing credential as ``payment`` / ``stake`` / ``drep``
    / ``multisig`` / ``minting`` / ``unknown``.

    The derivation-path purpose is checked first: a CIP-1854 (multisig) or
    CIP-1855 (minting policy) key must never be presented as a plain payment
    or stake address, because its on-chain identity is a script hash the
    device cannot compute. The role is the next signal (the signing intent),
    so a DRep (role 3) or stake key (role 2) is identified even when the
    credential is supplied as a type-6 enterprise wrapper that would otherwise
    look like a payment address. Falls back to the address structure when no
    path is given.
    """
    from cometa import Address, AddressType

    purpose = path_purpose(signing_path)
    if purpose == PURPOSE_CIP1854:
        return "multisig"
    if purpose == PURPOSE_MINTING:
        return "minting"

    role = path_role(signing_path)

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
        if role in (None, ROLE_DREP):
            return "drep"
        if role in (ROLE_PAYMENT, ROLE_CHANGE):
            return "payment"

    return "unknown"


def describe_signing_credential(address_bytes, signing_path=None) -> tuple:
    """Classify the CIP-8 signing credential for display as ``(label, value)``,
    e.g. ``("DRep ID:", "drep1...")``. Purpose- and role-aware (see
    :func:`classify_signing_credential`).

    A multisig (1854') or minting (1855') key is shown as its bare key hash in
    hex: the on-chain identity is a script address whose hash depends on the
    full policy, which the device does not have, so wrapping the key hash in
    an address would produce a valid-looking address that belongs to no
    wallet. Hex is also how coordinators show cosigner keys, so it is directly
    comparable on the host side.
    """
    from cometa import Address

    kind = classify_signing_credential(address_bytes, signing_path)
    role = path_role(signing_path)

    if kind in ("multisig", "minting"):
        key_hash = _credential_key_hash(address_bytes, role)
        if key_hash is None:
            return "Key Hash:", address_bytes.hex()
        return "Key Hash:", key_hash.hex()
    if kind == "drep":
        return "DRep ID:", drep_id_from_key_hash(_credential_key_hash(address_bytes))
    if kind in ("stake", "payment"):
        try:
            value = str(Address.from_bytes(address_bytes))
        except Exception:
            value = None
        if value is not None:
            label = "Stake Address:" if kind == "stake" else "Payment Address:"
            return label, value
        key_hash = _credential_key_hash(address_bytes, role)
        if key_hash is not None:
            return "Key Hash:", key_hash.hex()

    return "Address:", address_bytes.hex()


def _credential_key_hash(address_bytes, role=None):
    """The 28-byte credential key hash from a bare hash or an address wrapper
    (enterprise, base, reward); ``None`` if it can't be extracted.

    A base address holds two credentials: `role` selects the stake credential
    for a stake-role (2) signing key, the payment credential otherwise. A
    reward address always yields its stake credential.
    """
    if len(address_bytes) == 28:
        return address_bytes
    try:
        from cometa import Address
        addr = Address.from_bytes(address_bytes)
        enterprise = addr.to_enterprise_address()
        if enterprise is not None:
            return enterprise.payment_credential.hash.to_bytes()
        base = addr.to_base_address()
        if base is not None:
            cred = base.stake_credential if role == ROLE_STAKE else base.payment_credential
            return cred.hash.to_bytes()
        reward = addr.to_reward_address()
        if reward is not None:
            return reward.credential.hash.to_bytes()
    except Exception:
        pass
    return None


def _payment_key_credential_matches(addr, derived_payment_cred) -> bool:
    """Whether `addr`'s payment credential is a key hash equal to the derived
    payment credential's hash.

    Used for base addresses whose stake part is a script hash: the device
    cannot rebuild the whole address (it does not know the script), but
    ownership of the payment credential is still provable. Any shape that
    cannot be positively checked returns False.
    """
    from cometa import CredentialType

    try:
        base = addr.to_base_address()
        if base is None:
            return False
        payment_cred = base.payment_credential
        if payment_cred.type != CredentialType.KEY_HASH:
            return False
        return payment_cred.hash.to_bytes() == derived_payment_cred.hash.to_bytes()
    except Exception:
        return False


def _derived_credential(root_key, path):
    """The key-hash :class:`Credential` derived from `path` under `root_key`.

    Hashes the derived Ed25519 public key to a Blake2b-224 key hash and wraps
    it as a key-hash credential, the payment/stake credential form used when
    rebuilding an address for ownership comparison.
    """
    from cometa import Credential

    key = root_key.derive(path)
    return Credential.from_key_hash(key.get_public_key().to_ed25519_key().to_hash())


def _rebuilt_address_matches(root_key, path, network_id, addr, addr_type, target):
    """Whether the key-credential address rebuilt from `path` equals `target`.

    Dispatches on the CIP-19 address type: an all-key base address takes its
    payment credential from `path` and its stake credential from the
    account's standard stake key (:func:`account_stake_path`); an enterprise
    key address uses the payment credential only; both are rebuilt at
    `network_id` and compared to `target` as strings. A base address whose
    stake part is a script cannot be rebuilt (the script is not derivable),
    so it is matched on its payment credential alone, after confirming the
    address's network id equals `network_id`.

    Returns ``None`` for any other address type, leaving the outcome to the
    caller. Fail-safe: a derivation or comparison failure returns False.
    """
    from cometa import AddressType, BaseAddress, EnterpriseAddress

    handled = {
        AddressType.BASE_PAYMENT_KEY_STAKE_KEY,
        AddressType.BASE_PAYMENT_KEY_STAKE_SCRIPT,
        AddressType.ENTERPRISE_KEY,
    }
    if addr_type not in handled:
        return None

    try:
        payment_cred = _derived_credential(root_key, path)

        if addr_type == AddressType.BASE_PAYMENT_KEY_STAKE_SCRIPT:
            if addr.network_id != network_id:
                return False
            return _payment_key_credential_matches(addr, payment_cred)

        if addr_type == AddressType.BASE_PAYMENT_KEY_STAKE_KEY:
            stake_cred = _derived_credential(root_key, account_stake_path(path))
            derived_addr = BaseAddress.from_credentials(network_id, payment_cred, stake_cred)
            return str(derived_addr) == target

        derived_addr = EnterpriseAddress.from_credentials(network_id, payment_cred)
        return str(derived_addr) == target
    except Exception:
        return False


def _derived_address_matches(root_key, path, network_id, actual_addr) -> bool:
    """Whether the address derived from `path` equals `actual_addr`.

    Supports BaseAddress (payment key from the full path + staking key from
    the same account's 2/0 path) and EnterpriseAddress (payment key only);
    the actual address's type selects the derivation. A base address with a
    script stake part is matched on its payment credential alone, since the
    stake script is not derivable from the seed. Any other address type
    (pointer, reward, script-payment, byron), a parse failure, or a path
    that cannot be derived returns False.
    """
    from cometa import Address, AddressType

    try:
        parsed = Address.from_string(actual_addr)
        addr_type = AddressType(parsed.type)
    except Exception:
        return False

    return bool(
        _rebuilt_address_matches(root_key, path, network_id, parsed, addr_type, actual_addr)
    )


def verify_change_outputs(sign_request, seed, body) -> list[int]:
    """Verify which claimed change outputs actually belong to this wallet.

    Derives addresses from the paths in sign_request.change_outputs using
    the seed's mnemonic and the sign request's declared network, then
    compares against the actual output addresses in the transaction body.

    If an output's address doesn't match the derived address (wrong network,
    wrong keys, unsupported address type, etc.), it is not included; safe
    failure mode: unverified outputs are treated as external (user sees
    inflated spending amount). An entry whose index falls outside the body's
    output list or whose path cannot be derived is skipped the same way
    rather than failing the request.

    Base addresses are verified against the account's standard stake key
    (role 2, index 0), so a base address using a non-default stake index is
    treated as unverified.

    Returns a list of output indices that are verified as change.
    """
    root_key = root_key_from_seed(seed)
    network_id = sign_request.network
    output_count = len(body.outputs)
    verified = []

    for change_output in sign_request.change_outputs:
        if not 0 <= change_output.index < output_count:
            continue
        actual_addr = str(body.outputs[change_output.index].address)
        if _derived_address_matches(root_key, change_output.path, network_id, actual_addr):
            verified.append(change_output.index)

    return verified


def verify_collateral_return(sign_request, seed, body) -> bool:
    """Verify that the body's collateral_return output belongs to this wallet.

    The request's optional collateral_return_path declares the derivation
    path; the derived address must equal the collateral_return address and
    the declared xfp must match the selected seed. Absent field, absent
    collateral_return, or any mismatch returns False; the collateral return
    is then displayed as an external output (safe failure mode).
    """
    crp = sign_request.collateral_return_path
    if crp is None or body.collateral_return is None:
        return False
    if crp.xfp != seed_fingerprint(seed):
        return False

    root_key = root_key_from_seed(seed)
    actual_addr = str(body.collateral_return.address)
    return _derived_address_matches(root_key, crp.path, sign_request.network, actual_addr)


def derive_owned_key_hashes(sign_request, seed) -> set:
    """Blake2b-224 hashes of every public key derivable from the request's
    declared paths (inputs, extra signers, change outputs, collateral return)
    for the selected seed.

    Since each hash is computed on-device from the seed itself, membership is
    cryptographic proof that a credential hash appearing in the transaction
    (certificates, withdrawals, required signers, voters) belongs to this
    wallet; a host cannot make a foreign credential match by declaring
    extra paths. A declared path that cannot be derived contributes no hash
    and is skipped, so one malformed entry does not fail the request.
    """
    fingerprint = seed_fingerprint(seed)

    paths = set()
    for signing_input in sign_request.inputs:
        if signing_input.path is not None and signing_input.xfp == fingerprint:
            paths.add(tuple(signing_input.path))
    for extra_signer in sign_request.extra_signers:
        if extra_signer.xfp == fingerprint:
            paths.add(tuple(extra_signer.path))
    for change_output in sign_request.change_outputs:
        if change_output.xfp in (b"", fingerprint):
            paths.add(tuple(change_output.path))
    if sign_request.collateral_return_path is not None:
        if sign_request.collateral_return_path.xfp == fingerprint:
            paths.add(tuple(sign_request.collateral_return_path.path))

    root_key = root_key_from_seed(seed)
    hashes = set()
    for path in paths:
        try:
            key = root_key.derive(list(path))
        except Exception:
            continue
        hashes.add(key.get_public_key().to_ed25519_key().to_hash().to_bytes())
    return hashes


def verify_message_signing_address(msg_request, seed) -> bool:
    """Verify that the signing path matches the address in a CIP-8 request.

    For base/enterprise addresses, derives the payment key from the signing
    path and verifies it matches the payment credential in the address. Base
    addresses are verified against the account's standard stake key (role 2,
    index 0), so a base address using a non-default stake index is treated
    as unverified. A base address with a script stake part is matched on its
    payment credential alone, since the stake script is not derivable from
    the seed.
    For reward addresses, derives the staking key and verifies the stake
    credential.
    For DRep credentials (28-byte raw key hash), compares directly against
    the derived key hash.

    Parses the bytes as a standard Cardano address first; if that fails and
    the value is 28 bytes, treats it as a bare DRep key hash. For base
    addresses the payment credential comes from the signing path and the
    stake credential from the same account (role 2, index 0).

    Returns True if the address matches or if no address is provided.
    Returns False if verification fails (wrong key, unknown address type).
    """
    from cometa import Address, AddressType, RewardAddress

    if msg_request.address_bytes is None:
        return True

    root_key = root_key_from_seed(seed)
    path = msg_request.required_signing_path.path

    try:
        addr = Address.from_bytes(msg_request.address_bytes)
        addr_type = AddressType(addr.type)
        network_id = addr.network_id
    except Exception:
        if len(msg_request.address_bytes) == 28:
            return _verify_drep_credential(root_key, path, msg_request.address_bytes)
        return False

    result = _rebuilt_address_matches(root_key, path, network_id, addr, addr_type, str(addr))
    if result is not None:
        return result

    if addr_type == AddressType.REWARD_KEY:
        try:
            derived_addr = RewardAddress.from_credentials(
                network_id, _derived_credential(root_key, path)
            )
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
