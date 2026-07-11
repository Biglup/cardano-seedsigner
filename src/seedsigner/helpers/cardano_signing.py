"""
Cardano on-device signing core.

Pure crypto, no GUI/IO. Replicates cometa's
``SoftwareBip32SecureKeyHandler.sign_transaction`` (derive Ed25519 key per path,
sign the transaction-body hash, build a ``VkeyWitnessSet``) and uses
``cip8_sign`` for CIP-8 message signing.

Each signer in a request carries the master fingerprint (``xfp``). Given one
selected seed, only the signers whose ``xfp`` matches that seed's fingerprint are
signed here; the rest are left for another device/seed (partial witness set).
"""

from seedsigner.helpers.cardano_utils import (
    root_key_from_seed,
    verify_message_signing_address,
)
from seedsigner.models.cardano_tx import (
    CardanoSignRequest,
    CardanoTxSignResponse,
    CardanoMessageSignRequest,
    CardanoCip8SignResponse,
)


def _seed_fingerprint(seed) -> bytes:
    """The seed's 4-byte BTC BIP-32 master fingerprint (matches request xfp values)."""
    return bytes.fromhex(seed.get_fingerprint())


def _dedupe_paths(paths: list[list[int]]) -> list[list[int]]:
    """Remove duplicate derivation paths, preserving first-seen order.

    Two signers on the same path produce the same vkey witness; signing once
    avoids emitting a duplicate witness.
    """
    seen = set()
    unique = []
    for path in paths:
        key = tuple(path)
        if key not in seen:
            seen.add(key)
            unique.append(path)
    return unique


def matching_signing_paths(request: CardanoSignRequest, seed) -> list[list[int]]:
    """The derivation paths in `request` that belong to `seed` (by xfp), deduped.

    Script-locked inputs carry no path (their witnesses arrive via
    ``extra_signers``) and are skipped.
    """
    fingerprint = _seed_fingerprint(seed)
    candidates = [si.path for si in request.inputs
                  if si.path is not None and si.xfp == fingerprint]
    candidates += [es.path for es in request.extra_signers if es.xfp == fingerprint]
    return _dedupe_paths(candidates)


def sign_tx_body(seed, body_cbor: bytes, paths: list[list[int]]) -> bytes:
    """Sign a transaction-body hash with each path; return the VkeyWitnessSet CBOR.

    The hash signed is ``blake2b-256(body)`` — the transaction id — exactly as
    cometa's key handler does.
    """
    from cometa import (
        CborReader,
        CborWriter,
        TransactionBody,
        VkeyWitness,
        VkeyWitnessSet,
    )

    body = TransactionBody.from_cbor(CborReader.from_bytes(body_cbor))
    tx_hash = body.hash.to_bytes()

    root_key = root_key_from_seed(seed)
    witnesses = []
    for path in paths:
        signing_key = root_key.derive(path)
        vkey = signing_key.get_public_key().to_ed25519_key().to_bytes()
        signature = signing_key.to_ed25519_key().sign(tx_hash).to_bytes()
        witnesses.append(VkeyWitness.new(vkey=vkey, signature=signature))

    witness_set = VkeyWitnessSet.from_list(witnesses)
    writer = CborWriter()
    witness_set.to_cbor(writer)
    return writer.encode()


def build_tx_sign_response(seed, request: CardanoSignRequest) -> CardanoTxSignResponse:
    """Produce the device's witness response for a tx sign request and one seed.

    Only signers whose xfp matches the seed are signed (partial witness set is
    valid for multi-seed / cross-device multisig).
    """
    paths = matching_signing_paths(request, seed)
    witness_set_cbor = sign_tx_body(seed, request.sign_data, paths)
    return CardanoTxSignResponse(
        request_id=request.request_id,
        vkey_witness_set=witness_set_cbor,
    )


ALG_EDDSA = -8
COSE_KEY_TYPE_OKP = 1
COSE_CRV_ED25519 = 6


def sign_cip8(seed, message: bytes, address_bytes: bytes, path: list[int]) -> tuple:
    """Produce a CIP-8 COSE_Sign1 + COSE_Key for `message` bound to `address_bytes`.

    `address_bytes` is the signing context bound under the COSE ``"address"``
    header: a full Cardano address (payment / stake-reward) or a bare credential
    key hash (e.g. a DRep). Every case uses the Ledger / Keystone wire format —
    a 2-field protected header ``{1: alg, "address": address_bytes}`` (NO ``kid``)
    — for parity with the dominant Cardano hardware wallets and CIP-95 dApps.

    cometa's native ``cip8_sign`` / ``cip8_sign_with_key_hash`` are deliberately
    NOT used: they emit a non-interoperable header (an extra ``kid``, and a
    ``"keyHash"`` label for key hashes). See ``_sign_cip8_ledger``.

    TODO(upstream): fix libcardano-c ``lib/src/message_signing/cip8.c`` to emit
    the Ledger-parity headers (2-field ``"address"``, no ``kid``); once released
    in cometa this hand-rolled COSE can be replaced by ``cip8_sign*``.
    Tracked at: https://github.com/Biglup/cardano-c/issues/122

    Returns ``(cose_sign1, cose_key)`` as bytes.
    """
    derived = root_key_from_seed(seed).derive(path)
    signing_key = derived.to_ed25519_key()
    pubkey = derived.get_public_key().to_ed25519_key().to_bytes()
    return _sign_cip8_ledger(signing_key, message, address_bytes, pubkey)


def _sign_cip8_ledger(signing_key, message: bytes, address_field: bytes, pubkey: bytes) -> tuple:
    """Build a COSE_Sign1 + COSE_Key in the Ledger / Keystone CIP-8 wire format.

    Protected header is the 2-field map ``{1: alg, "address": address_field}``
    (no ``kid``), unprotected header is ``{"hashed": false}``, the signature is
    over the COSE ``Sig_structure``, and the COSE_Key ``kid`` is ``address_field``.
    ``address_field`` is a full address (payment/stake) or a bare key hash (DRep).
    Mirrors Ledger app-cardano signMsg.c / Keystone cip8_cbor_data_ledger.rs.
    """
    from cometa import CborWriter

    protected = CborWriter()
    protected.write_start_map(2)
    protected.write_int(1)
    protected.write_int(ALG_EDDSA)
    protected.write_str("address")
    protected.write_bytes(address_field)
    protected_bytes = protected.encode()

    sig_structure = CborWriter()
    sig_structure.write_start_array(4)
    sig_structure.write_str("Signature1")
    sig_structure.write_bytes(protected_bytes)
    sig_structure.write_bytes(b"")
    sig_structure.write_bytes(message)
    signature = signing_key.sign(sig_structure.encode()).to_bytes()

    cose_sign1 = CborWriter()
    cose_sign1.write_start_array(4)
    cose_sign1.write_bytes(protected_bytes)
    cose_sign1.write_start_map(1)
    cose_sign1.write_str("hashed")
    cose_sign1.write_bool(False)
    cose_sign1.write_bytes(message)
    cose_sign1.write_bytes(signature)

    cose_key = CborWriter()
    cose_key.write_start_map(5)
    cose_key.write_int(1)
    cose_key.write_int(COSE_KEY_TYPE_OKP)
    cose_key.write_int(2)
    cose_key.write_bytes(address_field)
    cose_key.write_int(3)
    cose_key.write_int(ALG_EDDSA)
    cose_key.write_int(-1)
    cose_key.write_int(COSE_CRV_ED25519)
    cose_key.write_int(-2)
    cose_key.write_bytes(pubkey)

    return cose_sign1.encode(), cose_key.encode()


def build_cip8_sign_response(seed, request: CardanoMessageSignRequest) -> CardanoCip8SignResponse:
    """Produce the device's CIP-8 signature response for one seed.

    Enforces the signer-confusion guards: the request's xfp (if present) must
    match the selected seed, and the signing key derived from the request path
    must actually correspond to the address the signature is bound to — otherwise
    a malicious host could obtain a signature bound to an address the user
    reviewed but signed with an unrelated key.
    """
    if request.xfp and request.xfp != _seed_fingerprint(seed):
        raise ValueError("cip8 sign request xfp does not match the selected seed")
    if not request.address_bytes:
        raise ValueError("cip8 sign request is missing the address to bind to")
    if not verify_message_signing_address(request, seed):
        raise ValueError("cip8 signing path does not match the bound address")

    cose_sign1, cose_key = sign_cip8(
        seed,
        request.message_payload,
        request.address_bytes,
        request.required_signing_path.path,
    )
    return CardanoCip8SignResponse(
        request_id=request.request_id,
        cose_sign1=cose_sign1,
        cose_key=cose_key,
    )
