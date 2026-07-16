import logging
import random
import time

from gettext import gettext as _

from seedsigner.gui.components import FontAwesomeIconConstants, GUIConstants, SeedSignerIconConstants
from seedsigner.gui.screens import (RET_CODE__BACK_BUTTON, ButtonListScreen,
    WarningScreen, DireWarningScreen, seed_screens)
from seedsigner.gui.screens.screen import ButtonOption, ButtonOptionWithoutTranslation
from seedsigner.models.encode_qr import CompactSeedQrEncoder, GenericStaticQrEncoder, SeedQrEncoder
from seedsigner.models.qr_type import QRType
from seedsigner.models.seed import Seed
from seedsigner.models.settings import Settings, SettingsConstants
from seedsigner.models.settings_definition import SettingsDefinition
from seedsigner.views.view import NotYetImplementedView, OptionDisabledView, View, Destination, BackStackView, MainMenuView, ErrorView

logger = logging.getLogger(__name__)



class SeedsMenuView(View):
    LOAD = ButtonOption("Load a seed")

    def __init__(self):
        super().__init__()
        self.seeds = []
        for seed in self.controller.storage.seeds:
            self.seeds.append({
                "fingerprint": seed.get_fingerprint()
            })


    def run(self):
        if not self.seeds:
            # Nothing to do here unless we have a seed loaded
            return Destination(LoadSeedView, clear_history=True)

        button_data = []
        for seed in self.seeds:
            button_data.append(ButtonOption(seed["fingerprint"], SeedSignerIconConstants.FINGERPRINT, icon_color=GUIConstants.ACCENT_TEXT_COLOR))
        button_data.append(self.LOAD)

        selected_menu_num = self.run_screen(
            ButtonListScreen,
            title=_("In-Memory Seeds"),
            is_button_text_centered=False,
            button_data=button_data
        )

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        elif len(self.seeds) > 0 and selected_menu_num < len(self.seeds):
            return Destination(SeedOptionsView, view_args={"seed_num": selected_menu_num})

        elif button_data[selected_menu_num] == self.LOAD:
            return Destination(LoadSeedView)



"""****************************************************************************
    Loading seeds, passphrases, etc
****************************************************************************"""
class LoadSeedView(View):
    SEED_QR = ButtonOption("Scan a SeedQR", SeedSignerIconConstants.QRCODE)
    TYPE_12WORD = ButtonOption("Enter 12-word seed", FontAwesomeIconConstants.KEYBOARD)
    TYPE_15WORD = ButtonOption("Enter 15-word seed", FontAwesomeIconConstants.KEYBOARD)
    TYPE_24WORD = ButtonOption("Enter 24-word seed", FontAwesomeIconConstants.KEYBOARD)
    CREATE = ButtonOption("Create a seed", SeedSignerIconConstants.PLUS)

    def run(self):
        button_data = [
            self.SEED_QR,
            self.TYPE_12WORD,
            self.TYPE_15WORD,
            self.TYPE_24WORD,
            self.CREATE,
        ]

        selected_menu_num = self.run_screen(
            ButtonListScreen,
            title=_("Load a Seed"),
            is_button_text_centered=False,
            button_data=button_data
        )

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        if button_data[selected_menu_num] == self.SEED_QR:
            from .scan_views import ScanSeedQRView
            return Destination(ScanSeedQRView)

        elif button_data[selected_menu_num] == self.CREATE:
            from .tools_views import ToolsMenuView
            return Destination(ToolsMenuView)

        elif button_data[selected_menu_num] == self.TYPE_12WORD:
            self.controller.storage.init_pending_mnemonic(num_words=12)
            return Destination(SeedMnemonicEntryView)

        elif button_data[selected_menu_num] == self.TYPE_15WORD:
            self.controller.storage.init_pending_mnemonic(num_words=15)
            return Destination(SeedMnemonicEntryView)

        elif button_data[selected_menu_num] == self.TYPE_24WORD:
            self.controller.storage.init_pending_mnemonic(num_words=24)
            return Destination(SeedMnemonicEntryView)



class SeedMnemonicEntryView(View):
    def __init__(self, cur_word_index: int = 0, is_calc_final_word: bool=False):
        super().__init__()
        self.cur_word_index = cur_word_index
        self.cur_word = self.controller.storage.get_pending_mnemonic_word(cur_word_index)
        self.is_calc_final_word = is_calc_final_word


    def run(self):
        ret = self.run_screen(
            seed_screens.SeedMnemonicEntryScreen,
            # TRANSLATOR_NOTE: Inserts the word number (e.g. "Seed Word #6")
            title=_("Seed Word #{}").format(self.cur_word_index + 1),  # Human-readable 1-indexing!
            initial_letters=list(self.cur_word) if self.cur_word else ["a"],
            wordlist=Seed.get_wordlist(wordlist_language_code=self.settings.get_value(SettingsConstants.SETTING__WORDLIST_LANGUAGE)),
        )

        if ret == RET_CODE__BACK_BUTTON:
            if self.cur_word_index > 0:
                return Destination(BackStackView)
            else:
                self.controller.storage.discard_pending_mnemonic()
                return Destination(MainMenuView)

        # ret will be our new mnemonic word
        self.controller.storage.update_pending_mnemonic(ret, self.cur_word_index)

        if self.is_calc_final_word and self.cur_word_index == self.controller.storage.pending_mnemonic_length - 2:
            # Time to calculate the last word. User must decide how they want to specify
            # the last bits of entropy for the final word.
            from seedsigner.views.tools_views import ToolsCalcFinalWordFinalizePromptView
            return Destination(ToolsCalcFinalWordFinalizePromptView)

        if self.is_calc_final_word and self.cur_word_index == self.controller.storage.pending_mnemonic_length - 1:
            # Time to calculate the last word. User must either select a final word to
            # contribute entropy to the checksum word OR we assume 0 ("abandon").
            from seedsigner.views.tools_views import ToolsCalcFinalWordShowFinalWordView
            return Destination(ToolsCalcFinalWordShowFinalWordView)

        if self.cur_word_index < self.controller.storage.pending_mnemonic_length - 1:
            return Destination(
                SeedMnemonicEntryView,
                view_args={
                    "cur_word_index": self.cur_word_index + 1,
                    "is_calc_final_word": self.is_calc_final_word
                }
            )
        else:
            # Attempt to finalize the mnemonic
            from seedsigner.models.seed import InvalidSeedException
            try:
                self.controller.storage.convert_pending_mnemonic_to_pending_seed()
            except InvalidSeedException:
                return Destination(SeedMnemonicInvalidView)

            return Destination(SeedFinalizeView)



class SeedMnemonicInvalidView(View):
    EDIT = ButtonOption("Review & edit")
    DISCARD = ButtonOption("Discard", button_label_color=GUIConstants.DESTRUCTIVE_ACTION_COLOR)

    def __init__(self):
        super().__init__()
        self.mnemonic: list[str] = self.controller.storage.pending_mnemonic


    def run(self):
        button_data = [self.EDIT, self.DISCARD]
        selected_menu_num = self.run_screen(
            DireWarningScreen,
            title=_("Invalid Mnemonic!"),
            status_icon_name=SeedSignerIconConstants.ERROR,
            status_headline=None,
            text=_("Checksum failure; not a valid seed phrase."),
            show_back_button=False,
            button_data=button_data,
        )

        if button_data[selected_menu_num] == self.EDIT:
            return Destination(SeedMnemonicEntryView, view_args={"cur_word_index": 0})

        elif button_data[selected_menu_num] == self.DISCARD:
            self.controller.storage.discard_pending_mnemonic()
            return Destination(MainMenuView)



class SeedFinalizeView(View):
    FINALIZE = ButtonOption("Done")
    PASSPHRASE = ButtonOption("BIP-39 Passphrase")

    def __init__(self):
        super().__init__()
        self.seed = self.controller.storage.get_pending_seed()

        if self.seed.get_fingerprint == "":
            # Expected normal user flow
            self.fingerprint = self.seed.get_fingerprint()

        else:
            # This view should display the "naked" seed's fingerprint. Normally the
            # just-loaded seed would be naked, but this is special handling for the
            # screenshot generator which creates a pending seed w/a passphrase already
            # set.
            passphrase = self.seed.passphrase
            self.seed.set_passphrase("")
            self.fingerprint = self.seed.get_fingerprint()
            self.seed.set_passphrase(passphrase)


    def run(self):
        button_data = [self.FINALIZE]
        self.PASSPHRASE.button_label = self.seed.passphrase_label
        if self.settings.get_value(SettingsConstants.SETTING__PASSPHRASE) != SettingsConstants.OPTION__DISABLED:
            button_data.append(self.PASSPHRASE)

        selected_menu_num = self.run_screen(
            seed_screens.SeedFinalizeScreen,
            fingerprint=self.fingerprint,
            button_data=button_data,
        )

        if button_data[selected_menu_num] == self.FINALIZE:
            from seedsigner.controller import Controller
            from seedsigner.gui.screens.screen import LoadingScreenThread
            loading_screen = LoadingScreenThread(text=_("Finalizing seed..."))
            loading_screen.start()
            try:
                seed_num = self.controller.storage.finalize_pending_seed()
            finally:
                loading_screen.stop()
            if self.controller.resume_main_flow == Controller.FLOW__CARDANO_ACCOUNT_EXPORT:
                from seedsigner.views.cardano_export_views import CardanoExportSelectSeedView
                self.controller.resume_main_flow = None
                return Destination(CardanoExportSelectSeedView, clear_history=True)
            if self.controller.resume_main_flow == Controller.FLOW__CARDANO_TX_SIGN:
                from seedsigner.views.cardano_export_views import CardanoTxSelectSeedView
                self.controller.resume_main_flow = None
                return Destination(CardanoTxSelectSeedView, clear_history=True)
            if self.controller.resume_main_flow == Controller.FLOW__CARDANO_CIP8_SIGN:
                from seedsigner.views.cardano_export_views import CardanoMsgSelectSeedView
                self.controller.resume_main_flow = None
                return Destination(CardanoMsgSelectSeedView, clear_history=True)
            return Destination(SeedOptionsView, view_args={"seed_num": seed_num}, clear_history=True)

        elif button_data[selected_menu_num] == self.PASSPHRASE:
            return Destination(SeedAddPassphraseView)

        elif selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)



class SeedAddPassphraseView(View):
    """
    initial_keyboard: used by the screenshot generator to render each different keyboard layout.
    """
    def __init__(self, initial_keyboard: str = seed_screens.SeedAddPassphraseScreen.KEYBOARD__LOWERCASE_BUTTON_TEXT):
        super().__init__()
        self.initial_keyboard = initial_keyboard
        self.seed = self.controller.storage.get_pending_seed()


    def run(self):
        passphrase_title=self.seed.passphrase_label
        ret_dict = self.run_screen(
            seed_screens.SeedAddPassphraseScreen,
            passphrase=self.seed.passphrase,
            title=passphrase_title,
            initial_keyboard=self.initial_keyboard,
        )

        # The new passphrase will be the return value; it might be empty.
        self.seed.set_passphrase(ret_dict["passphrase"])

        if "is_back_button" in ret_dict or len(self.seed.passphrase) == 0:
            return Destination(SeedAddPassphraseExitDialogView)

        else:
            return Destination(SeedReviewPassphraseView)



class SeedAddPassphraseExitDialogView(View):
    EDIT = ButtonOption("Edit passphrase")
    DISCARD = ButtonOption("Discard passphrase", button_label_color=GUIConstants.DESTRUCTIVE_ACTION_COLOR)
    SKIP = ButtonOption("Skip passphrase")  # NOT red since we're not throwing anything away

    def __init__(self):
        super().__init__()
        self.seed = self.controller.storage.get_pending_seed()


    def run(self):
        if self.seed.passphrase:
            title = _("Discard passphrase?")
            message = _("Your current passphrase entry will be erased.")
            button_data = [self.EDIT, self.DISCARD]
        else:
            title = _("Skip passphrase?")
            message = _("You have not entered a passphrase yet.")
            button_data = [self.EDIT, self.SKIP]

        selected_menu_num = self.run_screen(
            WarningScreen,
            title=title,
            status_headline=None,
            text=message,
            show_back_button=False,
            button_data=button_data,
        )

        if button_data[selected_menu_num] == self.EDIT:
            return Destination(SeedAddPassphraseView)

        elif button_data[selected_menu_num] in [self.DISCARD, self.SKIP]:
            self.seed.set_passphrase("")
            return Destination(SeedFinalizeView)



class SeedReviewPassphraseView(View):
    """
        Display the completed passphrase back to the user.
    """
    EDIT = ButtonOption("Edit passphrase")
    DONE = ButtonOption("Done")

    def __init__(self):
        super().__init__()
        self.seed = self.controller.storage.get_pending_seed()


    def run(self):
        # Get the before/after fingerprints
        passphrase = self.seed.passphrase
        fingerprint_with = self.seed.get_fingerprint()
        self.seed.set_passphrase("")
        fingerprint_without = self.seed.get_fingerprint()
        self.seed.set_passphrase(passphrase)

        button_data = [self.EDIT, self.DONE]

        # Because we have an explicit "Edit" button, we disable "BACK" to keep the
        # routing options sane.
        selected_menu_num = self.run_screen(
            seed_screens.SeedReviewPassphraseScreen,
            fingerprint_without=fingerprint_without,
            fingerprint_with=fingerprint_with,
            passphrase=self.seed.passphrase,
            button_data=button_data,
            show_back_button=False,
        )

        if button_data[selected_menu_num] == self.EDIT:
            return Destination(SeedAddPassphraseView)

        elif button_data[selected_menu_num] == self.DONE:
            from seedsigner.gui.screens.screen import LoadingScreenThread
            loading_screen = LoadingScreenThread(text=_("Finalizing seed..."))
            loading_screen.start()
            try:
                seed_num = self.controller.storage.finalize_pending_seed()
            finally:
                loading_screen.stop()
            return Destination(SeedOptionsView, view_args={"seed_num": seed_num}, clear_history=True)



class SeedDiscardView(View):
    KEEP = ButtonOption("Keep seed")
    DISCARD = ButtonOption("Discard", button_label_color=GUIConstants.DESTRUCTIVE_ACTION_COLOR)

    def __init__(self, seed_num: int = None):
        super().__init__()
        self.seed_num = seed_num
        if self.seed_num is not None:
            self.seed = self.controller.get_seed(self.seed_num)
        else:
            self.seed = self.controller.storage.pending_seed


    def run(self):
        button_data = [self.KEEP, self.DISCARD]

        fingerprint = self.seed.get_fingerprint()
        # TRANSLATOR_NOTE: Inserts the seed fingerprint
        text = _("Wipe seed {} from the device?").format(fingerprint)
        selected_menu_num = self.run_screen(
            WarningScreen,
            title=_("Discard Seed?"),
            status_headline=None,
            text=text,
            show_back_button=False,
            button_data=button_data,
        )

        if button_data[selected_menu_num] == self.KEEP:
            # Use skip_current_view=True to prevent BACK from landing on this warning screen
            if self.seed_num is not None:
                return Destination(SeedOptionsView, view_args={"seed_num": self.seed_num}, skip_current_view=True)
            else:
                return Destination(SeedFinalizeView, skip_current_view=True)

        elif button_data[selected_menu_num] == self.DISCARD:
            if self.seed_num is not None:
                self.controller.discard_seed(self.seed_num)
            else:
                self.controller.storage.clear_pending_seed()
            return Destination(MainMenuView, clear_history=True)



"""****************************************************************************
    Views for actions on individual seeds:
****************************************************************************"""
class SeedOptionsView(View):
    SCAN_TX = ButtonOption("Scan transaction", SeedSignerIconConstants.QRCODE)
    SIGN_MESSAGE = ButtonOption("Sign message", SeedSignerIconConstants.QRCODE)
    EXPORT_ACCOUNT_KEY = ButtonOption("Export account key")
    EXPLORER = ButtonOption("Address explorer")
    BACKUP = ButtonOption("Backup seed", right_icon_name=SeedSignerIconConstants.CHEVRON_RIGHT)
    DISCARD = ButtonOption("Discard seed", button_label_color=GUIConstants.DESTRUCTIVE_ACTION_COLOR)

    def __init__(self, seed_num: int):
        super().__init__()
        self.seed_num = seed_num
        self.seed = self.controller.get_seed(self.seed_num)

    def run(self):
        button_data = [
            self.SCAN_TX,
            self.SIGN_MESSAGE,
            self.EXPORT_ACCOUNT_KEY,
            self.EXPLORER,
            self.BACKUP,
            self.DISCARD,
        ]

        selected_menu_num = self.run_screen(
            seed_screens.SeedOptionsScreen,
            button_data=button_data,
            fingerprint=self.seed.get_fingerprint(),
        )

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(MainMenuView)

        if button_data[selected_menu_num] == self.SCAN_TX:
            from seedsigner.views.scan_views import ScanView
            self.controller.cardano_seed = self.controller.get_seed(self.seed_num)
            return Destination(ScanView)

        elif button_data[selected_menu_num] == self.SIGN_MESSAGE:
            from seedsigner.views.scan_views import ScanView
            self.controller.cardano_seed = self.controller.get_seed(self.seed_num)
            return Destination(ScanView)

        elif button_data[selected_menu_num] == self.EXPORT_ACCOUNT_KEY:
            from seedsigner.views.cardano_export_views import CardanoExportAccountKeyView
            return Destination(CardanoExportAccountKeyView, view_args=dict(seed_num=self.seed_num))

        elif button_data[selected_menu_num] == self.EXPLORER:
            from seedsigner.views.cardano_explorer_views import CardanoAddressExplorerNetworkView
            return Destination(CardanoAddressExplorerNetworkView, view_args=dict(seed_num=self.seed_num))

        elif button_data[selected_menu_num] == self.BACKUP:
            return Destination(SeedBackupView, view_args=dict(seed_num=self.seed_num))

        elif button_data[selected_menu_num] == self.DISCARD:
            return Destination(SeedDiscardView, view_args=dict(seed_num=self.seed_num))



class SeedBackupView(View):
    VIEW_WORDS = ButtonOption("View seed words")
    EXPORT_SEEDQR = ButtonOption("Export as SeedQR")

    def __init__(self, seed_num):
        super().__init__()
        self.seed_num = seed_num
        self.seed = self.controller.get_seed(self.seed_num)


    def run(self):
        button_data = [self.VIEW_WORDS]

        if self.seed.seedqr_supported:
            button_data.append(self.EXPORT_SEEDQR)

        selected_menu_num = self.run_screen(
            ButtonListScreen,
            title=_("Backup Seed"),
            button_data=button_data,
            is_bottom_list=True,
        )

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        elif button_data[selected_menu_num] == self.VIEW_WORDS:
            return Destination(SeedWordsWarningView, view_args={"seed_num": self.seed_num})

        elif button_data[selected_menu_num] == self.EXPORT_SEEDQR:
            return Destination(SeedTranscribeSeedQRFormatView, view_args={"seed_num": self.seed_num})



"""****************************************************************************
    View Seed Words flow
****************************************************************************"""
class SeedWordsWarningView(View):
    def __init__(self, seed_num: int):
        super().__init__()
        self.seed_num = seed_num


    def run(self):
        destination = Destination(
            SeedWordsView,
            view_args=dict(
                seed_num=self.seed_num,
                page_index=0,
            ),
            skip_current_view=True,  # Prevent going BACK to WarningViews
        )
        if self.settings.get_value(SettingsConstants.SETTING__DIRE_WARNINGS) == SettingsConstants.OPTION__DISABLED:
            # Forward straight to showing the words
            return destination

        selected_menu_num = self.run_screen(
            DireWarningScreen,
            text=_("You must keep your seed words private & away from all online devices."),
        )

        if selected_menu_num == 0:
            # User clicked "I Understand"
            return destination

        elif selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)



class SeedWordsView(View):
    NEXT = ButtonOption("Next")
    DONE = ButtonOption("Done")

    def __init__(self, seed_num: int, page_index: int = 0):
        super().__init__()
        self.seed_num = seed_num
        if self.seed_num is None:
            self.seed = self.controller.storage.get_pending_seed()
        else:
            self.seed = self.controller.get_seed(self.seed_num)
        self.page_index = page_index


    def run(self):
        # Slice the mnemonic to our current 4-word section
        words_per_page = 4  # TODO: eventually make this configurable for bigger screens?

        mnemonic = self.seed.mnemonic_display_list
        title = _("Seed Words")
        words = mnemonic[self.page_index*words_per_page:(self.page_index + 1)*words_per_page]

        button_data = []
        num_pages = (len(mnemonic) + words_per_page - 1) // words_per_page
        if self.page_index < num_pages - 1 or self.seed_num is None:
            button_data.append(self.NEXT)
        else:
            button_data.append(self.DONE)

        selected_menu_num = self.run_screen(
            seed_screens.SeedWordsScreen,
            title=f"{title}: {self.page_index+1}/{num_pages}",
            words=words,
            page_index=self.page_index,
            num_pages=num_pages,
            words_per_page=words_per_page,
            button_data=button_data,
        )

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        if button_data[selected_menu_num] == self.NEXT:
            if self.seed_num is None and self.page_index == num_pages - 1:
                return Destination(
                    SeedWordsBackupTestPromptView,
                    view_args=dict(seed_num=self.seed_num),
                )
            else:
                return Destination(
                    SeedWordsView,
                    view_args=dict(seed_num=self.seed_num, page_index=self.page_index + 1)
                )

        elif button_data[selected_menu_num] == self.DONE:
            # Must clear history to avoid BACK button returning to private info
            return Destination(
                SeedWordsBackupTestPromptView,
                view_args=dict(seed_num=self.seed_num),
            )



"""****************************************************************************
    Seed Words Backup Test
****************************************************************************"""
class SeedWordsBackupTestPromptView(View):
    VERIFY = ButtonOption("Verify")
    SKIP = ButtonOption("Skip")

    def __init__(self, seed_num: int):
        super().__init__()
        self.seed_num = seed_num


    def run(self):
        button_data = [self.VERIFY, self.SKIP]
        selected_menu_num = self.run_screen(
            seed_screens.SeedWordsBackupTestPromptScreen,
            button_data=button_data,
        )

        if button_data[selected_menu_num] == self.VERIFY:
            return Destination(
                SeedWordsBackupTestView,
                view_args=dict(seed_num=self.seed_num),
            )

        elif button_data[selected_menu_num] == self.SKIP:
            if self.seed_num is not None:
                return Destination(SeedOptionsView, view_args=dict(seed_num=self.seed_num))
            else:
                return Destination(SeedFinalizeView)



class SeedWordsBackupTestView(View):
    def __init__(self, seed_num: int, confirmed_list: list[bool] = None, cur_index: int = None, rand_seed: int = None):
        """
        Note: `rand_seed` is ONLY USED BY THE SCREENSHOT GENERATOR!!! (to ensure
        consistent screenshot results).
        """
        super().__init__()
        self.seed_num = seed_num
        if self.seed_num is None:
            self.seed = self.controller.storage.get_pending_seed()
        else:
            self.seed = self.controller.get_seed(self.seed_num)

        self.mnemonic_list = self.seed.mnemonic_display_list

        self.confirmed_list = confirmed_list
        if not self.confirmed_list:
            self.confirmed_list = []

        self.cur_index = cur_index
        self.rand_seed = rand_seed


    def run(self):
        from embit import bip39

        if self.rand_seed is not None:
            random.seed(self.rand_seed + self.cur_index if self.cur_index is not None else 0)

        if self.cur_index is None:
            self.cur_index = int(random.random() * len(self.mnemonic_list))
            while self.cur_index in self.confirmed_list:
                self.cur_index = int(random.random() * len(self.mnemonic_list))

        real_word = ButtonOptionWithoutTranslation(self.mnemonic_list[self.cur_index])
        fake_word1 = ButtonOptionWithoutTranslation(bip39.WORDLIST[int(random.random() * 2047)])
        fake_word2 = ButtonOptionWithoutTranslation(bip39.WORDLIST[int(random.random() * 2047)])
        fake_word3 = ButtonOptionWithoutTranslation(bip39.WORDLIST[int(random.random() * 2047)])

        button_data = [real_word, fake_word1, fake_word2, fake_word3]
        random.shuffle(button_data)

        # TRANSLATOR_NOTE: Inserts the word number (e.g. "Verify Word #1")
        title = _("Verify Word #{}").format(self.cur_index + 1)
        selected_menu_num = self.run_screen(
            ButtonListScreen,
            title=title,
            show_back_button=False,
            button_data=button_data,
            is_bottom_list=True,
            is_button_text_centered=True,
        )

        if button_data[selected_menu_num] == real_word:
            self.confirmed_list.append(self.cur_index)
            if len(self.confirmed_list) == len(self.mnemonic_list):
                # Successfully confirmed the full mnemonic!
                return Destination(
                    SeedWordsBackupTestSuccessView,
                    view_args=dict(seed_num=self.seed_num),
                )
            else:
                # Continue testing the remaining words
                return Destination(
                    SeedWordsBackupTestView,
                    view_args=dict(seed_num=self.seed_num, confirmed_list=self.confirmed_list),
                )

        else:
            # Picked the WRONG WORD!
            return Destination(
                SeedWordsBackupTestMistakeView,
                view_args=dict(
                    seed_num=self.seed_num,
                    cur_index=self.cur_index,
                    wrong_word=button_data[selected_menu_num].button_label,
                    confirmed_list=self.confirmed_list,
                )
            )



class SeedWordsBackupTestMistakeView(View):
    REVIEW = ButtonOption("Review seed words")
    RETRY = ButtonOption("Try again")

    def __init__(self, seed_num: int, cur_index: int = None, wrong_word: str = None, confirmed_list: list[bool] = None):
        super().__init__()
        self.seed_num = seed_num
        self.cur_index = cur_index
        self.wrong_word = wrong_word
        self.confirmed_list = confirmed_list


    def run(self):
        button_data = [self.REVIEW, self.RETRY]

        # TRANSLATOR_NOTE: Inserts the word number and the word (e.g. "Word #1 is not "apple"!")
        text = _("Word #{} is not \"{}\"!").format(self.cur_index + 1, self.wrong_word)

        # TRANSLATOR_NOTE: User selected the wrong word during the mnemonic backup test (e.g. incorrectly said the 5th word was "zoo")
        status_headline = _("Wrong Word!")

        selected_menu_num = self.run_screen(
            DireWarningScreen,
            title=_("Verification Error"),
            show_back_button=False,
            status_icon_name=SeedSignerIconConstants.ERROR,
            status_headline=status_headline,
            button_data=button_data,
            text=text,
        )

        if button_data[selected_menu_num] == self.REVIEW:
            return Destination(
                SeedWordsView,
                view_args=dict(seed_num=self.seed_num),
            )

        elif button_data[selected_menu_num] == self.RETRY:
            return Destination(
                SeedWordsBackupTestView,
                view_args=dict(
                    seed_num=self.seed_num,
                    confirmed_list=self.confirmed_list,
                    cur_index=self.cur_index,
                )
            )



class SeedWordsBackupTestSuccessView(View):
    def __init__(self, seed_num: int):
        super().__init__()
        self.seed_num = seed_num

    def run(self):
        from seedsigner.gui.screens.screen import LargeIconStatusScreen
        self.run_screen(
            LargeIconStatusScreen,
            title=_("Backup Verified"),
            show_back_button=False,
            status_headline=_("Success!"),
            text=_("All mnemonic backup words were successfully verified!"),
            button_data=[ButtonOption("OK")]
        )

        if self.seed_num is not None:
            return Destination(SeedOptionsView, view_args=dict(seed_num=self.seed_num), clear_history=True)
        else:
            return Destination(SeedFinalizeView)



"""****************************************************************************
    Export as SeedQR
****************************************************************************"""
class SeedTranscribeSeedQRFormatView(View):
    def __init__(self, seed_num: int):
        super().__init__()
        self.seed_num = seed_num

    def run(self):
        seed = self.controller.get_seed(self.seed_num)

        # Calculate QR module counts based on word count
        # Standard SeedQR: numeric data (4 digits per word)
        # Compact SeedQR: binary data (entropy bytes)
        num_words = len(seed.mnemonic_list)
        standard_modules, compact_modules = self._get_qr_module_counts(num_words)

        if self.settings.get_value(SettingsConstants.SETTING__COMPACT_SEEDQR) != SettingsConstants.OPTION__ENABLED:
            return Destination(
                SeedTranscribeSeedQRWarningView,
                view_args={
                    "seed_num": self.seed_num,
                    "seedqr_format": QRType.SEED__SEEDQR,
                    "num_modules": standard_modules,
                },
                skip_current_view=True,
            )

        STANDARD = ButtonOption(f"Standard: {standard_modules}x{standard_modules}", return_data=standard_modules)
        COMPACT = ButtonOption(f"Compact: {compact_modules}x{compact_modules}", return_data=compact_modules)
        button_data = [STANDARD, COMPACT]

        selected_menu_num = self.run_screen(
            seed_screens.SeedTranscribeSeedQRFormatScreen,
            title=_("SeedQR Format"),
            button_data=button_data,
        )

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        if button_data[selected_menu_num] == STANDARD:
            seedqr_format = QRType.SEED__SEEDQR
        else:
            seedqr_format = QRType.SEED__COMPACTSEEDQR

        num_modules = button_data[selected_menu_num].return_data

        return Destination(
            SeedTranscribeSeedQRWarningView,
            view_args={
                "seed_num": self.seed_num,
                "seedqr_format": seedqr_format,
                "num_modules": num_modules,
            }
        )

    @staticmethod
    def _get_qr_module_counts(num_words: int) -> tuple[int, int]:
        """Return (standard_modules, compact_modules) for a given word count."""
        # Standard SeedQR: 4 numeric digits per word
        # Compact SeedQR: entropy bytes = num_words * 4 // 3
        # QR version determines module count: version N = 4N + 17 modules
        # Lookup based on actual QR encoding capacity
        standard_map = {12: 25, 15: 25, 24: 29}
        compact_map = {12: 21, 15: 21, 24: 25}
        return standard_map.get(num_words, 29), compact_map.get(num_words, 25)



class SeedTranscribeSeedQRWarningView(View):
    def __init__(self, seed_num: int, seedqr_format: str = QRType.SEED__SEEDQR, num_modules: int = 29):
        super().__init__()
        self.seed_num = seed_num
        self.seedqr_format = seedqr_format
        self.num_modules = num_modules


    def run(self):
        destination = Destination(
            SeedTranscribeSeedQRWholeQRView,
            view_args={
                "seed_num": self.seed_num,
                "seedqr_format": self.seedqr_format,
                "num_modules": self.num_modules,
            },
            skip_current_view=True,  # Prevent going BACK to WarningViews
        )

        if self.settings.get_value(SettingsConstants.SETTING__DIRE_WARNINGS) == SettingsConstants.OPTION__DISABLED:
            # Forward straight to transcribing the SeedQR
            return destination

        selected_menu_num = self.run_screen(
            DireWarningScreen,
            status_headline=_("SeedQR is your private key!"),
            text=_("Never photograph or scan it into a device that connects to the internet."),
        )

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        else:
            # User clicked "I Understand"
            return destination



class SeedTranscribeSeedQRWholeQRView(View):
    def __init__(self, seed_num: int, seedqr_format: str, num_modules: int):
        super().__init__()
        self.seed_num = seed_num
        self.seedqr_format = seedqr_format
        self.num_modules = num_modules
        self.seed = self.controller.get_seed(seed_num)


    def run(self):
        encoder_args = dict(mnemonic=self.seed.mnemonic_list,
                            wordlist_language_code=self.settings.get_value(SettingsConstants.SETTING__WORDLIST_LANGUAGE))
        if self.seedqr_format == QRType.SEED__SEEDQR:
            e = SeedQrEncoder(**encoder_args)
        elif self.seedqr_format == QRType.SEED__COMPACTSEEDQR:
            e = CompactSeedQrEncoder(**encoder_args)

        data = e.next_part()

        ret = self.run_screen(
            seed_screens.SeedTranscribeSeedQRWholeQRScreen,
            qr_data=data,
            num_modules=self.num_modules,
        )

        if ret == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        else:
            return Destination(
                SeedTranscribeSeedQRZoomedInView,
                view_args={
                    "seed_num": self.seed_num,
                    "seedqr_format": self.seedqr_format
                }
            )



class SeedTranscribeSeedQRZoomedInView(View):
    """
    intial_zone_x, initial_zone_y: Used by the screenshot generator to shift the view
    to a more interesting part of the QR code template.
    """
    def __init__(self, seed_num: int, seedqr_format: str, initial_zone_x: int = 0, initial_zone_y: int = 0):
        super().__init__()
        self.seed_num = seed_num
        self.seedqr_format = seedqr_format
        self.seed = self.controller.get_seed(seed_num)
        self.initial_zone_x = initial_zone_x
        self.initial_zone_y = initial_zone_y


    def run(self):
        encoder_args = dict(mnemonic=self.seed.mnemonic_list,
                            wordlist_language_code=self.settings.get_value(SettingsConstants.SETTING__WORDLIST_LANGUAGE))
        if self.seedqr_format == QRType.SEED__SEEDQR:
            e = SeedQrEncoder(**encoder_args)
        elif self.seedqr_format == QRType.SEED__COMPACTSEEDQR:
            e = CompactSeedQrEncoder(**encoder_args)

        data = e.next_part()

        num_words = len(self.seed.mnemonic_list)
        standard_modules, compact_modules = SeedTranscribeSeedQRFormatView._get_qr_module_counts(num_words)
        if self.seedqr_format == QRType.SEED__COMPACTSEEDQR:
            num_modules = compact_modules
        else:
            num_modules = standard_modules

        self.run_screen(
            seed_screens.SeedTranscribeSeedQRZoomedInScreen,
            qr_data=data,
            num_modules=num_modules,
            initial_zone_x=self.initial_zone_x,
            initial_zone_y=self.initial_zone_y,
        )

        return Destination(SeedTranscribeSeedQRConfirmQRPromptView, view_args={"seed_num": self.seed_num})



class SeedTranscribeSeedQRConfirmQRPromptView(View):
    SCAN = ButtonOption("Confirm SeedQR", SeedSignerIconConstants.QRCODE)
    DONE = ButtonOption("Done")

    def __init__(self, seed_num: int):
        super().__init__()
        self.seed_num = seed_num
        self.seed = self.controller.get_seed(seed_num)


    def run(self):
        button_data = [self.SCAN, self.DONE]

        selected_menu_option = self.run_screen(
            seed_screens.SeedTranscribeSeedQRConfirmQRPromptScreen,
            title=_("Confirm SeedQR?"),
            button_data=button_data,
        )

        if selected_menu_option == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        elif button_data[selected_menu_option] == self.SCAN:
            return Destination(SeedTranscribeSeedQRConfirmScanView, view_args={"seed_num": self.seed_num})

        elif button_data[selected_menu_option] == self.DONE:
            return Destination(SeedOptionsView, view_args={"seed_num": self.seed_num}, clear_history=True)



class SeedTranscribeSeedQRConfirmScanView(View):
    def __init__(self, seed_num: int):
        from seedsigner.models.decode_qr import DecodeQR
        super().__init__()
        self.seed_num = seed_num
        self.seed = self.controller.get_seed(seed_num)
        wordlist_language_code = self.settings.get_value(SettingsConstants.SETTING__WORDLIST_LANGUAGE)
        self.decoder = DecodeQR(wordlist_language_code=wordlist_language_code)

    def run(self):
        from seedsigner.gui.screens.scan_screens import ScanScreen

        # Run the live preview and QR code capture process
        # TODO: Does this belong in its own BaseThread?
        scanning_done=self.run_screen(
            ScanScreen,
            decoder=self.decoder,
            instructions_text=_("Scan your SeedQR")
        )

        # If the scanning was canceled because the back button was pressed, return to BackStackView (SeedTranscribeSeedQRConfirmQRPromptView).
        if scanning_done==False:
           return Destination(BackStackView, skip_current_view=False)

        if self.decoder.is_complete:
            if self.decoder.is_seed:
                seed_mnemonic = self.decoder.get_seed_phrase()
                # Found a valid mnemonic seed! But does it match?
                if seed_mnemonic != self.seed.mnemonic_list:
                    return Destination(SeedTranscribeSeedQRConfirmWrongSeedView, skip_current_view=True)
                else:
                    return Destination(SeedTranscribeSeedQRConfirmSuccessView, view_args={"seed_num": self.seed_num})

        # Will trigger if a different kind of QR code is scanned (non SeedQR)
        return Destination(SeedTranscribeSeedQRConfirmInvalidQRView, skip_current_view=True)



class SeedTranscribeSeedQRConfirmWrongSeedView(View):
    """
    A valid SeedQR was scanned but it did NOT match the one we just transcribed!
    """
    def run(self):
        self.run_screen(
            DireWarningScreen,
            title=_("Confirm SeedQR"),
            status_headline=_("Error!"),
            text=_("Your transcribed SeedQR does not match your original seed!"),
            show_back_button=False,
            button_data=[ButtonOption("Review SeedQR")],
        )

        # Skip BACK to the zoomed in transcription view
        return Destination(BackStackView, skip_current_view=True)



class SeedTranscribeSeedQRConfirmInvalidQRView(View):
    """
    A QR code was scanned but it was not a SeedQR and certainly not the SeedQR we just
    transcribed!
    """
    def run(self):
        # TODO: A better error message would be something like: "The QR code you scanned does not contain a valid SeedQR."
        self.run_screen(
            DireWarningScreen,
            title=_("Confirm SeedQR"),
            status_headline=_("Error!"),
            text=_("Your transcribed SeedQR could not be read!"),
            show_back_button=False,
            button_data=[ButtonOption("Review SeedQR")],
        )

        # Skip BACK to the zoomed in transcription view
        return Destination(BackStackView, skip_current_view=True)



class SeedTranscribeSeedQRConfirmSuccessView(View):
    """
    The SeedQR we just scanned matched the one we just transcribed.
    """
    def __init__(self, seed_num: int):
        super().__init__()
        self.seed_num = seed_num


    def run(self):
        from seedsigner.gui.screens.screen import LargeIconStatusScreen
        self.run_screen(
            LargeIconStatusScreen,
            title=_("Confirm SeedQR"),
            status_headline=_("Success!"),
            text=_("Your transcribed SeedQR successfully scanned and yielded the same seed."),
            show_back_button=False,
            button_data=[ButtonOption("OK")],
        )

        return Destination(SeedOptionsView, view_args={"seed_num": self.seed_num})

