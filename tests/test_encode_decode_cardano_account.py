"""
Round-trip transport tests for Cardano account export over animated UR QR.

Encodes a CardanoAccountResponse with CardanoAccountQrEncoder, collects all
emitted frames, feeds them back through DecodeQR, and asserts the reconstructed
response matches. Also decodes a CardanoAccountRequest produced by the model.
Runs at LOW / MEDIUM / HIGH density to exercise fountain fragmentation.
"""

import pytest

from seedsigner.models.decode_qr import DecodeQR, DecodeQRStatus
from seedsigner.models.encode_qr import CardanoAccountQrEncoder
from seedsigner.models.qr_type import QRType
from seedsigner.models.settings import SettingsConstants
from seedsigner.models.cardano_account import (
    AccountKey,
    CardanoAccountRequest,
    CardanoAccountResponse,
    account_path,
)


def _make_response(num_accounts):
    keys = [
        AccountKey(account_index=i, xpub=bytes([i % 251 + 1]) * 64, path=account_path(i))
        for i in range(num_accounts)
    ]
    return CardanoAccountResponse(
        request_id="round-trip-1",
        master_fingerprint=bytes.fromhex("a1b2c3d4"),
        keys=keys,
    )


def _feed_all_frames(encoder):
    decoder = DecodeQR()
    seen = set()
    status = None
    while True:
        part = encoder.next_part()
        status = decoder.add_data(part)
        if status == DecodeQRStatus.COMPLETE:
            break
        seen.add(part)
        if len(seen) > encoder.seq_len() * 4 + 10:
            pytest.fail("decoder did not complete after many frames")
    return decoder


@pytest.mark.parametrize("density", [
    SettingsConstants.DENSITY__LOW,
    SettingsConstants.DENSITY__MEDIUM,
    SettingsConstants.DENSITY__HIGH,
])
def test_response_roundtrip_over_animated_qr(density):
    response = _make_response(num_accounts=5)
    encoder = CardanoAccountQrEncoder(response=response, qr_density=density)

    decoder = _feed_all_frames(encoder)

    assert decoder.is_complete
    assert decoder.qr_type == QRType.CARDANO_ACCOUNT
    assert decoder.is_cardano_account
    decoded = decoder.get_cardano_account_response()
    assert decoded == response


def test_single_account_response_roundtrip():
    response = _make_response(num_accounts=1)
    encoder = CardanoAccountQrEncoder(response=response, qr_density=SettingsConstants.DENSITY__MEDIUM)
    decoder = _feed_all_frames(encoder)
    assert decoder.get_cardano_account_response() == response


def test_request_detection_and_decode():
    request = CardanoAccountRequest(
        request_id="req-xyz",
        account_indices=[0, 3],
        origin="Eternl",
    )
    from seedsigner.helpers.ur2.ur_encoder import UREncoder
    from seedsigner.helpers.ur2.ur import UR
    ur = UR("cardano-account-req", bytearray(request.to_cbor()))
    encoder = UREncoder(ur=ur, max_fragment_len=20)

    decoder = DecodeQR()
    status = None
    while status != DecodeQRStatus.COMPLETE:
        status = decoder.add_data(encoder.next_part().upper())

    assert decoder.qr_type == QRType.CARDANO_ACCOUNT_REQUEST
    assert decoder.is_cardano_account_request
    decoded = decoder.get_cardano_account_request()
    assert decoded == request
