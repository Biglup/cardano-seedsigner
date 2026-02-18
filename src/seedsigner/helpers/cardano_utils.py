"""
Cardano-specific utilities for key derivation and change output verification.
"""


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
        Bip32PrivateKey,
        Address,
        AddressType,
        BaseAddress,
        EnterpriseAddress,
        Credential,
        mnemonic_to_entropy,
    )

    # Address types we can verify
    BASE_TYPES = {
        AddressType.BASE_PAYMENT_KEY_STAKE_KEY,
        AddressType.BASE_PAYMENT_KEY_STAKE_SCRIPT,
    }
    ENTERPRISE_TYPES = {
        AddressType.ENTERPRISE_KEY,
    }

    entropy = mnemonic_to_entropy(seed.mnemonic_list)
    root_key = Bip32PrivateKey.from_bip39_entropy(b"", entropy)
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
