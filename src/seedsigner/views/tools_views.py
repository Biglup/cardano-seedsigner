import hashlib
import logging
import os
import time

from gettext import gettext as _

from seedsigner.gui.components import FontAwesomeIconConstants, GUIConstants, SeedSignerIconConstants, resize_image_to_fill
from seedsigner.gui.screens import RET_CODE__BACK_BUTTON, ButtonListScreen
from seedsigner.gui.screens.screen import ButtonOption
from seedsigner.helpers import mnemonic_generation
from seedsigner.models.seed import Seed
from seedsigner.models.settings_definition import SettingsConstants
from seedsigner.views.seed_views import SeedDiscardView, SeedFinalizeView, SeedMnemonicEntryView, SeedWordsWarningView

from .view import View, Destination, BackStackView

logger = logging.getLogger(__name__)



class ToolsMenuView(View):
    IMAGE = ButtonOption("New seed", FontAwesomeIconConstants.CAMERA)
    DICE = ButtonOption("New seed", FontAwesomeIconConstants.DICE)
    KEYBOARD = ButtonOption("Calc 12th/24th word", FontAwesomeIconConstants.KEYBOARD)

    def run(self):
        button_data = [self.IMAGE, self.DICE, self.KEYBOARD]

        selected_menu_num = self.run_screen(
            ButtonListScreen,
            title=_("Tools"),
            is_button_text_centered=False,
            button_data=button_data
        )

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        elif button_data[selected_menu_num] == self.IMAGE:
            return Destination(ToolsImageEntropyLivePreviewView)

        elif button_data[selected_menu_num] == self.DICE:
            return Destination(ToolsDiceEntropyMnemonicLengthView)

        elif button_data[selected_menu_num] == self.KEYBOARD:
            return Destination(ToolsCalcFinalWordNumWordsView)



"""****************************************************************************
    Image entropy Views
****************************************************************************"""
class ToolsImageEntropyLivePreviewView(View):
    def run(self):
        from seedsigner.gui.screens.tools_screens import ToolsImageEntropyLivePreviewScreen
        self.controller.image_entropy_preview_frames = None
        ret = self.run_screen(ToolsImageEntropyLivePreviewScreen)

        if ret == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)
        
        self.controller.image_entropy_preview_frames = ret
        return Destination(ToolsImageEntropyFinalImageView)



class ToolsImageEntropyFinalImageView(View):
    def run(self):
        from PIL import Image
        from PIL.ImageOps import autocontrast
        from seedsigner.gui.screens.tools_screens import ToolsImageEntropyFinalImageScreen
        if not self.controller.image_entropy_final_image:
            from seedsigner.hardware.camera import Camera
            # Take the final full-res image
            camera = Camera.get_instance()
            max_dim = max(self.canvas_width, self.canvas_height)

            # Final image will be at least 4x the number of pixels the screen can
            # actually display.
            camera.start_single_frame_mode(resolution=(2*max_dim, 2*max_dim))

            time.sleep(0.25)
            self.controller.image_entropy_final_image = camera.capture_frame()
            camera.stop_single_frame_mode()

        # Prep a copy of the image for display:
        #   * Boost the contrast for better presentation (but preserve the original pixels)
        #   * Resize it to fit the screen
        boosted_version = autocontrast(self.controller.image_entropy_final_image, cutoff=2)
        display_version = resize_image_to_fill(
            boosted_version,
            target_size_x=self.canvas_width,
            target_size_y=self.canvas_height,
            sampling_method=Image.Resampling.BICUBIC,
        )
        
        ret = self.run_screen(
            ToolsImageEntropyFinalImageScreen,
            final_image=display_version
        )

        if ret == RET_CODE__BACK_BUTTON:
            # Go back to live preview and reshoot
            self.controller.image_entropy_final_image = None
            return Destination(BackStackView)
        
        return Destination(ToolsImageEntropyMnemonicLengthView)



class ToolsImageEntropyMnemonicLengthView(View):
    TWELVE_WORDS = ButtonOption("12 words", return_data=12)
    TWENTYFOUR_WORDS = ButtonOption("24 words", return_data=24)

    def run(self):
        button_data = [self.TWELVE_WORDS, self.TWENTYFOUR_WORDS]

        selected_menu_num = self.run_screen(
            ButtonListScreen,
            title=_("Mnemonic Length"),
            button_data=button_data,
        )

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        mnemonic_length = button_data[selected_menu_num].return_data

        # The entropy calculation can take time, especially with a full image buffer. 
        # Show a loading spinner to provide feedback during this delay.
        from seedsigner.gui.screens.screen import LoadingScreenThread
        self.loading_screen = LoadingScreenThread(text=_("Calculating..."))
        self.loading_screen.start()

        try:
            preview_images = self.controller.image_entropy_preview_frames
            seed_entropy_image = self.controller.image_entropy_final_image

            # Build in some hardware-level uniqueness via CPU unique Serial num
            try:
                stream = os.popen("cat /proc/cpuinfo | grep Serial")
                output = stream.read()
                serial_num = output.split(":")[-1].strip().encode('utf-8')
                serial_hash = hashlib.sha256(serial_num)
                hash_bytes = serial_hash.digest()
            except Exception as e:
                logger.info(repr(e), exc_info=True)
                hash_bytes = b'0'

            # Build in modest entropy via millis since power on
            millis_hash = hashlib.sha256(hash_bytes + str(time.time()).encode('utf-8'))
            hash_bytes = millis_hash.digest()

            # Build in better entropy by chaining the preview frames
            for frame in preview_images:
                img_hash = hashlib.sha256(hash_bytes + frame.tobytes())
                hash_bytes = img_hash.digest()

            # Finally build in our headline entropy via the new full-res image
            final_hash = hashlib.sha256(hash_bytes + seed_entropy_image.tobytes()).digest()

            if mnemonic_length == 12:
                # 12-word mnemonic only uses the first 128 bits / 16 bytes of entropy
                final_hash = final_hash[:16]

            # Generate the mnemonic
            mnemonic = mnemonic_generation.generate_mnemonic_from_bytes(final_hash)

            # Image should never get saved nor stick around in memory
            seed_entropy_image = None
            preview_images = None
            final_hash = None
            hash_bytes = None
            self.controller.image_entropy_preview_frames = None
            self.controller.image_entropy_final_image = None

            # Add the mnemonic as an in-memory Seed
            seed = Seed(mnemonic, wordlist_language_code=self.settings.get_value(SettingsConstants.SETTING__WORDLIST_LANGUAGE))
            self.controller.storage.set_pending_seed(seed)

        finally:
            # Stop spinner even if an error occurs
            self.loading_screen.stop()

        # Cannot return BACK to this View
        return Destination(SeedWordsWarningView, view_args={"seed_num": None}, clear_history=True)



"""****************************************************************************
    Dice rolls Views
****************************************************************************"""
class ToolsDiceEntropyMnemonicLengthView(View):
    def run(self):
        # Since we're dynamically building the ButtonOption button_labels here, it's too
        # awkward to use the usual class-level attr approach.

        # TRANSLATOR_NOTE: Inserts the number of dice rolls needed for a 12-word mnemonic
        twelve = _("12 words ({} rolls)").format(mnemonic_generation.DICE__NUM_ROLLS__12WORD)
        TWELVE = ButtonOption(twelve, return_data=mnemonic_generation.DICE__NUM_ROLLS__12WORD)

        # TRANSLATOR_NOTE: Inserts the number of dice rolls needed for a 24-word mnemonic
        twenty_four = _("24 words ({} rolls)").format(mnemonic_generation.DICE__NUM_ROLLS__24WORD)
        TWENTY_FOUR = ButtonOption(twenty_four, return_data=mnemonic_generation.DICE__NUM_ROLLS__24WORD)

        button_data = [TWELVE, TWENTY_FOUR]
        selected_menu_num = self.run_screen(
            ButtonListScreen,
            title=_("Mnemonic Length"),
            is_bottom_list=True,
            is_button_text_centered=True,
            button_data=button_data,
        )

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        elif button_data[selected_menu_num] == TWELVE:
            return Destination(ToolsDiceEntropyEntryView, view_args=dict(total_rolls=mnemonic_generation.DICE__NUM_ROLLS__12WORD))

        elif button_data[selected_menu_num] == TWENTY_FOUR:
            return Destination(ToolsDiceEntropyEntryView, view_args=dict(total_rolls=mnemonic_generation.DICE__NUM_ROLLS__24WORD))



class ToolsDiceEntropyEntryView(View):
    def __init__(self, total_rolls: int):
        super().__init__()
        self.total_rolls = total_rolls
    

    def run(self):
        from seedsigner.gui.screens.tools_screens import ToolsDiceEntropyEntryScreen
        ret = self.run_screen(
            ToolsDiceEntropyEntryScreen,
            return_after_n_chars=self.total_rolls,
        )

        if ret == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)
        
        dice_seed_phrase = mnemonic_generation.generate_mnemonic_from_dice(ret)

        # Add the mnemonic as an in-memory Seed
        seed = Seed(dice_seed_phrase, wordlist_language_code=self.settings.get_value(SettingsConstants.SETTING__WORDLIST_LANGUAGE))
        self.controller.storage.set_pending_seed(seed)

        # Cannot return BACK to this View
        return Destination(SeedWordsWarningView, view_args={"seed_num": None}, clear_history=True)



"""****************************************************************************
    Calc final word Views
****************************************************************************"""
class ToolsCalcFinalWordNumWordsView(View):
    TWELVE = ButtonOption("12 words", return_data=12)
    FIFTEEN = ButtonOption("15 words", return_data=15)
    TWENTY_FOUR = ButtonOption("24 words", return_data=24)

    def run(self):
        button_data = [self.TWELVE, self.FIFTEEN, self.TWENTY_FOUR]

        selected_menu_num = self.run_screen(
            ButtonListScreen,
            title=_("Mnemonic Length"),
            is_bottom_list=True,
            is_button_text_centered=True,
            button_data=button_data,
        )

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        self.controller.storage.init_pending_mnemonic(button_data[selected_menu_num].return_data)

        return Destination(SeedMnemonicEntryView, view_args=dict(is_calc_final_word=True))



class ToolsCalcFinalWordFinalizePromptView(View):
    # TRANSLATOR_NOTE: Label to gather entropy through coin tosses
    COIN_FLIPS = ButtonOption("Coin flip entropy")

    # TRANSLATOR_NOTE: Label to gather entropy through user specified BIP-39 word
    SELECT_WORD = ButtonOption("Word selection entropy")

    # TRANSLATOR_NOTE: Label to allow user to default entropy as all-zeros
    ZEROS = ButtonOption("Finalize with zeros")

    def run(self):
        from seedsigner.gui.screens.tools_screens import ToolsCalcFinalWordFinalizePromptScreen
        mnemonic = self.controller.storage.pending_mnemonic
        mnemonic_length = len(mnemonic)
        # BIP-39: checksum bits = word_count // 3, entropy bits in final word = 11 - checksum
        num_entropy_bits = 11 - (mnemonic_length // 3)

        button_data = [self.COIN_FLIPS, self.SELECT_WORD, self.ZEROS]
        selected_menu_num = self.run_screen(
            ToolsCalcFinalWordFinalizePromptScreen,
            mnemonic_length=mnemonic_length,
            num_entropy_bits=num_entropy_bits,
            button_data=button_data,
        )

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        elif button_data[selected_menu_num] == self.COIN_FLIPS:
            return Destination(ToolsCalcFinalWordCoinFlipsView)

        elif button_data[selected_menu_num] == self.SELECT_WORD:
            # Clear the final word slot, just in case we're returning via BACK button
            self.controller.storage.update_pending_mnemonic(None, mnemonic_length - 1)
            return Destination(SeedMnemonicEntryView, view_args=dict(is_calc_final_word=True, cur_word_index=mnemonic_length - 1))

        elif button_data[selected_menu_num] == self.ZEROS:
            # User skipped the option to select a final word to provide last bits of
            # entropy. We'll insert all zeros and piggy-back on the coin flip attr
            wordlist_language_code = self.settings.get_value(SettingsConstants.SETTING__WORDLIST_LANGUAGE)
            self.controller.storage.update_pending_mnemonic(Seed.get_wordlist(wordlist_language_code)[0], mnemonic_length - 1)
            return Destination(ToolsCalcFinalWordShowFinalWordView, view_args=dict(coin_flips="0" * num_entropy_bits))



class ToolsCalcFinalWordCoinFlipsView(View):
    def run(self):
        from seedsigner.gui.screens.tools_screens import ToolsCoinFlipEntryScreen
        mnemonic_length = len(self.controller.storage.pending_mnemonic)

        total_flips = 11 - (mnemonic_length // 3)
        
        ret_val = self.run_screen(
            ToolsCoinFlipEntryScreen,
            return_after_n_chars=total_flips,
        )

        if ret_val == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)
        
        else:
            return Destination(ToolsCalcFinalWordShowFinalWordView, view_args=dict(coin_flips=ret_val))



class ToolsCalcFinalWordShowFinalWordView(View):
    NEXT = ButtonOption("Next")

    def __init__(self, coin_flips: str = None):
        super().__init__()
        # Construct the actual final word. The user's selected_final_word
        # contributes:
        #   * 3 bits to a 24-word seed (plus 8-bit checksum)
        #   * 7 bits to a 12-word seed (plus 4-bit checksum)
        from seedsigner.helpers import mnemonic_generation

        wordlist_language_code = self.settings.get_value(SettingsConstants.SETTING__WORDLIST_LANGUAGE)
        wordlist = Seed.get_wordlist(wordlist_language_code)

        # Prep the user's selected word / coin flips and the actual final word for
        # the display.
        if coin_flips:
            self.selected_final_word = None
            self.selected_final_bits = coin_flips
        else:
            # Convert the user's final word selection into its binary index equivalent
            self.selected_final_word = self.controller.storage.pending_mnemonic[-1]
            self.selected_final_bits = format(wordlist.index(self.selected_final_word), '011b')

        if coin_flips:
            # fill the last bits (what will eventually be the checksum) with zeros
            binary_string = coin_flips + "0" * (11 - len(coin_flips))

            # retrieve the matching word for the resulting index
            wordlist_index = int(binary_string, 2)
            wordlist = Seed.get_wordlist(self.controller.settings.get_value(SettingsConstants.SETTING__WORDLIST_LANGUAGE))
            word = wordlist[wordlist_index]

            # update the pending mnemonic with our new "final" (pre-checksum) word
            self.controller.storage.update_pending_mnemonic(word, -1)

        # Now calculate the REAL final word (has a proper checksum)
        final_mnemonic = mnemonic_generation.calculate_checksum(
            mnemonic=self.controller.storage.pending_mnemonic,
            wordlist_language_code=wordlist_language_code,
        )

        # Update our pending mnemonic with the real final word
        self.controller.storage.update_pending_mnemonic(final_mnemonic[-1], -1)

        mnemonic = self.controller.storage.pending_mnemonic
        mnemonic_length = len(mnemonic)

        # And grab the actual final word's checksum bits
        self.actual_final_word = self.controller.storage.pending_mnemonic[-1]
        num_checksum_bits = mnemonic_length // 3
        self.checksum_bits = format(wordlist.index(self.actual_final_word), '011b')[-num_checksum_bits:]


    def run(self):
        from seedsigner.gui.screens.tools_screens import ToolsCalcFinalWordScreen
        button_data = [self.NEXT]

        # TRANSLATOR_NOTE: label to calculate the last word of a BIP-39 mnemonic seed phrase
        title = _("Final Word Calc")

        selected_menu_num = self.run_screen(
            ToolsCalcFinalWordScreen,
            title=title,
            button_data=button_data,
            selected_final_word=self.selected_final_word,
            selected_final_bits=self.selected_final_bits,
            checksum_bits=self.checksum_bits,
            actual_final_word=self.actual_final_word,
        )

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        elif button_data[selected_menu_num] == self.NEXT:
            return Destination(ToolsCalcFinalWordDoneView)



class ToolsCalcFinalWordDoneView(View):
    LOAD = ButtonOption("Load seed")
    DISCARD = ButtonOption("Discard", button_label_color=GUIConstants.DESTRUCTIVE_ACTION_COLOR)

    def run(self):
        from seedsigner.gui.screens.tools_screens import ToolsCalcFinalWordDoneScreen
        mnemonic = self.controller.storage.pending_mnemonic
        mnemonic_word_length = len(mnemonic)
        final_word = mnemonic[-1]

        button_data = [self.LOAD, self.DISCARD]

        selected_menu_num = self.run_screen(
            ToolsCalcFinalWordDoneScreen,
            final_word=final_word,
            mnemonic_word_length=mnemonic_word_length,
            fingerprint=self.controller.storage.get_pending_mnemonic_fingerprint(),
            button_data=button_data,
        )

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)
        
        self.controller.storage.convert_pending_mnemonic_to_pending_seed()

        if button_data[selected_menu_num] == self.LOAD:
            return Destination(SeedFinalizeView)
        
        elif button_data[selected_menu_num] == self.DISCARD:
            return Destination(SeedDiscardView)

