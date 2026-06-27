"""Build and parse the six Cardano UR messages, reusing the device's codecs.

The host encodes *requests* and decodes *responses*; the device does the
reverse. Both sides import the same ``to_cbor``/``from_cbor`` so the wire format
is defined in exactly one place.
"""

from . import _paths  # noqa: F401  (sys.path side effect)

from seedsigner.helpers.ur2.ur import UR
from seedsigner.helpers.ur2.ur_encoder import UREncoder
from seedsigner.helpers.ur2.ur_decoder import URDecoder
from seedsigner.models.cardano_account import (
    CardanoAccountRequest,
    CardanoAccountResponse,
)
from seedsigner.models.cardano_tx import (
    CardanoSignRequest,
    CardanoTxSignResponse,
    CardanoMessageSignRequest,
    CardanoCip8SignResponse,
)
from seedsigner.models.qr_type import QRType

# The wire-type strings are owned by the device's QRType; alias them so host and
# device can never drift.
UR_ACCOUNT_REQ = QRType.CARDANO_ACCOUNT_REQUEST
UR_ACCOUNT_RES = QRType.CARDANO_ACCOUNT
UR_TX_SIG_REQ = QRType.CARDANO_TX_SIG_REQUEST
UR_TX_SIG_RES = QRType.CARDANO_TX_SIG_RESPONSE
UR_CIP8_SIG_REQ = QRType.CARDANO_CIP8_SIG_REQUEST
UR_CIP8_SIG_RES = QRType.CARDANO_CIP8_SIG_RESPONSE

RESPONSE_FOR_REQUEST = {
    UR_ACCOUNT_REQ: UR_ACCOUNT_RES,
    UR_TX_SIG_REQ: UR_TX_SIG_RES,
    UR_CIP8_SIG_REQ: UR_CIP8_SIG_RES,
}


def make_encoder(ur_type: str, cbor: bytes, max_fragment_len: int = 90) -> UREncoder:
    """A UR fountain encoder for an outgoing message (animated QR source)."""
    return UREncoder(ur=UR(ur_type, bytearray(cbor)), max_fragment_len=max_fragment_len)


def parse_response(ur_type: str, cbor: bytes):
    """Parse a response CBOR payload by its UR type into a dataclass."""
    if ur_type == UR_ACCOUNT_RES:
        return CardanoAccountResponse.from_cbor(cbor)
    if ur_type == UR_TX_SIG_RES:
        return CardanoTxSignResponse.from_cbor(cbor)
    if ur_type == UR_CIP8_SIG_RES:
        return CardanoCip8SignResponse.from_cbor(cbor)
    raise ValueError(f"unknown response UR type: {ur_type}")


def parse_request(ur_type: str, cbor: bytes):
    """Parse a request CBOR payload (used by the device / simulator)."""
    if ur_type == UR_ACCOUNT_REQ:
        return CardanoAccountRequest.from_cbor(cbor)
    if ur_type == UR_TX_SIG_REQ:
        return CardanoSignRequest.from_cbor(cbor)
    if ur_type == UR_CIP8_SIG_REQ:
        return CardanoMessageSignRequest.from_cbor(cbor)
    raise ValueError(f"unknown request UR type: {ur_type}")


def decode_ur_parts(parts) -> tuple:
    """Reassemble UR string parts into ``(ur_type, cbor)``."""
    decoder = URDecoder()
    for part in parts:
        decoder.receive_part(part)
        if decoder.is_complete():
            break
    if not decoder.is_complete():
        raise ValueError("UR stream did not complete")
    message = decoder.result_message()
    return message.type, message.cbor
