from typing import Callable
from unittest.mock import patch

# Must import test base before the Controller
from base import BaseTest, FlowTest, FlowStep

from seedsigner.controller import Controller
from seedsigner.gui.screens.screen import RET_CODE__BACK_BUTTON, ButtonOption
from seedsigner.models.settings import Settings, SettingsConstants
from seedsigner.models.seed import Seed
from seedsigner.views.view import MainMenuView, View
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
        def test_with_mnemonic(mnemonic, word_type):
            Settings.HOSTNAME = "not seedsigner-os"
            sequence = [
                FlowStep(MainMenuView, button_data_selection=MainMenuView.SEEDS),
                FlowStep(seed_views.SeedsMenuView, is_redirect=True),  # When no seeds are loaded it auto-redirects to LoadSeedView
                FlowStep(seed_views.LoadSeedView, button_data_selection=word_type),
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

        # Test 12-word mnemonic
        test_with_mnemonic(
            "tone flat shed cool census soul paddle boy flight fantasy stem social".split(),
            seed_views.LoadSeedView.TYPE_12WORD,
        )

        BaseTest.reset_controller()

        # Test 24-word mnemonic
        test_with_mnemonic(
            "cotton artefact spy mind wing there echo steak child oak awful host despair online bicycle divorce middle firm diamond rare execute chimney almost hollow".split(),
            seed_views.LoadSeedView.TYPE_24WORD,
        )

        BaseTest.reset_controller()

        # Test 15-word mnemonic (Daedalus compatibility)
        test_with_mnemonic(
            "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon address".split(),
            seed_views.LoadSeedView.TYPE_15WORD,
        )


    def test_seed_words_pagination(self):
        """
            Viewing seed words should paginate the entire mnemonic with each word
            numbered by its position: 3 pages for 12 words, 4 pages for 15 words
            (final page shows only words 13-15), and 6 pages for 24 words.
        """
        def paginate_seed_words(mnemonic: list[str], expected_num_pages: int):
            BaseTest.reset_controller()
            controller = Controller.get_instance()
            controller.storage.set_pending_seed(Seed(mnemonic=mnemonic))
            controller.storage.finalize_pending_seed()

            captured = {}
            def fake_run_screen(self, screen_cls, **kwargs):
                captured.update(kwargs)
                return RET_CODE__BACK_BUTTON

            words_displayed = []
            numbers_displayed = []
            with patch.object(seed_views.SeedWordsView, "run_screen", fake_run_screen):
                for page_index in range(expected_num_pages):
                    seed_views.SeedWordsView(seed_num=0, page_index=page_index).run()
                    assert captured["num_pages"] == expected_num_pages
                    assert captured["title"] == f"Seed Words: {page_index + 1}/{expected_num_pages}"
                    if page_index < expected_num_pages - 1:
                        assert captured["button_data"] == [seed_views.SeedWordsView.NEXT]
                    else:
                        assert captured["button_data"] == [seed_views.SeedWordsView.DONE]
                    words_displayed.extend(captured["words"])
                    numbers_displayed.extend(
                        captured["page_index"] * captured["words_per_page"] + index + 1
                        for index in range(len(captured["words"]))
                    )

            assert words_displayed == mnemonic
            assert numbers_displayed == list(range(1, len(mnemonic) + 1))

        paginate_seed_words(
            "tone flat shed cool census soul paddle boy flight fantasy stem social".split(),
            expected_num_pages=3,
        )
        paginate_seed_words(
            "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon address".split(),
            expected_num_pages=4,
        )
        paginate_seed_words(
            "cotton artefact spy mind wing there echo steak child oak awful host despair online bicycle divorce middle firm diamond rare execute chimney almost hollow".split(),
            expected_num_pages=6,
        )


    def test_invalid_mnemonic(self):
        """ Should be able to go back and edit or discard an invalid mnemonic """
        # Test data from iancoleman.io
        mnemonic = "blush twice taste dawn feed second opinion lazy thumb play neglect impact".split()
        sequence = [
            FlowStep(MainMenuView, button_data_selection=MainMenuView.SEEDS),
            FlowStep(seed_views.SeedsMenuView, is_redirect=True),  # When no seeds are loaded it auto-redirects to LoadSeedView
            FlowStep(seed_views.LoadSeedView, button_data_selection=seed_views.LoadSeedView.TYPE_12WORD),
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
