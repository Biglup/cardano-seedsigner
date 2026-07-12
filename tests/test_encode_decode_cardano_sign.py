"""
Round-trip transport tests for the M5 sign messages over animated UR QR.

Each message is fountain-encoded with its QrEncoder, all frames are fed back
through DecodeQR, and the reconstructed object is asserted equal. Runs at
LOW / MEDIUM / HIGH density to exercise multi-frame fountain fragmentation, and
checks that detection routes each UR type to the right getter.
"""

import pytest

from cometa import NetworkId

from seedsigner.models.decode_qr import DecodeQR, DecodeQRStatus
from seedsigner.models.encode_qr import (
    CardanoTxSigRequestQrEncoder,
    CardanoCip8SigRequestQrEncoder,
    CardanoTxSigResponseQrEncoder,
    CardanoCip8SigResponseQrEncoder,
)
from seedsigner.models.qr_type import QRType
from seedsigner.models.settings import SettingsConstants
from seedsigner.models.cardano_tx import (
    CardanoSignRequest,
    CardanoTxSignResponse,
    CardanoMessageSignRequest,
    CardanoCip8SignResponse,
    SigningInput,
    ChangeOutput,
    ExtraSigner,
    SigningPath,
)


H = 0x80000000
PATH = [1852 + H, 1815 + H, 0 + H, 0, 0]
XFP = bytes.fromhex("b2743478")
DENSITIES = [
    SettingsConstants.DENSITY__LOW,
    SettingsConstants.DENSITY__MEDIUM,
    SettingsConstants.DENSITY__HIGH,
]


def _feed_all_frames(encoder):
    decoder = DecodeQR()
    seen = set()
    while True:
        part = encoder.next_part()
        status = decoder.add_data(part)
        if status == DecodeQRStatus.COMPLETE:
            break
        seen.add(part)
        if len(seen) > encoder.seq_len() * 4 + 10:
            pytest.fail("decoder did not complete after many frames")
    return decoder


def _tx_request():
    return CardanoSignRequest(
        request_id="tx-roundtrip-1",
        origin="Eternl",
        sign_data=bytes.fromhex("a30081825820" + "00" * 32 + "00") * 4,
        inputs=[
            SigningInput(tx_hash=b"\x01" * 32, index=0, xfp=XFP, path=PATH),
            SigningInput(tx_hash=b"\x02" * 32, index=1, xfp=XFP, path=PATH),
        ],
        change_outputs=[ChangeOutput(index=1, path=PATH, xfp=XFP)],
        network=NetworkId.MAINNET,
        extra_signers=[ExtraSigner(xfp=bytes.fromhex("deadbeef"), path=PATH)],
    )


def _cip8_request():
    return CardanoMessageSignRequest(
        request_id="cip8-roundtrip-1",
        origin="Lace",
        message_payload=b"I attest ownership of this Cardano address." * 3,
        required_signing_path=SigningPath(index=0, path=PATH),
        address_bytes=bytes.fromhex("61" + "11" * 28),
        xfp=XFP,
    )


@pytest.mark.parametrize("density", DENSITIES)
def test_tx_sign_request_roundtrip(density):
    request = _tx_request()
    decoder = _feed_all_frames(CardanoTxSigRequestQrEncoder(request=request, qr_density=density))
    assert decoder.is_complete
    assert decoder.qr_type == QRType.CARDANO_TX_SIG_REQUEST
    assert decoder.is_cardano_tx_sign_request
    assert decoder.get_cardano_tx_sign_request() == request


@pytest.mark.parametrize("density", DENSITIES)
def test_cip8_sign_request_roundtrip(density):
    request = _cip8_request()
    decoder = _feed_all_frames(CardanoCip8SigRequestQrEncoder(request=request, qr_density=density))
    assert decoder.is_complete
    assert decoder.qr_type == QRType.CARDANO_CIP8_SIG_REQUEST
    assert decoder.is_cardano_cip8_sign_request
    assert decoder.get_cardano_cip8_sign_request() == request


@pytest.mark.parametrize("density", DENSITIES)
def test_tx_witness_response_roundtrip(density):
    response = CardanoTxSignResponse(
        request_id="tx-roundtrip-1",
        vkey_witness_set=bytes.fromhex("d90102" + "81" + "82" + "5820" + "aa" * 32 + "5840" + "bb" * 64),
    )
    decoder = _feed_all_frames(CardanoTxSigResponseQrEncoder(response=response, qr_density=density))
    assert decoder.qr_type == QRType.CARDANO_TX_SIG_RESPONSE
    assert decoder.is_cardano_tx_sign_response
    assert decoder.get_cardano_tx_sign_response() == response


@pytest.mark.parametrize("density", DENSITIES)
def test_cip8_sig_response_roundtrip(density):
    response = CardanoCip8SignResponse(
        request_id="cip8-roundtrip-1",
        cose_sign1=b"\x84\x43\xa1\x01\x27" + b"\x00" * 60,
        cose_key=b"\xa4\x01\x01\x03\x27" + b"\x11" * 40,
    )
    decoder = _feed_all_frames(CardanoCip8SigResponseQrEncoder(response=response, qr_density=density))
    assert decoder.qr_type == QRType.CARDANO_CIP8_SIG_RESPONSE
    assert decoder.is_cardano_cip8_sign_response
    assert decoder.get_cardano_cip8_sign_response() == response


def test_malformed_request_surfaces_value_error():
    """A UR that reassembles but carries non-conforming CBOR must raise
    ValueError from the getter (not a raw cometa error) so the scan flow can
    fail gracefully."""
    from seedsigner.helpers.ur2.ur_encoder import UREncoder
    from seedsigner.helpers.ur2.ur import UR
    from cometa import CborWriter

    w = CborWriter()
    w.write_start_map(1)
    w.write_int(2)
    w.write_str("only-origin-no-required-fields")
    ur = UR("cardano-tx-sig-req", bytearray(w.encode()))
    encoder = UREncoder(ur=ur, max_fragment_len=20)

    decoder = DecodeQR()
    status = None
    while status != DecodeQRStatus.COMPLETE:
        status = decoder.add_data(encoder.next_part().upper())

    assert decoder.is_cardano_tx_sign_request
    with pytest.raises(ValueError):
        decoder.get_cardano_tx_sign_request()


def test_stray_frames_mid_scan_are_ignored():
    """Frames of a different QR type arriving mid animated scan (a stray
    settings QR, invalid UTF-8 bytes, seed-entropy-sized garbage) must return a
    non-fatal status instead of raising, and must leave the in-progress
    fountain decode intact."""
    request = _tx_request()
    encoder = CardanoTxSigRequestQrEncoder(
        request=request, qr_density=SettingsConstants.DENSITY__LOW)
    decoder = DecodeQR()

    assert decoder.add_data(encoder.next_part()) == DecodeQRStatus.PART_COMPLETE
    assert decoder.qr_type == QRType.CARDANO_TX_SIG_REQUEST
    assert not decoder.is_complete

    stray_frames = [
        b"settings::v1 name=Stray",
        b"\xff\xfe\x80\x9c\x00 not utf-8",
        b"\xff" * 32,
    ]
    for stray in stray_frames:
        assert decoder.add_data(stray) == DecodeQRStatus.FALSE

    assert decoder.qr_type == QRType.CARDANO_TX_SIG_REQUEST
    assert not decoder.is_complete

    status = None
    for _ in range(encoder.seq_len() * 4 + 10):
        status = decoder.add_data(encoder.next_part())
        if status == DecodeQRStatus.COMPLETE:
            break
    assert status == DecodeQRStatus.COMPLETE

    assert decoder.is_complete
    assert decoder.get_cardano_tx_sign_request() == request


def test_getter_on_incomplete_ur_raises_value_error():
    """A getter called before the UR fully reassembles (or after a failed
    reassembly, where result_message() is an error rather than a UR) must raise
    ValueError, not AttributeError."""
    request = _tx_request()
    encoder = CardanoTxSigRequestQrEncoder(
        request=request, qr_density=SettingsConstants.DENSITY__LOW)
    decoder = DecodeQR()
    decoder.add_data(encoder.next_part())
    assert not decoder.is_complete
    with pytest.raises(ValueError):
        decoder.get_cardano_tx_sign_request()
