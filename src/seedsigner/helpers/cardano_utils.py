"""
Cardano-specific utilities for key derivation and change output verification.
"""


def verify_change_outputs(sign_request, seed, body) -> list[int]:
    """Verify which claimed change outputs actually belong to this wallet.

    Derives addresses from the paths in sign_request.change_outputs using
    the seed's mnemonic, then compares against the actual output addresses
    in the transaction body.

    Returns a list of output indices that are verified as change.
    """
    from cometa import (
        Bip32PrivateKey,
        BaseAddress,
        Credential,
        NetworkId,
        mnemonic_to_entropy,
    )

    entropy = mnemonic_to_entropy(seed.mnemonic_list)
    root_key = Bip32PrivateKey.from_bip39_entropy(b"", entropy)
    verified = []

    for change_output in sign_request.change_outputs:
        path = change_output.path
        # Derive payment key from full path
        key = root_key.derive(path)
        payment_cred = Credential.from_key_hash(
            key.get_public_key().to_ed25519_key().to_hash()
        )

        # Derive stake key: same account (path[:3]) + [2, 0]
        stake_path = list(path[:3]) + [2, 0]
        stake_key = root_key.derive(stake_path)
        stake_cred = Credential.from_key_hash(
            stake_key.get_public_key().to_ed25519_key().to_hash()
        )

        # Detect network from output address
        actual_addr = str(body.outputs[change_output.index].address)
        network_id = NetworkId.MAINNET if actual_addr.startswith("addr1") else NetworkId.TESTNET

        derived_addr = BaseAddress.from_credentials(network_id, payment_cred, stake_cred)
        if str(derived_addr) == actual_addr:
            verified.append(change_output.index)

    return verified
