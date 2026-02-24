from typing import Callable
from unittest.mock import patch

# Must import test base before the Controller
from base import BaseTest, FlowTest, FlowStep

from seedsigner.gui.screens.screen import RET_CODE__BACK_BUTTON, ButtonOption
from seedsigner.models.settings import Settings, SettingsConstants
from seedsigner.models.seed import Seed
from seedsigner.views.view import MainMenuView, View, NetworkMismatchErrorView
from seedsigner.views import seed_views, scan_views


def load_seed_into_decoder(view: scan_views.ScanView):
    view.decoder.add_data("0000" * 11 + "0003")



class TestSeedFlows(FlowTest):

    def test_scan_seedqr_flow(self):
        """
            Selecting "Scan" from the MainMenuView and scanning a SeedQR should enter the
            Finalize Seed flow and end at the SeedOptionsView.
        """
        self.run_sequence([
            FlowStep(MainMenuView, button_data_selection=MainMenuView.SCAN),
            FlowStep(scan_views.ScanView, before_run=load_seed_into_decoder),  # simulate read SeedQR; ret val is ignored
            FlowStep(seed_views.SeedFinalizeView, button_data_selection=seed_views.SeedFinalizeView.FINALIZE),
            FlowStep(seed_views.SeedOptionsView),
        ])


    def test_passphrase_entry_flow(self):
        """
        Opting to add a BIP-39 passphrase on the Finalize Seed screen should enter the
        passphrase entry / review flow and end at the SeedOptionsView. 
        """
        self.run_sequence([
            FlowStep(MainMenuView, button_data_selection=MainMenuView.SCAN),
            FlowStep(scan_views.ScanView, before_run=load_seed_into_decoder),  # simulate read SeedQR; ret val is ignored
            FlowStep(seed_views.SeedFinalizeView, button_data_selection=seed_views.SeedFinalizeView.PASSPHRASE),
            FlowStep(seed_views.SeedAddPassphraseView, screen_return_value=dict(passphrase="muhpassphrase", is_back_button=True)),
            FlowStep(seed_views.SeedAddPassphraseExitDialogView, button_data_selection=seed_views.SeedAddPassphraseExitDialogView.DISCARD),
            FlowStep(seed_views.SeedFinalizeView, button_data_selection=seed_views.SeedFinalizeView.PASSPHRASE),
            FlowStep(seed_views.SeedAddPassphraseView, screen_return_value=dict(passphrase="muhpassphrase", is_back_button=True)),
            FlowStep(seed_views.SeedAddPassphraseExitDialogView, button_data_selection=seed_views.SeedAddPassphraseExitDialogView.EDIT),
            FlowStep(seed_views.SeedAddPassphraseView, screen_return_value=dict(passphrase="muhpassphrase")),
            FlowStep(seed_views.SeedReviewPassphraseView, button_data_selection=seed_views.SeedReviewPassphraseView.EDIT),
            FlowStep(seed_views.SeedAddPassphraseView, screen_return_value=dict(passphrase="muhpassphrase")),
            FlowStep(seed_views.SeedReviewPassphraseView, button_data_selection=seed_views.SeedReviewPassphraseView.DONE),
            FlowStep(seed_views.SeedOptionsView),
        ])


    def test_mnemonic_entry_flow(self):
        """
            Manually entering a mnemonic should land at the Finalize Seed flow and end at
            the SeedOptionsView.
        """
        def test_with_mnemonic(mnemonic):
            Settings.HOSTNAME = "not seedsigner-os"
            sequence = [
                FlowStep(MainMenuView, button_data_selection=MainMenuView.SEEDS),
                FlowStep(seed_views.SeedsMenuView, is_redirect=True),  # When no seeds are loaded it auto-redirects to LoadSeedView
                FlowStep(seed_views.LoadSeedView, button_data_selection=seed_views.LoadSeedView.TYPE_12WORD if len(mnemonic) == 12 else seed_views.LoadSeedView.TYPE_24WORD),
            ]

            # Now add each manual word entry step
            for word in mnemonic:
                sequence.append(
                    FlowStep(seed_views.SeedMnemonicEntryView, screen_return_value=word)
                )
            
            # With the mnemonic completely entered, we land on the SeedFinalizeView
            sequence += [
                FlowStep(seed_views.SeedFinalizeView, button_data_selection=seed_views.SeedFinalizeView.FINALIZE),
                FlowStep(seed_views.SeedOptionsView),
            ]

            self.run_sequence(sequence)

        # Test data from iancoleman.io; 12- and 24-word mnemonic
        test_with_mnemonic("tone flat shed cool census soul paddle boy flight fantasy stem social".split())

        BaseTest.reset_controller()

        test_with_mnemonic("cotton artefact spy mind wing there echo steak child oak awful host despair online bicycle divorce middle firm diamond rare execute chimney almost hollow".split())


    def test_invalid_mnemonic(self):
        """ Should be able to go back and edit or discard an invalid mnemonic """
        # Test data from iancoleman.io
        mnemonic = "blush twice taste dawn feed second opinion lazy thumb play neglect impact".split()
        sequence = [
            FlowStep(MainMenuView, button_data_selection=MainMenuView.SEEDS),
            FlowStep(seed_views.SeedsMenuView, is_redirect=True),  # When no seeds are loaded it auto-redirects to LoadSeedView
            FlowStep(seed_views.LoadSeedView, button_data_selection=seed_views.LoadSeedView.TYPE_12WORD if len(mnemonic) == 12 else seed_views.LoadSeedView.TYPE_24WORD),
        ]
        for word in mnemonic[:-1]:
            sequence.append(FlowStep(seed_views.SeedMnemonicEntryView, screen_return_value=word))

        sequence += [
            FlowStep(seed_views.SeedMnemonicEntryView, screen_return_value="zoo"),  # But finish with an INVALID checksum word
            FlowStep(seed_views.SeedMnemonicInvalidView, button_data_selection=seed_views.SeedMnemonicInvalidView.EDIT),
        ]

        # Restarts from first word
        for word in mnemonic[:-1]:
            sequence.append(FlowStep(seed_views.SeedMnemonicEntryView, screen_return_value=word))

        sequence += [
            FlowStep(seed_views.SeedMnemonicEntryView, screen_return_value="zebra"),  # provide yet another invalid checksum word
            FlowStep(seed_views.SeedMnemonicInvalidView, button_data_selection=seed_views.SeedMnemonicInvalidView.DISCARD),
            FlowStep(MainMenuView),
        ]

        self.run_sequence(sequence)


    def test_export_xpub_standard_flow(self):
        """
            Selecting "Export XPUB" from the SeedOptionsView should enter the Export XPUB flow and end at the MainMenuView.
            Sig types, script types, and coordinators are now hardcoded in the views (no longer settings-driven).
        """
        def flowtest_standard_xpub(sig_tuple, script_tuple, coord_tuple):
            if sig_tuple[0] == SettingsConstants.SINGLE_SIG:
                sig_selection = seed_views.SeedExportXpubSigTypeView.SINGLE_SIG
            else:
                sig_selection = seed_views.SeedExportXpubSigTypeView.MULTISIG
            self.run_sequence(
                initial_destination_view_args=dict(seed_num=0),
                sequence=[
                    FlowStep(seed_views.SeedOptionsView, button_data_selection=seed_views.SeedOptionsView.EXPORT_XPUB),
                    FlowStep(seed_views.SeedExportXpubSigTypeView, button_data_selection=sig_selection),
                    FlowStep(seed_views.SeedExportXpubScriptTypeView, button_data_selection=ButtonOption(script_tuple[1], return_data=script_tuple[0])),
                    FlowStep(seed_views.SeedExportXpubCoordinatorView, button_data_selection=ButtonOption(coord_tuple[1], return_data=coord_tuple[0])),
                    FlowStep(seed_views.SeedExportXpubWarningView, screen_return_value=0),
                    FlowStep(seed_views.SeedExportXpubDetailsView, screen_return_value=0),
                    FlowStep(seed_views.SeedExportXpubQRDisplayView, screen_return_value=0),
                    FlowStep(MainMenuView),
                ]
        )

        # Load a finalized Seed into the Controller
        mnemonic = "blush twice taste dawn feed second opinion lazy thumb play neglect impact".split()
        self.controller.storage.set_pending_seed(Seed(mnemonic=mnemonic))
        self.controller.storage.finalize_pending_seed()

        # Hardcoded sig types, script types, and coordinators matching the views
        sig_types = SettingsConstants.ALL_SIG_TYPES
        script_types = [
            (SettingsConstants.NATIVE_SEGWIT, "Native Segwit"),
            (SettingsConstants.NESTED_SEGWIT, "Nested Segwit"),
            (SettingsConstants.TAPROOT, "Taproot"),
        ]
        coordinators = [
            (SettingsConstants.COORDINATOR__BLUE_WALLET, "BlueWallet"),
            (SettingsConstants.COORDINATOR__NUNCHUK, "Nunchuk"),
            (SettingsConstants.COORDINATOR__SPARROW, "Sparrow"),
            (SettingsConstants.COORDINATOR__SPECTER_DESKTOP, "Specter Desktop"),
        ]

        # exhaustively test flows thru standard sig_types, script_types, and coordinators
        for sig_tuple in sig_types:
            for script_tuple in script_types:
                for coord_tuple in coordinators:
                    # skip multisig taproot
                    if sig_tuple[0] == SettingsConstants.MULTISIG and script_tuple[0] == SettingsConstants.TAPROOT:
                        continue
                    else:
                        print('\n\ntest_standard_xpubs(%s, %s, %s)' % (sig_tuple, script_tuple, coord_tuple))
                        flowtest_standard_xpub(sig_tuple, script_tuple, coord_tuple)


    def test_discard_seed_flow(self):
        """
            Selecting "Discard Seed" from the SeedOptionsView should enter the Discard Seed flow and 
            remove the in-memory seed from the Controller.
        """
        # Load a finalized Seed into the Controller
        mnemonic = "blush twice taste dawn feed second opinion lazy thumb play neglect impact".split()
        self.controller.storage.set_pending_seed(Seed(mnemonic=mnemonic))
        self.controller.storage.finalize_pending_seed()

        self.run_sequence(
            initial_destination_view_args=dict(seed_num=0),
            sequence=[
                FlowStep(seed_views.SeedOptionsView, button_data_selection=seed_views.SeedOptionsView.DISCARD),
                FlowStep(seed_views.SeedDiscardView, button_data_selection=seed_views.SeedDiscardView.DISCARD),
                FlowStep(MainMenuView, button_data_selection=MainMenuView.SEEDS),
                FlowStep(seed_views.SeedsMenuView, is_redirect=True),  # When no seeds are loaded it auto-redirects to LoadSeedView
                FlowStep(seed_views.LoadSeedView),
            ]
        )


    @patch("seedsigner.gui.screens.seed_screens.SeedTranscribeSeedQRZoomedInScreen", autospec=True)
    def test_transcribe_seedqr_and_verify(self, mock_zoomed_in_screen: Callable):
        """
        """
        # Load a finalized Seed into the Controller
        mnemonic = ["abandon"] * 11 + ["about"]
        self.controller.storage.set_pending_seed(Seed(mnemonic=mnemonic))
        self.controller.storage.finalize_pending_seed()

        def load_wrong_seed_into_decoder(view: View):
            view.decoder.add_data("0138" * 24)

        def load_completely_wrong_qr_type_into_decoder(view: View):
            view.decoder.add_data("I like cheese")

        def load_recognized_qr_type_isnot_seed_into_decoder(view: View):
            view.decoder.add_data("UR:CRYPTO-PSBT/HKADHEJOJKIDJYZMADAEGMAOAEAEAEADHHGLEYKGBDSBKEMTSARLVYSGIABEDELFSKWLLUDKLYESJOFDLPJPFXSOHHWZTYWEAEAEAEAEAEZCZMZMZMADBKBZJEDEHEAEAEAECMAEBBVEPFDWDMBBGSPFZTKIMYCLKPSOBDDTRDWTWPYKGAQDKNAEAEGWADAAECLTTKAXWSWTUTSNLAAEAEAEPKCTBSHGISSSRETIVEWSGYNEPTHTESNSWMLBTARYEMHTBTBTLNWSBKJLMKYNFGHLAXJYBBTTIDHKDICHAMLEHHDSRKATGDLYSBIYHNHDNEWPJKZSZMDKVETYNSGOCXKNDNBEOLFSRSNSGHAEAELAADAEAELAAEAEAELAAEADADCTKSBZJEDEHEAEAEAECMAEBBVEPFDWDMBBGSPFZTKIMYCLKPSOBDDTRDWTWPYKGAADAXAAADAEAEAECPAMAODSFTLDTYFRECSKVWYLKNBANNKKZCRTHYJTPSHLHNHKNBPDCLCFDMSOLPDKFXLFQZCSOLFSRSNSGHAEAELAADAEAELAAEAEAELAAEAEAEAEAEAEAEAEAECPAOAODSFTLDTYFRECSKVWYLKNBANNKKZCRTHYJTPSHLHNHKNBPDCLCFDMSOLPDKFXLFQZCSOLFSRSNSGHAEAELAADAEAELAAEAEAELAAEAEAEAEAEAEAEAEAELGMKFZCW")        

        def load_right_seed_into_decoder(view: View):
            view.decoder.add_data("0000" * 11 + "0003")

        self.run_sequence([
            FlowStep(MainMenuView, button_data_selection=MainMenuView.SEEDS),
            FlowStep(seed_views.SeedsMenuView, screen_return_value=0),
            FlowStep(seed_views.SeedOptionsView, button_data_selection=seed_views.SeedOptionsView.BACKUP),
            FlowStep(seed_views.SeedBackupView, button_data_selection=seed_views.SeedBackupView.EXPORT_SEEDQR),
            FlowStep(seed_views.SeedTranscribeSeedQRFormatView, button_data_selection=seed_views.SeedTranscribeSeedQRFormatView.STANDARD_12),
            FlowStep(seed_views.SeedTranscribeSeedQRWarningView),
            FlowStep(seed_views.SeedTranscribeSeedQRWholeQRView),
            FlowStep(seed_views.SeedTranscribeSeedQRZoomedInView),
            FlowStep(seed_views.SeedTranscribeSeedQRConfirmQRPromptView, button_data_selection=seed_views.SeedTranscribeSeedQRConfirmQRPromptView.SCAN),

            # Intentionally "scan" the wrong SeedQR
            FlowStep(seed_views.SeedTranscribeSeedQRConfirmScanView, before_run=load_wrong_seed_into_decoder),
            FlowStep(seed_views.SeedTranscribeSeedQRConfirmWrongSeedView),
            FlowStep(seed_views.SeedTranscribeSeedQRZoomedInView),

            # Intentionally scan QR data that makes no sense for this flow
            FlowStep(seed_views.SeedTranscribeSeedQRConfirmQRPromptView, button_data_selection=seed_views.SeedTranscribeSeedQRConfirmQRPromptView.SCAN),
            FlowStep(seed_views.SeedTranscribeSeedQRConfirmScanView, before_run=load_completely_wrong_qr_type_into_decoder),
            FlowStep(seed_views.SeedTranscribeSeedQRConfirmInvalidQRView),
            FlowStep(seed_views.SeedTranscribeSeedQRZoomedInView),

            # Intentionally scan QR data that makes no sense for this flow because is another QR recognized but is not a SeedQR (e.g., bitcoin address, psbt)
            FlowStep(seed_views.SeedTranscribeSeedQRConfirmQRPromptView, button_data_selection=seed_views.SeedTranscribeSeedQRConfirmQRPromptView.SCAN),
            FlowStep(seed_views.SeedTranscribeSeedQRConfirmScanView, before_run=load_recognized_qr_type_isnot_seed_into_decoder),
            FlowStep(seed_views.SeedTranscribeSeedQRConfirmInvalidQRView),
            FlowStep(seed_views.SeedTranscribeSeedQRZoomedInView),
            
            # Now scan the correct SeedQR
            FlowStep(seed_views.SeedTranscribeSeedQRConfirmQRPromptView, button_data_selection=seed_views.SeedTranscribeSeedQRConfirmQRPromptView.SCAN),
            FlowStep(seed_views.SeedTranscribeSeedQRConfirmScanView, before_run=load_right_seed_into_decoder),
            FlowStep(seed_views.SeedTranscribeSeedQRConfirmSuccessView),
            FlowStep(seed_views.SeedOptionsView),
        ])



class TestMessageSigningFlows(FlowTest):
    MAINNET_DERIVATION_PATH = "m/84h/0h/0h/0/0"
    TESTNET_DERIVATION_PATH = "m/84h/1h/0h/0/0"
    CUSTOM_DERIVATION_PATH = "m/99h/0/0"
    SHORT_MESSAGE = "I attest that I control this bitcoin address blah blah blah"
    NO_WHITESPACE_MESSAGE = """{"height":841407,"lightning_bolt12":"lno1xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"}"""
    MULTIPAGE_MESSAGE = """Chancellor on brink of second bailout for banks

        Billions may be needed as lending squeeze tightens

        Alistair Darling has been forced to consider a second bailout for banks as the lending drought worsens.

        The Chancellor will decide within weeks whether to pump billions more into the economy as evidence mounts that the £37 billion part-nationalisation last year has failed to keep credit flowing. Options include cash injections, offering banks cheaper state guarantees to raise money privately or buying up “toxic assets”, The Times has learnt."""


    def load_seed_into_decoder(self, view: scan_views.ScanView):
        view.decoder.add_data("0000" * 11 + "0003")


    def load_signmessage_into_decoder(self, view:View, derivation_path: str, message: str):
        view.decoder.add_data(f"signmessage {derivation_path} ascii:{message}")


    def load_short_message_into_decoder(self, view: View):
        self.load_signmessage_into_decoder(view, self.MAINNET_DERIVATION_PATH, self.SHORT_MESSAGE)


    def load_testnet_message_into_decoder(self, view: View):
        self.load_signmessage_into_decoder(view, self.TESTNET_DERIVATION_PATH, self.SHORT_MESSAGE)


    def load_multipage_message_into_decoder(self, view: View):
        self.load_signmessage_into_decoder(view, self.MAINNET_DERIVATION_PATH, self.MULTIPAGE_MESSAGE)


    def load_no_whitespace_message_into_decoder(self, view: View):
        self.load_signmessage_into_decoder(view, self.MAINNET_DERIVATION_PATH, self.NO_WHITESPACE_MESSAGE)


    def load_custom_derivation_into_decoder(self, view: View):
        self.load_signmessage_into_decoder(view, self.CUSTOM_DERIVATION_PATH, self.SHORT_MESSAGE)


    def inject_mesage_as_paged_message(self, view: View):
        # Because the Screen won't actually run, we have to do the Screen's work here
        from seedsigner.gui.components import reflow_text_into_pages, GUIConstants
        paged = reflow_text_into_pages(
            text=self.controller.sign_message_data["message"],
            width=240 - 2*GUIConstants.EDGE_PADDING,
            height=240 - GUIConstants.TOP_NAV_HEIGHT - 3*GUIConstants.EDGE_PADDING - GUIConstants.BUTTON_HEIGHT,
        )
        self.controller.sign_message_data["paged_message"] = paged


    def test_sign_message_flow(self):
        """
        Should scan a `signmessage` QR and complete the message review, address review,
        and signing flow. Message signing is now always enabled (no settings gate).
        """
        # Scenario 1: Load the message first, then the seed
        self.run_sequence([
            FlowStep(MainMenuView, button_data_selection=MainMenuView.SCAN),
            FlowStep(scan_views.ScanView, before_run=self.load_short_message_into_decoder),  # simulate read message QR; ret val is ignored
            FlowStep(seed_views.SeedSignMessageStartView, is_redirect=True),
            FlowStep(seed_views.SeedSelectSeedView, button_data_selection=seed_views.SeedSelectSeedView.SCAN_SEED),
            FlowStep(scan_views.ScanView, before_run=self.load_seed_into_decoder),  # simulate read SeedQR; ret val is ignored
            FlowStep(seed_views.SeedFinalizeView, button_data_selection=seed_views.SeedFinalizeView.FINALIZE),
            FlowStep(seed_views.SeedOptionsView, is_redirect=True),
            FlowStep(seed_views.SeedSignMessageConfirmMessageView, before_run=self.inject_mesage_as_paged_message, screen_return_value=0),
            FlowStep(seed_views.SeedSignMessageConfirmAddressView, screen_return_value=0),
            FlowStep(seed_views.SeedSignMessageSignedMessageQRView, screen_return_value=0),
            FlowStep(MainMenuView),
        ])

        # Scenario 2: Load a long, multipage message
        self.run_sequence([
            FlowStep(MainMenuView, button_data_selection=MainMenuView.SCAN),
            FlowStep(scan_views.ScanView, before_run=self.load_multipage_message_into_decoder),  # simulate read message QR; ret val is ignored
            FlowStep(seed_views.SeedSignMessageStartView, is_redirect=True),
            FlowStep(seed_views.SeedSelectSeedView, button_data_selection=seed_views.SeedSelectSeedView.SCAN_SEED),
            FlowStep(scan_views.ScanView, before_run=self.load_seed_into_decoder),  # simulate read SeedQR; ret val is ignored
            FlowStep(seed_views.SeedFinalizeView, button_data_selection=seed_views.SeedFinalizeView.FINALIZE),
            FlowStep(seed_views.SeedOptionsView, is_redirect=True),
            FlowStep(seed_views.SeedSignMessageConfirmMessageView, before_run=self.inject_mesage_as_paged_message, screen_return_value=0),  # page 1/5
            FlowStep(seed_views.SeedSignMessageConfirmMessageView, screen_return_value=0),  # page 2/5
            FlowStep(seed_views.SeedSignMessageConfirmMessageView, screen_return_value=0),  # page 3/5
            FlowStep(seed_views.SeedSignMessageConfirmMessageView, screen_return_value=0),  # page 4/5
            FlowStep(seed_views.SeedSignMessageConfirmMessageView, screen_return_value=0),  # page 5/5

            # Arrive at the address confirmation, then go backwards to re-review the paged message
            FlowStep(seed_views.SeedSignMessageConfirmAddressView, screen_return_value=RET_CODE__BACK_BUTTON),  # then back to page 5/5
            FlowStep(seed_views.SeedSignMessageConfirmMessageView, screen_return_value=RET_CODE__BACK_BUTTON),  # back to page 4/5
            FlowStep(seed_views.SeedSignMessageConfirmMessageView, screen_return_value=RET_CODE__BACK_BUTTON),  # back to page 3/5
            FlowStep(seed_views.SeedSignMessageConfirmMessageView, screen_return_value=RET_CODE__BACK_BUTTON),  # back to page 2/5
            FlowStep(seed_views.SeedSignMessageConfirmMessageView, screen_return_value=RET_CODE__BACK_BUTTON),  # back to page 1/5

            # Now proceed forward again to the end
            FlowStep(seed_views.SeedSignMessageConfirmMessageView, screen_return_value=0),  # page 1/5
            FlowStep(seed_views.SeedSignMessageConfirmMessageView, screen_return_value=0),  # page 2/5
            FlowStep(seed_views.SeedSignMessageConfirmMessageView, screen_return_value=0),  # page 3/5
            FlowStep(seed_views.SeedSignMessageConfirmMessageView, screen_return_value=0),  # page 4/5
            FlowStep(seed_views.SeedSignMessageConfirmMessageView, screen_return_value=0),  # page 5/5
            FlowStep(seed_views.SeedSignMessageConfirmAddressView, screen_return_value=0),
            FlowStep(seed_views.SeedSignMessageSignedMessageQRView, screen_return_value=0),
            FlowStep(MainMenuView),
        ])


    def test_sign_message_network_mismatch_flow(self):
        """
        Should redirect to NetworkMismatchErrorView if a message's derivation path
        is not mainnet (the device now always assumes mainnet).

        The error view should then forward to MainMenuView.
        """
        # TESTNET derivation path should trigger a mismatch since the device expects mainnet
        self.run_sequence([
            FlowStep(MainMenuView, button_data_selection=MainMenuView.SCAN),
            FlowStep(scan_views.ScanView, before_run=self.load_testnet_message_into_decoder),  # simulate read message QR; ret val is ignored
            FlowStep(seed_views.SeedSignMessageStartView, is_redirect=True),
            FlowStep(NetworkMismatchErrorView),
            FlowStep(MainMenuView),
        ])


    def test_sign_message_unsupported_derivation_flow(self):
        """
        Should redirect to NotYetImplementedView if a message's derivation path isn't yet supported.
        Uses scan-first flow (scan message QR directly).
        """
        self.run_sequence([
            FlowStep(MainMenuView, button_data_selection=MainMenuView.SCAN),
            FlowStep(scan_views.ScanView, before_run=self.load_custom_derivation_into_decoder),  # simulate read message QR; ret val is ignored
            FlowStep(seed_views.SeedSignMessageStartView, is_redirect=True),
            FlowStep(seed_views.NotYetImplementedView),
            FlowStep(MainMenuView),
        ])


