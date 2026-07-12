"""
Flow tests for scan-initiated Cardano transaction and CIP-8 message signing.

Drives MainMenu -> Scan (inject a cardano-tx-sig-req / cardano-cip8-sig-req) ->
seed selection -> review overview, and the 0-seed resume sub-flow.
"""

from base import BaseTest, FlowTest, FlowStep

from cometa import NetworkId

from seedsigner.models.settings import Settings, SettingsConstants
from seedsigner.models.seed import Seed
from seedsigner.views.view import MainMenuView
from seedsigner.views import seed_views, scan_views
from seedsigner.views.tx_review.overview_view import CardanoTxOverviewView
from seedsigner.views.tx_review.sign_view import CardanoTxSignView, CardanoTxSignedQRView
from seedsigner.views.msg_sign.overview_view import CardanoMsgOverviewView
from seedsigner.views.msg_sign.sign_view import CardanoMsgSignView, CardanoMsgSignedQRView
from seedsigner.views.view import MainMenuView as _MainMenuView


ABANDON_MNEMONIC = (
    "abandon abandon abandon abandon abandon abandon abandon abandon "
    "abandon abandon abandon about"
).split()

H = 0x80000000
PATH = [1852 + H, 1815 + H, 0 + H, 0, 0]
XFP = bytes.fromhex("b2743478")

BODY_CBOR = bytes.fromhex(
    "a3"
    "00" "81" "82" "5820" + "00" * 32 + "00"
    "01" "81" "82" "581d61" + "11" * 28 + "1a000f4240"
    "02" "1a0002bf20"
)

BODY_CBOR_WITH_CERT = bytes.fromhex(
    "a4"
    "00" "81" "82" "5820" + "00" * 32 + "00"
    "01" "81" "82" "581d61" + "11" * 28 + "1a000f4240"
    "02" "1a0002bf20"
    "04" "81" "82" "00" "82" "00" "581c" + "aa" * 28
)

BODY_CBOR_WITH_PROPOSAL = bytes.fromhex(
    "a4"
    "00" "81" "82" "5820" + "00" * 32 + "00"
    "01" "81" "82" "581d61" + "11" * 28 + "1a000f4240"
    "02" "1a0002bf20"
    "14" "81" "84"
    "1a000f4240"
    "581d" "e1" + "aa" * 28
    + "81" "06"
    "82" "69" + b"https://a".hex() + "5820" + "bb" * 32
)


def _feed(view, ur_type, cbor):
    from seedsigner.helpers.ur2.ur_encoder import UREncoder
    from seedsigner.helpers.ur2.ur import UR
    from seedsigner.models.decode_qr import DecodeQRStatus

    encoder = UREncoder(ur=UR(ur_type, bytearray(cbor)), max_fragment_len=200)
    status = None
    while status != DecodeQRStatus.COMPLETE:
        status = view.decoder.add_data(encoder.next_part().upper())


def inject_tx_request():
    from seedsigner.models.cardano_tx import CardanoSignRequest, SigningInput

    request = CardanoSignRequest(
        request_id="tx-1", origin="Eternl", sign_data=BODY_CBOR,
        inputs=[SigningInput(tx_hash=b"\x00" * 32, index=0, xfp=XFP, path=PATH)],
        change_outputs=[], network=NetworkId.MAINNET,
    )
    return lambda view: _feed(view, "cardano-tx-sig-req", request.to_cbor())


def inject_cip8_request():
    from seedsigner.models.cardano_tx import CardanoMessageSignRequest, SigningPath

    request = CardanoMessageSignRequest(
        request_id="m-1", origin="Lace",
        message_payload=b"I attest ownership of this address.",
        required_signing_path=SigningPath(index=0, path=PATH),
        address_bytes=None, xfp=XFP,
    )
    return lambda view: _feed(view, "cardano-cip8-sig-req", request.to_cbor())


class TestCardanoSignFlows(FlowTest):

    def _load_seed(self):
        self.controller.storage.set_pending_seed(Seed(mnemonic=ABANDON_MNEMONIC))
        self.controller.storage.finalize_pending_seed()

    def test_tx_sign_scan_routes_to_review(self):
        self._load_seed()
        self.run_sequence([
            FlowStep(MainMenuView, button_data_selection=MainMenuView.SCAN),
            FlowStep(scan_views.ScanView, before_run=inject_tx_request()),
            FlowStep(seed_views.CardanoTxSelectSeedView, is_redirect=True),
            FlowStep(CardanoTxOverviewView),
        ])

    def test_cip8_sign_scan_routes_to_review(self):
        self._load_seed()
        self.run_sequence([
            FlowStep(MainMenuView, button_data_selection=MainMenuView.SCAN),
            FlowStep(scan_views.ScanView, before_run=inject_cip8_request()),
            FlowStep(seed_views.CardanoMsgSelectSeedView, is_redirect=True),
            FlowStep(CardanoMsgOverviewView),
        ])

    def test_tx_sign_zero_seed_resumes_after_load(self):
        # No seed loaded: select-seed offers Scan/Type, sets resume flow; after a
        # seed is finalized, SeedFinalizeView resumes the tx-sign select-seed view.
        self.run_sequence([
            FlowStep(MainMenuView, button_data_selection=MainMenuView.SCAN),
            FlowStep(scan_views.ScanView, before_run=inject_tx_request()),
            FlowStep(seed_views.CardanoTxSelectSeedView,
                     button_data_selection=seed_views.CardanoTxSelectSeedView.TYPE_12WORD),
            FlowStep(seed_views.SeedMnemonicEntryView, is_redirect=True),
        ])
        assert self.controller.resume_main_flow == self.controller.FLOW__CARDANO_TX_SIGN

    def test_tx_sign_malformed_body_routes_to_error(self):
        """A request with a valid envelope but garbage tx-body CBOR must land on
        a friendly ErrorView, not crash to the unhandled-exception screen."""
        from seedsigner.models.cardano_tx import CardanoSignRequest, SigningInput
        from seedsigner.views.view import ErrorView

        self._load_seed()
        request = CardanoSignRequest(
            request_id="bad", origin=None, sign_data=b"\xff\xff\xff",
            inputs=[SigningInput(tx_hash=b"\x00" * 32, index=0, xfp=XFP, path=PATH)],
            change_outputs=[], network=NetworkId.MAINNET,
        )
        inject = lambda view: _feed(view, "cardano-tx-sig-req", request.to_cbor())
        self.run_sequence([
            FlowStep(MainMenuView, button_data_selection=MainMenuView.SCAN),
            FlowStep(scan_views.ScanView, before_run=inject),
            FlowStep(seed_views.CardanoTxSelectSeedView, is_redirect=True),
            FlowStep(ErrorView),
        ])

    def test_tx_sign_multi_seed_picker_selects_correct_seed(self):
        SECOND_MNEMONIC = ("legal winner thank year wave sausage worth useful "
                           "legal winner thank yellow").split()
        self._load_seed()
        self.controller.storage.set_pending_seed(Seed(mnemonic=SECOND_MNEMONIC))
        self.controller.storage.finalize_pending_seed()
        seeds = self.controller.storage.seeds
        assert len(seeds) == 2

        self.run_sequence([
            FlowStep(MainMenuView, button_data_selection=MainMenuView.SCAN),
            FlowStep(scan_views.ScanView, before_run=inject_tx_request()),
            FlowStep(seed_views.CardanoTxSelectSeedView, screen_return_value=1),
            FlowStep(CardanoTxOverviewView),
        ])
        assert self.controller.cardano_seed is seeds[1]

    def _parsed_tx_for(self, request):
        from seedsigner.models.cardano_tx import CardanoParsedTx
        return CardanoParsedTx(request, verified_change_indices=[])

    def _tx_request_with_xfp(self, xfp):
        from seedsigner.models.cardano_tx import CardanoSignRequest, SigningInput
        return CardanoSignRequest(
            request_id="sign-1", origin="Eternl", sign_data=BODY_CBOR,
            inputs=[SigningInput(tx_hash=b"\x00" * 32, index=0, xfp=xfp, path=PATH)],
            change_outputs=[], network=NetworkId.MAINNET,
        )

    def test_tx_sign_matching_seed_emits_witness_qr(self):
        self._load_seed()
        seed = self.controller.storage.seeds[0]
        request = self._tx_request_with_xfp(bytes.fromhex(seed.get_fingerprint()))
        self.controller.cardano_seed = seed
        self.controller.cardano_tx_sign_request = request

        self.run_sequence(
            [
                FlowStep(CardanoTxSignView, screen_return_value=1),
                FlowStep(CardanoTxSignedQRView),
            ],
            initial_destination_view_args=dict(parsed_tx=self._parsed_tx_for(request)),
        )

    def test_tx_sign_wrong_seed_warns_and_aborts(self):
        self._load_seed()
        seed = self.controller.storage.seeds[0]
        request = self._tx_request_with_xfp(bytes.fromhex("deadbeef"))
        self.controller.cardano_seed = seed
        self.controller.cardano_tx_sign_request = request

        self.run_sequence(
            [
                FlowStep(CardanoTxSignView, screen_return_value=0),
                FlowStep(_MainMenuView),
            ],
            initial_destination_view_args=dict(parsed_tx=self._parsed_tx_for(request)),
        )

    def test_tx_sign_partial_match_proceeds(self):
        from seedsigner.models.cardano_tx import CardanoSignRequest, SigningInput

        self._load_seed()
        seed = self.controller.storage.seeds[0]
        request = CardanoSignRequest(
            request_id="partial", origin=None, sign_data=BODY_CBOR,
            inputs=[
                SigningInput(tx_hash=b"\x00" * 32, index=0,
                             xfp=bytes.fromhex(seed.get_fingerprint()), path=PATH),
                SigningInput(tx_hash=b"\x11" * 32, index=1,
                             xfp=bytes.fromhex("deadbeef"), path=PATH),
            ],
            change_outputs=[], network=NetworkId.MAINNET,
        )
        self.controller.cardano_seed = seed
        self.controller.cardano_tx_sign_request = request

        self.run_sequence(
            [
                FlowStep(CardanoTxSignView, screen_return_value=1),
                FlowStep(CardanoTxSignedQRView),
            ],
            initial_destination_view_args=dict(parsed_tx=self._parsed_tx_for(request)),
        )

    def test_sign_path_witness_roundtrips_and_verifies(self):
        from cometa import (CborReader, TransactionBody, VkeyWitnessSet,
                            Ed25519PublicKey, Ed25519Signature)
        from seedsigner.helpers.cardano_signing import build_tx_sign_response
        from seedsigner.models.encode_qr import CardanoTxSigResponseQrEncoder
        from seedsigner.models.decode_qr import DecodeQR, DecodeQRStatus

        seed = Seed(mnemonic=ABANDON_MNEMONIC)
        request = self._tx_request_with_xfp(bytes.fromhex(seed.get_fingerprint()))
        response = build_tx_sign_response(seed, request)

        encoder = CardanoTxSigResponseQrEncoder(
            response=response, qr_density=SettingsConstants.DENSITY__LOW)
        decoder = DecodeQR()
        while decoder.add_data(encoder.next_part()) != DecodeQRStatus.COMPLETE:
            pass
        decoded = decoder.get_cardano_tx_sign_response()
        assert decoded.request_id == "sign-1"

        ws = VkeyWitnessSet.from_cbor(CborReader.from_bytes(decoded.vkey_witness_set))
        assert len(ws) == 1
        tx_hash = TransactionBody.from_cbor(CborReader.from_bytes(BODY_CBOR)).hash.to_bytes()
        pub = Ed25519PublicKey.from_bytes(ws[0].vkey)
        sig = Ed25519Signature.from_bytes(ws[0].signature)
        assert pub.verify(sig, tx_hash)

    def _enterprise_addr_bytes(self, seed):
        from cometa import Credential, EnterpriseAddress, NetworkId as _N
        from seedsigner.helpers.cardano_utils import root_key_from_seed
        key = root_key_from_seed(seed).derive(PATH)
        cred = Credential.from_key_hash(key.get_public_key().to_ed25519_key().to_hash())
        return EnterpriseAddress.from_credentials(_N.MAINNET, cred).to_address().to_bytes()

    def _cip8_request_for(self, seed, xfp):
        from seedsigner.models.cardano_tx import CardanoMessageSignRequest, SigningPath
        return CardanoMessageSignRequest(
            request_id="cip8-sign", origin="Lace",
            message_payload=b"I attest ownership of this address.",
            required_signing_path=SigningPath(index=0, path=PATH),
            address_bytes=self._enterprise_addr_bytes(seed), xfp=xfp,
        )

    def test_cip8_sign_matching_seed_emits_cose_qr(self):
        self._load_seed()
        seed = self.controller.storage.seeds[0]
        request = self._cip8_request_for(seed, bytes.fromhex(seed.get_fingerprint()))
        self.controller.cardano_seed = seed
        self.controller.cardano_cip8_sign_request = request

        self.run_sequence(
            [
                FlowStep(CardanoMsgSignView, screen_return_value=1),
                FlowStep(CardanoMsgSignedQRView),
            ],
            initial_destination_view_args=dict(msg_request=request),
        )

    def test_cip8_sign_wrong_seed_warns_and_aborts(self):
        self._load_seed()
        seed = self.controller.storage.seeds[0]
        request = self._cip8_request_for(seed, bytes.fromhex("deadbeef"))
        self.controller.cardano_seed = seed
        self.controller.cardano_cip8_sign_request = request

        self.run_sequence(
            [
                FlowStep(CardanoMsgSignView, screen_return_value=0),
                FlowStep(_MainMenuView),
            ],
            initial_destination_view_args=dict(msg_request=request),
        )

    def test_cip8_sign_address_binding_failure_rejected(self):
        from seedsigner.models.cardano_tx import CardanoMessageSignRequest, SigningPath

        self._load_seed()
        seed = self.controller.storage.seeds[0]
        stake_path = [1852 + H, 1815 + H, 0 + H, 2, 0]
        request = CardanoMessageSignRequest(
            request_id="bind-fail", origin=None, message_payload=b"hi",
            required_signing_path=SigningPath(index=0, path=stake_path),
            address_bytes=self._enterprise_addr_bytes(seed),
            xfp=bytes.fromhex(seed.get_fingerprint()),
        )
        self.controller.cardano_seed = seed
        self.controller.cardano_cip8_sign_request = request

        self.run_sequence(
            [
                FlowStep(CardanoMsgSignView, screen_return_value=1),
                FlowStep(_MainMenuView),
            ],
            initial_destination_view_args=dict(msg_request=request),
        )

    def test_cip8_sign_cose_roundtrips(self):
        from seedsigner.helpers.cardano_signing import build_cip8_sign_response
        from seedsigner.models.encode_qr import CardanoCip8SigResponseQrEncoder
        from seedsigner.models.decode_qr import DecodeQR, DecodeQRStatus

        seed = Seed(mnemonic=ABANDON_MNEMONIC)
        request = self._cip8_request_for(seed, bytes.fromhex(seed.get_fingerprint()))
        response = build_cip8_sign_response(seed, request)

        encoder = CardanoCip8SigResponseQrEncoder(
            response=response, qr_density=SettingsConstants.DENSITY__LOW)
        decoder = DecodeQR()
        while decoder.add_data(encoder.next_part()) != DecodeQRStatus.COMPLETE:
            pass
        decoded = decoder.get_cardano_cip8_sign_response()
        assert decoded.request_id == "cip8-sign"
        assert decoded.cose_sign1 == response.cose_sign1
        assert decoded.cose_key == response.cose_key
        assert len(decoded.cose_sign1) > 0 and len(decoded.cose_key) > 0

    PATH_MULTISIG = [1854 + H, 1815 + H, 0 + H, 0, 0]

    def test_signing_keys_step_gates_the_sign_confirmation(self):
        from seedsigner.gui.screens.tx_review import RET_CODE__RIGHT_BUTTON
        from seedsigner.models.cardano_tx import CardanoSignRequest, SigningInput, ExtraSigner
        from seedsigner.views.tx_review.sequential_review_view import CardanoTxSequentialReviewView
        from seedsigner.views.tx_review.signing_keys_view import CardanoTxSigningKeysView

        self._load_seed()
        seed = self.controller.storage.seeds[0]
        xfp = bytes.fromhex(seed.get_fingerprint())
        stake_path = [1852 + H, 1815 + H, 0 + H, 2, 0]
        request = CardanoSignRequest(
            request_id="gate-1", origin=None, sign_data=BODY_CBOR,
            inputs=[SigningInput(tx_hash=b"\x00" * 32, index=0, xfp=xfp, path=PATH)],
            change_outputs=[], network=NetworkId.MAINNET,
            extra_signers=[ExtraSigner(xfp=xfp, path=stake_path)],
        )
        self.controller.cardano_seed = seed
        self.controller.cardano_tx_sign_request = request
        parsed_tx = self._parsed_tx_for(request)
        last_page = len(parsed_tx.build_review_pages()) - 1

        self.run_sequence(
            [
                FlowStep(CardanoTxSequentialReviewView, screen_return_value=RET_CODE__RIGHT_BUTTON),
                FlowStep(CardanoTxSigningKeysView, screen_return_value=RET_CODE__RIGHT_BUTTON),
                FlowStep(CardanoTxSigningKeysView, screen_return_value=RET_CODE__RIGHT_BUTTON),
                FlowStep(CardanoTxSignView, screen_return_value=1),
                FlowStep(CardanoTxSignedQRView),
            ],
            initial_destination_view_args=dict(parsed_tx=parsed_tx, global_index=last_page),
        )

    def test_signing_keys_step_no_match_falls_through_to_wrong_seed(self):
        from seedsigner.views.tx_review.signing_keys_view import CardanoTxSigningKeysView

        self._load_seed()
        seed = self.controller.storage.seeds[0]
        request = self._tx_request_with_xfp(bytes.fromhex("deadbeef"))
        self.controller.cardano_seed = seed
        self.controller.cardano_tx_sign_request = request

        self.run_sequence(
            [
                FlowStep(CardanoTxSigningKeysView, is_redirect=True),
                FlowStep(CardanoTxSignView, screen_return_value=0),
                FlowStep(_MainMenuView),
            ],
            initial_destination_view_args=dict(parsed_tx=self._parsed_tx_for(request)),
        )

    def test_msg_signing_key_step_gates_the_sign_confirmation(self):
        from seedsigner.gui.screens.tx_review import RET_CODE__RIGHT_BUTTON
        from seedsigner.views.msg_sign.payload_view import CardanoMsgPayloadView
        from seedsigner.views.msg_sign.signing_key_view import CardanoMsgSigningKeyView

        self._load_seed()
        seed = self.controller.storage.seeds[0]
        request = self._cip8_request_for(seed, bytes.fromhex(seed.get_fingerprint()))
        self.controller.cardano_seed = seed
        self.controller.cardano_cip8_sign_request = request

        self.run_sequence(
            [
                FlowStep(CardanoMsgPayloadView, screen_return_value=RET_CODE__RIGHT_BUTTON),
                FlowStep(CardanoMsgSigningKeyView, screen_return_value=RET_CODE__RIGHT_BUTTON),
                FlowStep(CardanoMsgSignView, screen_return_value=1),
                FlowStep(CardanoMsgSignedQRView),
            ],
            initial_destination_view_args=dict(msg_request=request),
        )

    def test_cip8_multisig_key_signs_via_key_inspection(self):
        from cometa import CborReader
        from seedsigner.gui.screens.tx_review import RET_CODE__RIGHT_BUTTON
        from seedsigner.helpers.cardano_utils import root_key_from_seed
        from seedsigner.models.cardano_tx import CardanoMessageSignRequest, SigningPath
        from seedsigner.views.msg_sign.signing_key_view import CardanoMsgSigningKeyView

        self._load_seed()
        seed = self.controller.storage.seeds[0]
        key = root_key_from_seed(seed).derive(self.PATH_MULTISIG)
        key_hash = key.get_public_key().to_ed25519_key().to_hash().to_bytes()
        request = CardanoMessageSignRequest(
            request_id="cip8-ms-flow", origin=None, message_payload=b"ms",
            required_signing_path=SigningPath(index=0, path=self.PATH_MULTISIG),
            address_bytes=key_hash, xfp=bytes.fromhex(seed.get_fingerprint()),
        )
        self.controller.cardano_seed = seed
        self.controller.cardano_cip8_sign_request = request

        self.run_sequence(
            [
                FlowStep(CardanoMsgSigningKeyView, screen_return_value=RET_CODE__RIGHT_BUTTON),
                FlowStep(CardanoMsgSignView, screen_return_value=1),
                FlowStep(CardanoMsgSignedQRView),
            ],
            initial_destination_view_args=dict(msg_request=request),
        )

    def _tx_request_with_body(self, seed, sign_data):
        from seedsigner.models.cardano_tx import CardanoSignRequest, SigningInput
        return CardanoSignRequest(
            request_id="review-1", origin=None, sign_data=sign_data,
            inputs=[SigningInput(tx_hash=b"\x00" * 32, index=0,
                                 xfp=bytes.fromhex(seed.get_fingerprint()), path=PATH)],
            change_outputs=[], network=NetworkId.MAINNET,
        )

    def _run_undisplayable_section_aborts(self, sign_data, section, view_cls):
        from unittest.mock import patch
        from seedsigner.views.tx_review.sequential_review_view import CardanoTxSequentialReviewView

        self._load_seed()
        seed = self.controller.storage.seeds[0]
        request = self._tx_request_with_body(seed, sign_data)
        self.controller.cardano_seed = seed
        self.controller.cardano_tx_sign_request = request
        parsed_tx = self._parsed_tx_for(request)
        pages = parsed_tx.build_review_pages()
        page_index = next(i for i, page in enumerate(pages) if page.section == section)

        with patch.object(view_cls, "_build_content",
                          side_effect=Exception("undecodable")):
            self.run_sequence(
                [
                    FlowStep(CardanoTxSequentialReviewView),
                    FlowStep(_MainMenuView),
                ],
                initial_destination_view_args=dict(parsed_tx=parsed_tx,
                                                   global_index=page_index),
            )
        assert self.controller.cardano_tx_sign_request is None
        assert self.controller.cardano_seed is None
        assert self.controller.resume_main_flow is None

    def test_tx_review_undecodable_certificate_aborts(self):
        from seedsigner.views.tx_review.certificate_view import CertificateReviewView

        self._run_undisplayable_section_aborts(
            BODY_CBOR_WITH_CERT, "certificate", CertificateReviewView)

    def test_tx_review_undecodable_proposal_aborts(self):
        from seedsigner.views.tx_review.proposal_view import ProposalReviewView

        self._run_undisplayable_section_aborts(
            BODY_CBOR_WITH_PROPOSAL, "proposal", ProposalReviewView)

    def test_tx_review_decodable_certificate_still_reaches_sign(self):
        from seedsigner.gui.screens.tx_review import RET_CODE__RIGHT_BUTTON
        from seedsigner.views.tx_review.sequential_review_view import CardanoTxSequentialReviewView
        from seedsigner.views.tx_review.signing_keys_view import CardanoTxSigningKeysView

        self._load_seed()
        seed = self.controller.storage.seeds[0]
        request = self._tx_request_with_body(seed, BODY_CBOR_WITH_CERT)
        self.controller.cardano_seed = seed
        self.controller.cardano_tx_sign_request = request
        parsed_tx = self._parsed_tx_for(request)
        last_page = len(parsed_tx.build_review_pages()) - 1

        self.run_sequence(
            [
                FlowStep(CardanoTxSequentialReviewView, screen_return_value=RET_CODE__RIGHT_BUTTON),
                FlowStep(CardanoTxSigningKeysView, screen_return_value=RET_CODE__RIGHT_BUTTON),
                FlowStep(CardanoTxSignView, screen_return_value=1),
                FlowStep(CardanoTxSignedQRView),
            ],
            initial_destination_view_args=dict(parsed_tx=parsed_tx, global_index=last_page),
        )

    def test_msg_overview_without_seed_exits_to_main_menu(self):
        seed = Seed(mnemonic=ABANDON_MNEMONIC)
        request = self._cip8_request_for(seed, bytes.fromhex(seed.get_fingerprint()))
        assert self.controller.cardano_seed is None
        assert len(self.controller.storage.seeds) == 0

        self.run_sequence(
            [
                FlowStep(CardanoMsgOverviewView, is_redirect=True),
                FlowStep(_MainMenuView),
            ],
            initial_destination_view_args=dict(msg_request=request),
        )

    def test_msg_select_seed_without_request_routes_to_error(self):
        from seedsigner.views.view import ErrorView

        self._load_seed()

        def clear_request(view):
            self.controller.cardano_cip8_sign_request = None

        self.run_sequence([
            FlowStep(MainMenuView, button_data_selection=MainMenuView.SCAN),
            FlowStep(scan_views.ScanView, before_run=inject_cip8_request()),
            FlowStep(seed_views.CardanoMsgSelectSeedView, before_run=clear_request,
                     is_redirect=True),
            FlowStep(ErrorView),
        ])
        assert self.controller.cardano_seed is None

    def test_msg_payload_deeply_nested_json_renders_as_text(self):
        from seedsigner.gui.screens.tx_review import RET_CODE__RIGHT_BUTTON
        from seedsigner.models.cardano_tx import CardanoMessageSignRequest, SigningPath
        from seedsigner.views.msg_sign.payload_view import CardanoMsgPayloadView
        from seedsigner.views.msg_sign.signing_key_view import CardanoMsgSigningKeyView

        self._load_seed()
        seed = self.controller.storage.seeds[0]
        request = CardanoMessageSignRequest(
            request_id="deep-json", origin=None,
            message_payload=b"[" * 3000,
            required_signing_path=SigningPath(index=0, path=PATH),
            address_bytes=None, xfp=bytes.fromhex(seed.get_fingerprint()),
        )
        self.controller.cardano_seed = seed
        self.controller.cardano_cip8_sign_request = request

        self.run_sequence(
            [
                FlowStep(CardanoMsgPayloadView, screen_return_value=RET_CODE__RIGHT_BUTTON),
                FlowStep(CardanoMsgSigningKeyView),
            ],
            initial_destination_view_args=dict(msg_request=request),
        )

    PATH_DREP = [1852 + H, 1815 + H, 0 + H, 3, 0]

    def _key_hash_bytes(self, seed, path):
        from seedsigner.helpers.cardano_utils import root_key_from_seed
        key = root_key_from_seed(seed).derive(path)
        return key.get_public_key().to_ed25519_key().to_hash().to_bytes()

    def _run_overview_rejects(self, request):
        from unittest.mock import patch

        with patch.object(CardanoMsgOverviewView, "_show_rejection") as mock_rejection:
            self.run_sequence(
                [
                    FlowStep(CardanoMsgOverviewView, is_redirect=True),
                    FlowStep(_MainMenuView),
                ],
                initial_destination_view_args=dict(msg_request=request),
            )
        assert mock_rejection.call_args.kwargs["title"] == "Address Mismatch"

    def test_msg_overview_address_mismatch_rejected(self):
        from seedsigner.models.cardano_tx import CardanoMessageSignRequest, SigningPath

        self._load_seed()
        seed = self.controller.storage.seeds[0]
        other_path = [1852 + H, 1815 + H, 0 + H, 0, 1]
        request = CardanoMessageSignRequest(
            request_id="addr-mismatch", origin="Lace", message_payload=b"hi",
            required_signing_path=SigningPath(index=0, path=other_path),
            address_bytes=self._enterprise_addr_bytes(seed),
            xfp=bytes.fromhex(seed.get_fingerprint()),
        )
        self.controller.cardano_seed = seed
        self.controller.cardano_cip8_sign_request = request

        self._run_overview_rejects(request)

    def test_msg_overview_owned_drep_key_hash_proceeds(self):
        from seedsigner.models.cardano_tx import CardanoMessageSignRequest, SigningPath
        from seedsigner.views.msg_sign.address_view import CardanoMsgAddressView

        self._load_seed()
        seed = self.controller.storage.seeds[0]
        request = CardanoMessageSignRequest(
            request_id="drep-owned", origin="Lace", message_payload=b"vote",
            required_signing_path=SigningPath(index=0, path=self.PATH_DREP),
            address_bytes=self._key_hash_bytes(seed, self.PATH_DREP),
            xfp=bytes.fromhex(seed.get_fingerprint()),
        )
        self.controller.cardano_seed = seed
        self.controller.cardano_cip8_sign_request = request

        self.run_sequence(
            [
                FlowStep(CardanoMsgOverviewView, screen_return_value=0),
                FlowStep(CardanoMsgAddressView),
            ],
            initial_destination_view_args=dict(msg_request=request),
        )

    def test_msg_overview_mismatched_drep_key_hash_rejected(self):
        from seedsigner.models.cardano_tx import CardanoMessageSignRequest, SigningPath

        self._load_seed()
        seed = self.controller.storage.seeds[0]
        other_drep_path = [1852 + H, 1815 + H, 0 + H, 3, 1]
        request = CardanoMessageSignRequest(
            request_id="drep-mismatch", origin="Lace", message_payload=b"vote",
            required_signing_path=SigningPath(index=0, path=self.PATH_DREP),
            address_bytes=self._key_hash_bytes(seed, other_drep_path),
            xfp=bytes.fromhex(seed.get_fingerprint()),
        )
        self.controller.cardano_seed = seed
        self.controller.cardano_cip8_sign_request = request

        self._run_overview_rejects(request)

    def test_extra_signers_only_multisig_tx_signs(self):
        from seedsigner.gui.screens.tx_review import RET_CODE__RIGHT_BUTTON
        from seedsigner.models.cardano_tx import CardanoSignRequest, SigningInput, ExtraSigner
        from seedsigner.views.tx_review.signing_keys_view import CardanoTxSigningKeysView

        self._load_seed()
        seed = self.controller.storage.seeds[0]
        request = CardanoSignRequest(
            request_id="ms-flow", origin=None, sign_data=BODY_CBOR,
            inputs=[SigningInput(tx_hash=b"\x00" * 32, index=0)],
            change_outputs=[], network=NetworkId.MAINNET,
            extra_signers=[ExtraSigner(xfp=bytes.fromhex(seed.get_fingerprint()),
                                       path=self.PATH_MULTISIG)],
        )
        self.controller.cardano_seed = seed
        self.controller.cardano_tx_sign_request = request

        self.run_sequence(
            [
                FlowStep(CardanoTxSigningKeysView, screen_return_value=RET_CODE__RIGHT_BUTTON),
                FlowStep(CardanoTxSignView, screen_return_value=1),
                FlowStep(CardanoTxSignedQRView),
            ],
            initial_destination_view_args=dict(parsed_tx=self._parsed_tx_for(request)),
        )
