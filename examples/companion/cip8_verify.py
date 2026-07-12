"""External CIP-8 / COSE_Sign1 verification.

cometa exposes CIP-8 signing but no verification, so the host reconstructs the
COSE ``Sig_structure`` and checks the Ed25519 signature against the public key in
the returned COSE_Key. Used to prove the device's message signature is valid.
"""

from . import _paths  # noqa: F401

import cbor2

from cometa import Ed25519PublicKey, Ed25519Signature

COSE_KEY_X = -2  # COSE_Key map label for the public key bytes (OKP curve)


def public_key_from_cose_key(cose_key: bytes) -> bytes:
    key_map = cbor2.loads(cose_key)
    return key_map[COSE_KEY_X]


def cose_key_hash_hex(cose_key: bytes) -> str:
    """Blake2b-224 hash (hex) of the public key inside a COSE_Key.

    Lets the host confirm the device signed with the key it expected (i.e. the
    one that owns the reviewed address) rather than an arbitrary key.
    """
    pub = Ed25519PublicKey.from_bytes(public_key_from_cose_key(cose_key))
    return pub.to_hash().to_hex()


def verify_cose_sign1(cose_sign1: bytes, cose_key: bytes) -> bool:
    """Verify a COSE_Sign1 (CIP-8, hashed=false, empty external_aad).

    Checks the signature against the public key embedded in ``cose_key``, so a
    True result proves self-consistency only: any key can produce a pair that
    passes. To prove origin, callers must also compare
    ``cose_key_hash_hex(cose_key)`` (or the raw public key) to the expected
    wallet credential.
    """
    protected, _unprotected, payload, signature = cbor2.loads(cose_sign1)

    sig_structure = cbor2.dumps(["Signature1", protected, b"", payload])

    pub = Ed25519PublicKey.from_bytes(public_key_from_cose_key(cose_key))
    sig = Ed25519Signature.from_bytes(signature)
    return pub.verify(sig, sig_structure)


def signed_payload(cose_sign1: bytes) -> bytes:
    """The message bytes that were signed (the COSE_Sign1 payload field)."""
    _protected, _unprotected, payload, _signature = cbor2.loads(cose_sign1)
    return payload
