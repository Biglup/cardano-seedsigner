"""
Tests for the Milestone 5 sign-request/response models and CBOR codecs.

Covers CBOR round-trips for the four custom UR messages:
  - cardano-tx-sig-req   (CardanoSignRequest)
  - cardano-tx-sig-res   (CardanoTxSignResponse)
  - cardano-cip8-sig-req (CardanoMessageSignRequest)
  - cardano-cip8-sig-res (CardanoCip8SignResponse)
including per-signer xfp, change-output xfp, multi-signer, and missing-field errors.
"""

import pytest

from cometa import CborWriter, NetworkId

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


PATH_PAYMENT = [2147485500, 2147485463, 2147483648, 0, 0]
PATH_CHANGE = [2147485500, 2147485463, 2147483648, 1, 0]
XFP = bytes.fromhex("b2743478")


def test_tx_request_roundtrip_minimal():
    req = CardanoSignRequest(
        request_id="req-1",
        origin=None,
        sign_data=b"\xa0",
        inputs=[SigningInput(tx_hash=b"\x0f" * 32, index=0, xfp=XFP, path=PATH_PAYMENT)],
        change_outputs=[],
        network=NetworkId.TESTNET,
    )
    decoded = CardanoSignRequest.from_cbor(req.to_cbor())
    assert decoded == req


def test_tx_request_roundtrip_full_multi_signer():
    req = CardanoSignRequest(
        request_id="abc-123",
        origin="Eternl",
        sign_data=bytes.fromhex("a30081825820" + "00" * 32 + "00"),
        inputs=[
            SigningInput(tx_hash=b"\x01" * 32, index=0, xfp=XFP, path=PATH_PAYMENT),
            SigningInput(tx_hash=b"\x02" * 32, index=3, xfp=bytes.fromhex("deadbeef"), path=PATH_CHANGE),
        ],
        change_outputs=[ChangeOutput(index=1, path=PATH_CHANGE, xfp=XFP)],
        network=NetworkId.MAINNET,
        extra_signers=[ExtraSigner(xfp=bytes.fromhex("cafebabe"), path=PATH_PAYMENT)],
    )
    decoded = CardanoSignRequest.from_cbor(req.to_cbor())
    assert decoded == req
    assert decoded.network == NetworkId.MAINNET
    assert decoded.change_outputs[0].xfp == XFP


def test_change_output_default_xfp_roundtrips():
    co = ChangeOutput(index=2, path=PATH_CHANGE)
    assert co.xfp == b""
    req = CardanoSignRequest(
        request_id="r", origin=None, sign_data=b"\xa0",
        inputs=[], change_outputs=[co], network=NetworkId.TESTNET,
    )
    decoded = CardanoSignRequest.from_cbor(req.to_cbor())
    assert decoded.change_outputs[0].xfp == b""


def test_tx_request_missing_sign_data_raises():
    w = CborWriter()
    w.write_start_map(1)
    w.write_int(1)
    w.write_str("only-id")
    with pytest.raises(ValueError):
        CardanoSignRequest.from_cbor(w.encode())


def test_tx_response_roundtrip():
    resp = CardanoTxSignResponse(request_id="req-1", vkey_witness_set=b"\xa1\x00\x80")
    decoded = CardanoTxSignResponse.from_cbor(resp.to_cbor())
    assert decoded == resp


def test_tx_response_missing_witness_raises():
    w = CborWriter()
    w.write_start_map(1)
    w.write_int(1)
    w.write_str("req-1")
    with pytest.raises(ValueError):
        CardanoTxSignResponse.from_cbor(w.encode())


def test_tx_response_missing_request_id_raises():
    w = CborWriter()
    w.write_start_map(1)
    w.write_int(2)
    w.write_bytes(b"\xa1\x00\x80")
    with pytest.raises(ValueError):
        CardanoTxSignResponse.from_cbor(w.encode())


def test_cip8_request_roundtrip_minimal():
    req = CardanoMessageSignRequest(
        request_id="m-1",
        origin=None,
        message_payload=b"hello",
        required_signing_path=SigningPath(index=0, path=PATH_PAYMENT),
        xfp=XFP,
    )
    decoded = CardanoMessageSignRequest.from_cbor(req.to_cbor())
    assert decoded == req


def test_cip8_request_roundtrip_full():
    req = CardanoMessageSignRequest(
        request_id="m-2",
        origin="Lace",
        message_payload=b"I attest ownership of this address.",
        required_signing_path=SigningPath(index=2, path=PATH_CHANGE),
        address_bytes=bytes.fromhex("01" + "35" * 28 + "1f" * 28),
        xfp=XFP,
    )
    decoded = CardanoMessageSignRequest.from_cbor(req.to_cbor())
    assert decoded == req
    assert decoded.address_bytes == req.address_bytes


def test_cip8_request_missing_payload_raises():
    w = CborWriter()
    w.write_start_map(1)
    w.write_int(1)
    w.write_str("m-1")
    with pytest.raises(ValueError):
        CardanoMessageSignRequest.from_cbor(w.encode())


def test_cip8_response_roundtrip():
    resp = CardanoCip8SignResponse(
        request_id="m-1",
        cose_sign1=b"\x84\x43\xa1\x01\x27",
        cose_key=b"\xa4\x01\x01",
    )
    decoded = CardanoCip8SignResponse.from_cbor(resp.to_cbor())
    assert decoded == resp


def test_cip8_response_missing_key_raises():
    w = CborWriter()
    w.write_start_map(2)
    w.write_int(1)
    w.write_str("m-1")
    w.write_int(2)
    w.write_bytes(b"\x84")
    with pytest.raises(ValueError):
        CardanoCip8SignResponse.from_cbor(w.encode())


def test_cip8_response_missing_sign1_raises():
    w = CborWriter()
    w.write_start_map(2)
    w.write_int(1)
    w.write_str("m-1")
    w.write_int(3)
    w.write_bytes(b"\xa4")
    with pytest.raises(ValueError):
        CardanoCip8SignResponse.from_cbor(w.encode())


def test_cip8_response_missing_request_id_raises():
    w = CborWriter()
    w.write_start_map(2)
    w.write_int(2)
    w.write_bytes(b"\x84")
    w.write_int(3)
    w.write_bytes(b"\xa4")
    with pytest.raises(ValueError):
        CardanoCip8SignResponse.from_cbor(w.encode())


def test_tx_request_multi_change_and_signers_roundtrip():
    req = CardanoSignRequest(
        request_id="r",
        origin=None,
        sign_data=b"\xa0",
        inputs=[],
        change_outputs=[
            ChangeOutput(index=1, path=PATH_CHANGE, xfp=XFP),
            ChangeOutput(index=2, path=PATH_PAYMENT),
        ],
        network=NetworkId.TESTNET,
        extra_signers=[
            ExtraSigner(xfp=XFP, path=PATH_PAYMENT),
            ExtraSigner(xfp=bytes.fromhex("deadbeef"), path=PATH_CHANGE),
        ],
    )
    assert CardanoSignRequest.from_cbor(req.to_cbor()) == req


def test_tx_request_collateral_return_path_roundtrips():
    req = CardanoSignRequest(
        request_id="r-cr",
        origin="Lace",
        sign_data=b"\xa0",
        inputs=[SigningInput(tx_hash=b"\x0f" * 32, index=0, xfp=XFP, path=PATH_PAYMENT)],
        change_outputs=[],
        network=NetworkId.TESTNET,
        collateral_return_path=ExtraSigner(xfp=XFP, path=PATH_CHANGE),
    )
    decoded = CardanoSignRequest.from_cbor(req.to_cbor())
    assert decoded == req
    assert decoded.collateral_return_path.path == PATH_CHANGE
    assert decoded.collateral_return_path.xfp == XFP


def test_tx_request_collateral_return_path_defaults_to_none():
    req = CardanoSignRequest(
        request_id="r",
        origin=None,
        sign_data=b"\xa0",
        inputs=[],
        change_outputs=[],
        network=NetworkId.TESTNET,
    )
    decoded = CardanoSignRequest.from_cbor(req.to_cbor())
    assert decoded.collateral_return_path is None


def test_tx_request_malformed_collateral_return_path_raises():
    w = CborWriter()
    w.write_start_map(4)
    w.write_int(1)
    w.write_str("r-bad-crp")
    w.write_int(3)
    w.write_bytes(b"\xa0")
    w.write_int(7)
    w.write_int(0)
    w.write_int(8)
    w.write_start_map(2)
    w.write_int(1)
    w.write_bytes(b"\x01\x02\x03")
    w.write_int(2)
    w.write_start_array(1)
    w.write_int(0)
    with pytest.raises(ValueError):
        CardanoSignRequest.from_cbor(w.encode())


def test_tx_request_unknown_key_is_skipped():
    """An unknown top-level key (99) with a nested container value must be
    skipped without corrupting subsequent reads."""
    w = CborWriter()
    w.write_start_map(5)
    w.write_int(99)
    w.write_start_array(2)
    w.write_int(1)
    w.write_int(2)
    w.write_int(1)
    w.write_str("req-skip")
    w.write_int(3)
    w.write_bytes(b"\xa0")
    w.write_int(4)
    w.write_start_array(0)
    w.write_int(7)
    w.write_int(0)
    decoded = CardanoSignRequest.from_cbor(w.encode())
    assert decoded.request_id == "req-skip"
    assert decoded.network == NetworkId.TESTNET


def test_signing_input_bad_xfp_length_raises():
    """A 2-byte xfp where 4 bytes are required must raise ValueError."""
    from cometa import CborReader
    from seedsigner.models.cardano_tx import SigningInput
    w = CborWriter()
    w.write_start_map(4)
    w.write_int(1)
    w.write_bytes(b"\x00" * 32)
    w.write_int(2)
    w.write_int(0)
    w.write_int(3)
    w.write_bytes(b"\x00\x01")
    w.write_int(4)
    w.write_start_array(1)
    w.write_int(0)
    with pytest.raises(ValueError):
        SigningInput.from_cbor(CborReader.from_bytes(w.encode()))


def test_bad_tx_hash_length_raises():
    """An 8-byte tx hash where 32 bytes are required must raise ValueError."""
    from cometa import CborReader
    from seedsigner.models.cardano_tx import SigningInput
    w = CborWriter()
    w.write_start_map(4)
    w.write_int(1)
    w.write_bytes(b"\x00" * 8)
    w.write_int(2)
    w.write_int(0)
    w.write_int(3)
    w.write_bytes(XFP)
    w.write_int(4)
    w.write_start_array(1)
    w.write_int(0)
    with pytest.raises(ValueError):
        SigningInput.from_cbor(CborReader.from_bytes(w.encode()))


def test_oversized_path_raises():
    """A 50-component derivation path exceeds MAX_PATH_COMPONENTS and must
    raise ValueError."""
    from cometa import CborReader
    from seedsigner.models.cardano_tx import ExtraSigner
    w = CborWriter()
    w.write_start_map(2)
    w.write_int(1)
    w.write_bytes(XFP)
    w.write_int(2)
    w.write_start_array(50)
    for _ in range(50):
        w.write_int(0)
    with pytest.raises(ValueError):
        ExtraSigner.from_cbor(CborReader.from_bytes(w.encode()))


def test_malformed_cbor_raises_valueerror_not_cometa_error():
    """A wrong type for request_id (int where tstr is expected) must surface
    as ValueError so the scan handler can fail gracefully."""
    w = CborWriter()
    w.write_start_map(2)
    w.write_int(1)
    w.write_int(12345)
    w.write_int(3)
    w.write_bytes(b"\xa0")
    with pytest.raises(ValueError):
        CardanoSignRequest.from_cbor(w.encode())


def test_script_locked_input_roundtrips_without_path():
    req = CardanoSignRequest(
        request_id="script-1",
        origin=None,
        sign_data=b"\x01\x02",
        inputs=[SigningInput(tx_hash=b"\x00" * 32, index=0)],
        change_outputs=[],
        network=NetworkId.TESTNET,
        extra_signers=[ExtraSigner(xfp=XFP, path=PATH_PAYMENT)],
    )
    decoded = CardanoSignRequest.from_cbor(req.to_cbor())
    assert decoded.inputs[0].tx_hash == b"\x00" * 32
    assert decoded.inputs[0].index == 0
    assert decoded.inputs[0].xfp == b""
    assert decoded.inputs[0].path is None
    assert decoded.extra_signers[0].path == PATH_PAYMENT


def test_mixed_script_locked_and_owned_inputs_roundtrip():
    req = CardanoSignRequest(
        request_id="mixed-1",
        origin=None,
        sign_data=b"\x01",
        inputs=[
            SigningInput(tx_hash=b"\x00" * 32, index=0),
            SigningInput(tx_hash=b"\x11" * 32, index=1, xfp=XFP, path=PATH_PAYMENT),
        ],
        change_outputs=[],
        network=NetworkId.MAINNET,
    )
    decoded = CardanoSignRequest.from_cbor(req.to_cbor())
    assert decoded.inputs[0].path is None
    assert decoded.inputs[1].path == PATH_PAYMENT
    assert decoded.inputs[1].xfp == XFP


def test_signing_input_path_without_xfp_raises():
    from cometa import CborReader
    w = CborWriter()
    w.write_start_map(3)
    w.write_int(1)
    w.write_bytes(b"\x00" * 32)
    w.write_int(2)
    w.write_int(0)
    w.write_int(4)
    w.write_start_array(1)
    w.write_int(0)
    with pytest.raises(ValueError):
        SigningInput.from_cbor(CborReader.from_bytes(w.encode()))


BODY_CBOR_ONE_OUTPUT = bytes.fromhex(
    "a3"
    "00" "81" "82" "5820" + "00" * 32 + "00"
    "01" "81" "82" "581d61" + "11" * 28 + "1a000f4240"
    "02" "1a0002bf20"
)

BODY_CBOR_EMPTY_VOTING = bytes.fromhex(
    "a4"
    "00" "81" "82" "5820" + "00" * 32 + "00"
    "01" "81" "82" "581d61" + "11" * 28 + "1a000f4240"
    "02" "1a0002bf20"
    "13" "a0"
)

BODY_CBOR_ONE_VOTE = bytes.fromhex(
    "a4"
    "00" "81" "82" "5820" + "00" * 32 + "00"
    "01" "81" "82" "581d61" + "11" * 28 + "1a000f4240"
    "02" "1a0002bf20"
    "13" "a1" "8200581c" + "22" * 28 + "a1" "825820" + "33" * 32 + "00" "8201f6"
)

BODY_CBOR_WITH_UPDATE = bytes.fromhex(
    "a4"
    "00" "80"
    "01" "80"
    "02" "1a00029810"
    "06" "82" "a1" "581c" + "aa" * 28 + "a1" "00" "1a000f423f" "05"
)


def _parsed_tx(verified_change_indices, sign_data=BODY_CBOR_ONE_OUTPUT):
    from seedsigner.models.cardano_tx import CardanoParsedTx
    req = CardanoSignRequest(
        request_id="w-1", origin=None, sign_data=sign_data,
        inputs=[], change_outputs=[], network=NetworkId.MAINNET,
    )
    return CardanoParsedTx(req, verified_change_indices=verified_change_indices)


def test_unverified_outputs_flag_fires_when_no_change_verified():
    parsed = _parsed_tx([])
    assert parsed.has_unverified_outputs
    assert parsed.output_amounts == [1_000_000]


def test_unverified_outputs_flag_clear_when_change_verified():
    parsed = _parsed_tx([0])
    assert not parsed.has_unverified_outputs


def test_has_voting_false_for_empty_voting_procedures():
    parsed = _parsed_tx([], sign_data=BODY_CBOR_EMPTY_VOTING)
    assert parsed.voting_procedures is not None
    assert not parsed.has_voting


def test_has_voting_true_for_nonempty_voting_procedures():
    parsed = _parsed_tx([], sign_data=BODY_CBOR_ONE_VOTE)
    assert parsed.has_voting


def test_body_with_protocol_param_update_field_is_rejected():
    """A body carrying the pre-Conway protocol parameter update (key 6) has
    no review page, so parsing it must raise ValueError instead of letting
    the user approve content that was never displayed."""
    with pytest.raises(ValueError, match="protocol parameter update"):
        _parsed_tx([], sign_data=BODY_CBOR_WITH_UPDATE)


def test_signing_input_encode_path_without_xfp_raises():
    si = SigningInput(tx_hash=b"\x00" * 32, index=0, path=PATH_PAYMENT)
    with pytest.raises(ValueError):
        si.to_cbor(CborWriter())


def test_request_with_no_signers_at_all_raises():
    req = CardanoSignRequest(
        request_id="no-signers", origin=None, sign_data=b"\x01",
        inputs=[SigningInput(tx_hash=b"\x00" * 32, index=0)],
        change_outputs=[], network=NetworkId.TESTNET,
    )
    with pytest.raises(ValueError):
        CardanoSignRequest.from_cbor(req.to_cbor())


def test_failed_change_claim_flag():
    from seedsigner.models.cardano_tx import CardanoParsedTx

    def parsed(change_outputs, verified):
        req = CardanoSignRequest(
            request_id="c-1", origin=None, sign_data=BODY_CBOR_ONE_OUTPUT,
            inputs=[], change_outputs=change_outputs, network=NetworkId.MAINNET,
        )
        return CardanoParsedTx(req, verified_change_indices=verified)

    claim = ChangeOutput(index=0, path=PATH_CHANGE)
    assert parsed([claim], []).has_failed_change_claims
    assert not parsed([claim], [0]).has_failed_change_claims
    assert not parsed([], []).has_failed_change_claims
