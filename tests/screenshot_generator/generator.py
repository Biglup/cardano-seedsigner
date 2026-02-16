from dataclasses import dataclass
import embit
import pathlib
import pytest
import os
import random
import sys
import time
from unittest.mock import Mock, patch, MagicMock
from PIL import ImageFont

from embit import compact
from embit.psbt import PSBT, OutputScope
from embit.script import Script

# Prevent importing modules w/Raspi hardware dependencies.
# These must precede any SeedSigner imports.
sys.modules['seedsigner.hardware.displays.st7789_mpy'] = MagicMock()
sys.modules['seedsigner.hardware.displays.ili9341'] = MagicMock()
sys.modules['seedsigner.views.screensaver.ScreensaverScreen'] = MagicMock()
sys.modules['RPi'] = MagicMock()
sys.modules['RPi.GPIO'] = MagicMock()
sys.modules['seedsigner.hardware.camera.Camera'] = MagicMock()
sys.modules['seedsigner.hardware.microsd'] = MagicMock()

from seedsigner.controller import Controller
from seedsigner.gui.components import GUIConstants
from seedsigner.gui.renderer import Renderer
from seedsigner.gui.screens.screen import BaseScreen
from seedsigner.gui.screens.seed_screens import SeedAddPassphraseScreen
from seedsigner.gui.toast import RemoveSDCardToastManagerThread, SDCardStateChangeToastManagerThread
from seedsigner.gui.toast import DefaultToast, InfoToast, SuccessToast, WarningToast, ErrorToast, DireWarningToast
from seedsigner.hardware.microsd import MicroSD
from seedsigner.helpers import embit_utils
from seedsigner.models.decode_qr import DecodeQR
from seedsigner.models.encode_qr import BaseQrEncoder
from seedsigner.models.psbt_parser import OPCODES, PSBTParser
from seedsigner.models.qr_type import QRType
from seedsigner.models.seed import Seed
from seedsigner.models.settings import Settings
from seedsigner.models.settings_definition import SettingsConstants, SettingsDefinition
from seedsigner.views import (MainMenuView, PowerOptionsView, RestartView, RemoveMicroSDWarningView, NotYetImplementedView, UnhandledExceptionView,
    psbt_views, seed_views, settings_views, tools_views, scan_views, cardano_tx_views)
from seedsigner.models.cardano_tx import CardanoSignRequest, CardanoParsedTx, SigningInput, ChangeOutput, ExtraSigner
from seedsigner.views.screensaver import OpeningSplashView
from seedsigner.views.view import CameraConnectionErrorView, NetworkMismatchErrorView, OptionDisabledView, PowerOffView

from .utils import ScreenshotComplete, ScreenshotConfig, ScreenshotRenderer

import warnings; warnings.warn = lambda *args, **kwargs: None

# Dynamically generate a pytest test run for each locale
@pytest.mark.parametrize("locale", [x for x, y in SettingsConstants.get_detected_languages()])
def test_generate_all(locale, target_locale):
    """
    `target_locale` is a fixture created in conftest.py via the `--locale` command line arg.

    Optionally skips all other locales.
    """
    if target_locale and locale != target_locale:
        pytest.skip(f"Skipping {locale}")
    
    if not ImageFont.core.HAVE_RAQM:
        # We can't generate pixel-perfect screenshots that match what gets rendered on
        # the device if we don't have libraqm.
        pytest.fail("libraqm is not installed.")
    
    generate_screenshots(locale)



"""**************************************************************************************
    Set up global test data that will be re-used across a variety of screenshots and for
    all locales.
**************************************************************************************"""
# Single sig ("abandon" test wallet) tx; 1mil sat input, 1 external output, 1 self-transfer, 1 change output, 400 sat fee
BASE64_SINGLE_SIG_PSBT = """cHNidP8BAJACAAAAAT8SmJzLhTMNgtn9QOmBmet0nnqqIJpsgpgBN5JWNJCxAQAAAAD9////A5CfBwAAAAAAFgAULzSqHPAKU7BVopGgOn1F8KaYi1KQ0AMAAAAAABYAFGQh2ztS8DzX4kGVKUKQhFPrlNNIkNADAAAAAAAWABRvoBZQCjxqc367Jg4t3KeLqSNFWGYAAABPAQQ1h88DDvSxr4AAAAA8jCA37kwWIdoNNI21EWNwmmItDSg43ebYQZxR9jAcYgO4jg++P2RjN+2TvAwPO4Q/z30lieXsiEdU5kAgJ6iQtBBzxdoKVAAAgAEAAIAAAACAAAEAcQIAAAABF84F9MpvLC1H3Cyews1xoNZ4ch3uJMu8jonehCIqmScAAAAAAP3///8CM6/2KQEAAAAWABQQumvlzzcWsGXBNIOliqXTvr9YxEBCDwAAAAAAFgAU0MSj7wnpl7bpnjl+UY/j5BoRjKFNAAAAAQEfQEIPAAAAAAAWABTQxKPvCemXtumeOX5Rj+PkGhGMoQEDBAEAAAAiBgLnqyU3tdSelwMJquBunknzbOHJ/rvUTsjg0cygtPnDGRhzxdoKVAAAgAEAAIAAAACAAAAAAAAAAAAAIgIDXUnszVTQCZ5DZ2J3x6bUYl1hHaiKXfSb+VF6d5Gnd6UYc8XaClQAAIABAACAAAAAgAEAAAAAAAAAAAAiAgPu7SBaaQIv7UpioCRX82mbGcBr90v4AazG2a6EvBap4RhzxdoKVAAAgAEAAIAAAACAAAAAAAEAAAAA"""

BASE64_MULTISIG_PSBT = """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"""
mnemonic_12b = ["abandon"] * 11 + ["about"]
seed_12b = Seed(mnemonic=mnemonic_12b, wordlist_language_code=SettingsConstants.WORDLIST_LANGUAGE__ENGLISH)

def add_op_return_to_psbt(psbt: PSBT, raw_payload_data: bytes):
    data = (compact.to_bytes(OPCODES.OP_RETURN) + 
        compact.to_bytes(OPCODES.OP_PUSHDATA1) + 
        compact.to_bytes(len(raw_payload_data)) +
        raw_payload_data)
    script = Script(data)
    output = OutputScope()
    output.script_pubkey = script
    output.value = 0
    psbt.outputs.append(output)
    return psbt.to_string()

# Prep a PSBT with a human-readable OP_RETURN
raw_payload_data = "Chancellor on the brink of third bailout for banks".encode()
psbt = PSBT.from_base64(BASE64_MULTISIG_PSBT)

# Simplify the output side
output = psbt.outputs[-1]
psbt.outputs.clear()
psbt.outputs.append(output)
assert len(psbt.outputs) == 1
BASE64_PSBT_WITH_OP_RETURN_TEXT = add_op_return_to_psbt(psbt, raw_payload_data)

# Prep a PSBT with a (repeatably) random 80-byte OP_RETURN
random.seed(6102)
BASE64_PSBT_WITH_OP_RETURN_RAW_BYTES = add_op_return_to_psbt(PSBT.from_base64(BASE64_MULTISIG_PSBT), random.randbytes(80))

mnemonic_12 = "forum undo fragile fade shy sign arrest garment culture tube off merit".split()
mnemonic_24 = "attack pizza motion avocado network gather crop fresh patrol unusual wild holiday candy pony ranch winter theme error hybrid van cereal salon goddess expire".split()
seed_12 = Seed(mnemonic=mnemonic_12, passphrase="cap*BRACKET3stove", wordlist_language_code=SettingsConstants.WORDLIST_LANGUAGE__ENGLISH)
seed_24 = Seed(mnemonic=mnemonic_24, passphrase="some-PASS*phrase9", wordlist_language_code=SettingsConstants.WORDLIST_LANGUAGE__ENGLISH)
seed_24_w_passphrase = Seed(mnemonic=mnemonic_24, passphrase="some-PASS*phrase9", wordlist_language_code=SettingsConstants.WORDLIST_LANGUAGE__ENGLISH)

MULTISIG_WALLET_DESCRIPTOR = """wsh(sortedmulti(1,[22bde1a9/48h/1h/0h/2h]tpubDFfsBrmpj226ZYiRszYi2qK6iGvh2vkkghfGB2YiRUVY4rqqedHCFEgw12FwDkm7rUoVtq9wLTKc6BN2sxswvQeQgp7m8st4FP8WtP8go76/{0,1}/*,[73c5da0a/48h/1h/0h/2h]tpubDFH9dgzveyD8zTbPUFuLrGmCydNvxehyNdUXKJAQN8x4aZ4j6UZqGfnqFrD4NqyaTVGKbvEW54tsvPTK2UoSbCC1PJY8iCNiwTL3RWZEheQ/{0,1}/*))#3jhtf6yx"""


# Wrap QRDisplayScreen's `render_brightness_tip` in a simple View + Screen so we
# can call it outside of its child thread and generate a screenshot.
class SeedExportXpubQR_ScreenBrightnessView(seed_views.SeedExportXpubQRDisplayView):
    @dataclass
    class QRDisplayScreenBrightnessTipScreen(BaseScreen):
        qr_encoder: BaseQrEncoder = None

        def _render(self):
            from seedsigner.gui.screens.screen import QRDisplayScreen
            image = self.qr_encoder.part_to_image(self.qr_encoder.cur_part(), 240, 240, border=2, background_color="white")
            QRDisplayScreen.QRDisplayThread.render_brightness_tip(None, image)
            self.renderer.show_image(image)

    def run(self):
        self.run_screen(
            SeedExportXpubQR_ScreenBrightnessView.QRDisplayScreenBrightnessTipScreen,
            qr_encoder=self.qr_encoder,  # initialized by SeedExportXpubQRDisplayView
        )



def _build_cardano_parsed_tx() -> CardanoParsedTx:
    """Build a CardanoParsedTx from the test CBOR data for screenshot generation."""
    sign_request = CardanoSignRequest(
        request_id="c4218ca2-6bc2-4f54-9559-66edf0e9a58f",
        origin="Lace",
        sign_data=bytes.fromhex("b300818258200f3abbc8fc19c2e61bab6059bf8a466e6e754833a08a62a6c56fe0e78f19d9d500018782583900350d57fd8f9f49f429449d89c893df74210ba70b9f13fc6c9736b7e31fa4a08fd7daf8f2ede99a7dd4ff3f9bd93b307f7ae16e47f071e60e1a004c4b408258390040a5da568e7941c588ce882389613c40719534a06800aae92745c14a1fa4a08fd7daf8f2ede99a7dd4ff3f9bd93b307f7ae16e47f071e60e821a00989680a5581c2a286ad895d091f2b3d168a6091ad2627d30a72761a5bc36eef00740a1401864581c3a286ad895d091f2b3d168a6091ad2627d30a72761a5bc36eef00741a14018fa581c4a286ad895d091f2b3d168a6091ad2627d30a72761a5bc36eef00742a1401901f4581c5a286ad895d091f2b3d168a6091ad2627d30a72761a5bc36eef00743a1401903e8581c6a286ad895d091f2b3d168a6091ad2627d30a72761a5bc36eef00744a140184b83583900e1caeff6682bf553eecc96a3ae020b2878e7aa433259884b2eb495891fa4a08fd7daf8f2ede99a7dd4ff3f9bd93b307f7ae16e47f071e60e821a003567e0a1581c7a286ad895d091f2b3d168a6091ad2627d30a72761a5bc36eef00745a14019012c5820abcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcda300583900a158650cba5554cb499dcef3bf8b01bf6396e1845e3b3052eae534951fa4a08fd7daf8f2ede99a7dd4ff3f9bd93b307f7ae16e47f071e60e01821a006acfc0a2581c8a286ad895d091f2b3d168a6091ad2627d30a72761a5bc36eef00746a1401896581c9a286ad895d091f2b3d168a6091ad2627d30a72761a5bc36eef00747a14018c8028201d81857d8799f182a4b48656c6c6f20576f726c649f010203ffffa300583900606b741406e74ac6ff6acba2eb47a7d72789282744223b977a16e5581fa4a08fd7daf8f2ede99a7dd4ff3f9bd93b307f7ae16e47f071e60e01821a003d0900a1581caa286ad895d091f2b3d168a6091ad2627d30a72761a5bc36eef00748a140185003d818582c82008201828200581c6199186adb51974690d7247d2646097d2c62763b767b528816fb7ed382041a02aea540a300583900350d57fd8f9f49f429449d89c893df74210ba70b9f13fc6c9736b7e31fa4a08fd7daf8f2ede99a7dd4ff3f9bd93b307f7ae16e47f071e60e01821a005b8d80a3581cba286ad895d091f2b3d168a6091ad2627d30a72761a5bc36eef00749a1401878581cca286ad895d091f2b3d168a6091ad2627d30a72761a5bc36eef0074aa140185a581cda286ad895d091f2b3d168a6091ad2627d30a72761a5bc36eef0074ba140183c03d81857820254590a0e590a0b01000032323232323232323232328358390040a5da568e7941c588ce882389613c40719534a06800aae92745c14a1fa4a08fd7daf8f2ede99a7dd4ff3f9bd93b307f7ae16e47f071e60e821a00e4e1c0a8581c0b286ad895d091f2b3d168a6091ad2627d30a72761a5bc36eef0074ea140190bb8581c1b286ad895d091f2b3d168a6091ad2627d30a72761a5bc36eef0074fa140190fa0581c2b286ad895d091f2b3d168a6091ad2627d30a72761a5bc36eef00750a140191388581c3b286ad895d091f2b3d168a6091ad2627d30a72761a5bc36eef00751a1401901f4581c4b286ad895d091f2b3d168a6091ad2627d30a72761a5bc36eef00752a1401902ee581c5b286ad895d091f2b3d168a6091ad2627d30a72761a5bc36eef00753a14018fa581cea286ad895d091f2b3d168a6091ad2627d30a72761a5bc36eef0074ca1401903e8581cfa286ad895d091f2b3d168a6091ad2627d30a72761a5bc36eef0074da1401907d05820fedcbafedcbafedcbafedcbafedcbafedcbafedcbafedcbafedcbafedcbafede021a0007a120031a02faf080049483078200581c3542acb3a64d80c29302260d62c3b87a742ad14abf855ebc6733081e1a001e848083088200581c3542acb3a64d80c29302260d62c3b87a742ad14abf855ebc6733081e1a001e848083028200581c3542acb3a64d80c29302260d62c3b87a742ad14abf855ebc6733081e581c0f292fcaa02b8b2f9b3c8f9fd8e0bb21abedb692a6d5058df3ef273583098200581c3542acb3a64d80c29302260d62c3b87a742ad14abf855ebc6733081e8200581c4542acb3a64d80c29302260d62c3b87a742ad14abf855ebc6733081f840a8200581c3542acb3a64d80c29302260d62c3b87a742ad14abf855ebc6733081e581c0f292fcaa02b8b2f9b3c8f9fd8e0bb21abedb692a6d5058df3ef27358200581c4542acb3a64d80c29302260d62c3b87a742ad14abf855ebc6733081f830e8200581c3542acb3a64d80c29302260d62c3b87a742ad14abf855ebc6733081e8200581c4542acb3a64d80c29302260d62c3b87a742ad14abf855ebc6733081f830f8200581c3542acb3a64d80c29302260d62c3b87a742ad14abf855ebc6733081e82782468747470733a2f2f6578616d706c652e636f6d2f72657369676e6174696f6e2e6a736f6e5820000000000000000000000000000000000000000000000000000000000000000084108200581c4542acb3a64d80c29302260d62c3b87a742ad14abf855ebc6733081f1a1dcd650082781d68747470733a2f2f6578616d706c652e636f6d2f647265702e6a736f6e5820111111111111111111111111111111111111111111111111111111111111111183118200581c4542acb3a64d80c29302260d62c3b87a742ad14abf855ebc6733081f1a1dcd650083128200581c4542acb3a64d80c29302260d62c3b87a742ad14abf855ebc6733081f82782568747470733a2f2f6578616d706c652e636f6d2f647265702d757064617465642e6a736f6e58202222222222222222222222222222222222222222222222222222222222222222840b8200581c3542acb3a64d80c29302260d62c3b87a742ad14abf855ebc6733081e581c0f292fcaa02b8b2f9b3c8f9fd8e0bb21abedb692a6d5058df3ef27351a001e8480840c8200581c3542acb3a64d80c29302260d62c3b87a742ad14abf855ebc6733081e8200581c4542acb3a64d80c29302260d62c3b87a742ad14abf855ebc6733081f1a001e8480850d8200581c3542acb3a64d80c29302260d62c3b87a742ad14abf855ebc6733081e581c0f292fcaa02b8b2f9b3c8f9fd8e0bb21abedb692a6d5058df3ef27358200581c4542acb3a64d80c29302260d62c3b87a742ad14abf855ebc6733081f1a001e848082008200581c3542acb3a64d80c29302260d62c3b87a742ad14abf855ebc6733081e82018200581c3542acb3a64d80c29302260d62c3b87a742ad14abf855ebc6733081e8a03581c0f292fcaa02b8b2f9b3c8f9fd8e0bb21abedb692a6d5058df3ef273558208dd154228946bd12967c12bedb1cb6038b78f8b84a1760b1a788fa72a4af3db01b000000174876e8001a1443fd00d81e82031864581de01fa4a08fd7daf8f2ede99a7dd4ff3f9bd93b307f7ae16e47f071e60e81581c1fa4a08fd7daf8f2ede99a7dd4ff3f9bd93b307f7ae16e47f071e60e818400190bb944c0a80101f682782668747470733a2f2f6578616d706c652e636f6d2f706f6f6c2d6d657461646174612e6a736f6e582033333333333333333333333333333333333333333333333333333333333333338a03581c0f292fcaa02b8b2f9b3c8f9fd8e0bb21abedb692a6d5058df3ef273558209dd154228946bd12967c12bedb1cb6038b78f8b84a1760b1a788fa72a4af3db11b0000000ba43b74001a1443fd00d81e82051864581de01fa4a08fd7daf8f2ede99a7dd4ff3f9bd93b307f7ae16e47f071e60e81581c1fa4a08fd7daf8f2ede99a7dd4ff3f9bd93b307f7ae16e47f071e60e818400190bbaf65020010db885a3000000008a2e0370733482782768747470733a2f2f6578616d706c652e636f6d2f706f6f6c322d6d657461646174612e6a736f6e582066666666666666666666666666666666666666666666666666666666666666668a03581c0f292fcaa02b8b2f9b3c8f9fd8e0bb21abedb692a6d5058df3ef27355820add154228946bd12967c12bedb1cb6038b78f8b84a1760b1a788fa72a4af3db21b0000001176592e001a1443fd00d81e82041864581de01fa4a08fd7daf8f2ede99a7dd4ff3f9bd93b307f7ae16e47f071e60e81581c1fa4a08fd7daf8f2ede99a7dd4ff3f9bd93b307f7ae16e47f071e60e818301190bbb7272656c6179312e6578616d706c652e636f6d82782768747470733a2f2f6578616d706c652e636f6d2f706f6f6c332d6d657461646174612e6a736f6e582077777777777777777777777777777777777777777777777777777777777777778a03581c0f292fcaa02b8b2f9b3c8f9fd8e0bb21abedb692a6d5058df3ef27355820bdd154228946bd12967c12bedb1cb6038b78f8b84a1760b1a788fa72a4af3db31b0000001bf08eb0001a1443fd00d81e82021864581de01fa4a08fd7daf8f2ede99a7dd4ff3f9bd93b307f7ae16e47f071e60e81581c1fa4a08fd7daf8f2ede99a7dd4ff3f9bd93b307f7ae16e47f071e60e8182027772656c6179732e706f6f6c2e6578616d706c652e636f6d82782768747470733a2f2f6578616d706c652e636f6d2f706f6f6c342d6d657461646174612e6a736f6e582088888888888888888888888888888888888888888888888888888888888888888304581c0f292fcaa02b8b2f9b3c8f9fd8e0bb21abedb692a6d5058df3ef27351901f405a1581de01fa4a08fd7daf8f2ede99a7dd4ff3f9bd93b307f7ae16e47f071e60e1a000f42400758201010101010101010101010101010101010101010101010101010101010101010081a02aea54009af581c0b286ad895d091f2b3d168a6091ad2627d30a72761a5bc36eef0074ea140197530581c2a286ad895d091f2b3d168a6091ad2627d30a72761a5bc36eef00740a1401903e8581c3a286ad895d091f2b3d168a6091ad2627d30a72761a5bc36eef00741a1401909c4581c4a286ad895d091f2b3d168a6091ad2627d30a72761a5bc36eef00742a1401901f4581c5a286ad895d091f2b3d168a6091ad2627d30a72761a5bc36eef00743a140192710581c6a286ad895d091f2b3d168a6091ad2627d30a72761a5bc36eef00744a1401902ee581c7a286ad895d091f2b3d168a6091ad2627d30a72761a5bc36eef00745a140190bb8581c8a286ad895d091f2b3d168a6091ad2627d30a72761a5bc36eef00746a1401905dc581c9a286ad895d091f2b3d168a6091ad2627d30a72761a5bc36eef00747a1401907d0581caa286ad895d091f2b3d168a6091ad2627d30a72761a5bc36eef00748a1403863581cba286ad895d091f2b3d168a6091ad2627d30a72761a5bc36eef00749a14038f9581cca286ad895d091f2b3d168a6091ad2627d30a72761a5bc36eef0074aa1403831581cda286ad895d091f2b3d168a6091ad2627d30a72761a5bc36eef0074ba140190258581cea286ad895d091f2b3d168a6091ad2627d30a72761a5bc36eef0074ca140192710581cfa286ad895d091f2b3d168a6091ad2627d30a72761a5bc36eef0074da140194e200b5820ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff0d818258202f3abbc8fc19c2e61bab6059bf8a466e6e754833a08a62a6c56fe0e78f19d9d7000e81581c6199186adb51974690d7247d2646097d2c62763b767b528816fb7ed31083583900a158650cba5554cb499dcef3bf8b01bf6396e1845e3b3052eae534951fa4a08fd7daf8f2ede99a7dd4ff3f9bd93b307f7ae16e47f071e60e821a007a1200a5581c1b286ad895d091f2b3d168a6091ad2627d30a72761a5bc36eef0074fa140190190581c2b286ad895d091f2b3d168a6091ad2627d30a72761a5bc36eef00750a140190226581c3b286ad895d091f2b3d168a6091ad2627d30a72761a5bc36eef00751a140190258581c4b286ad895d091f2b3d168a6091ad2627d30a72761a5bc36eef00752a1401902ee581c5b286ad895d091f2b3d168a6091ad2627d30a72761a5bc36eef00753a14018fa5820c0ffeebadc0ffeebadc0ffeebadc0ffeebadc0ffeebadc0ffeebadc0ffeebade111a004c4b4012818258203f3abbc8fc19c2e61bab6059bf8a466e6e754833a08a62a6c56fe0e78f19d9d80013a38200581c12345678901234567890123456789012345678901234567890abcdefa1825820dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd00820182782168747470733a2f2f6578616d706c652e636f6d2f766f74652d7965732e6a736f6e5820eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee8202581c23456789012345678901234567890123456789012345678901234567a1825820dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd008200f68204581c34567890123456789012345678901234567890123456789012345678a1825820dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd008202f61487841b00000002540be400581de01fa4a08fd7daf8f2ede99a7dd4ff3f9bd93b307f7ae16e47f071e60e8400825820444444444444444444444444444444444444444444444444444444444444444400a100182c581c5555555555555555555555555555555555555555555555555555555582781e68747470733a2f2f6578616d706c652e636f6d2f706172616d2e6a736f6e58203333333333333333333333333333333333333333333333333333333333333333841b00000002540be400581de01fa4a08fd7daf8f2ede99a7dd4ff3f9bd93b307f7ae16e47f071e60e8301f6820a0082782168747470733a2f2f6578616d706c652e636f6d2f68617264666f726b2e6a736f6e58206666666666666666666666666666666666666666666666666666666666666666841b00000002540be400581de01fa4a08fd7daf8f2ede99a7dd4ff3f9bd93b307f7ae16e47f071e60e8302a1581de01fa4a08fd7daf8f2ede99a7dd4ff3f9bd93b307f7ae16e47f071e60e1b000000174876e800f682782168747470733a2f2f6578616d706c652e636f6d2f74726561737572792e6a736f6e58207777777777777777777777777777777777777777777777777777777777777777841b00000002540be400581de01fa4a08fd7daf8f2ede99a7dd4ff3f9bd93b307f7ae16e47f071e60e8203f682781f68747470733a2f2f6578616d706c652e636f6d2f6e6f636f6e662e6a736f6e58208888888888888888888888888888888888888888888888888888888888888888841b00000002540be400581de01fa4a08fd7daf8f2ede99a7dd4ff3f9bd93b307f7ae16e47f071e60e8504f6828200581c3542acb3a64d80c29302260d62c3b87a742ad14abf855ebc6733081e8200581c6542acb3a64d80c29302260d62c3b87a742ad14abf855ebc6733081aa38200581c4542acb3a64d80c29302260d62c3b87a742ad14abf855ebc6733081f1901f48200581c7542acb3a64d80c29302260d62c3b87a742ad14abf855ebc6733081b1901f98201581c8542acb3a64d80c29302260d62c3b87a742ad14abf855ebc6733081c1901fed81e82020382782268747470733a2f2f6578616d706c652e636f6d2f636f6d6d69747465652e6a736f6e58209999999999999999999999999999999999999999999999999999999999999999841b00000002540be400581de01fa4a08fd7daf8f2ede99a7dd4ff3f9bd93b307f7ae16e47f071e60e8305f68282781e68747470733a2f2f6578616d706c652e636f6d2f636f6e73742e6a736f6e5820bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbf682782568747470733a2f2f6578616d706c652e636f6d2f636f6e737469747574696f6e2e6a736f6e5820aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa841b00000002540be400581de01fa4a08fd7daf8f2ede99a7dd4ff3f9bd93b307f7ae16e47f071e60e810682781d68747470733a2f2f6578616d706c652e636f6d2f696e666f2e6a736f6e5820cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc151a05f5e100161a000f4240"),
        inputs=[
            SigningInput(
                tx_hash=bytes.fromhex("0f3abbc8fc19c2e61bab6059bf8a466e6e754833a08a62a6c56fe0e78f19d9d5"),
                index=0,
                xfp=bytes.fromhex("b2743478"),
                path=[2147485500, 2147485463, 2147483648, 0, 0],
            ),
        ],
        change_outputs=[
            ChangeOutput(
                index=2,
                path=[2147485500, 2147485463, 2147483648, 0, 2],
            ),
        ],
        extra_signers=[],
    )
    # For screenshots, use a simple verified_change_indices without actual key derivation
    # Index 2 is the intended change output in the test data
    return CardanoParsedTx(sign_request, verified_change_indices=[2])


def _build_cardano_screenshot_configs():
    """Build screenshot configs for Cardano TX views using real parsed data."""
    parsed_tx = _build_cardano_parsed_tx()
    # Global indices for the test TX (7 outputs, fee@7, ttl@8, 20 certs@9-28,
    # withdrawal@29, aux_hash@30, validity@31, 15 mints@32-46, script_hash@47,
    # collateral@48, req_signer@49, coll_return@50, total_coll@51, ref_input@52,
    # 3 votes@53-55, 7 proposals@56-62, treasury@63, donation@64)
    seq = cardano_tx_views.CardanoTxSequentialReviewView
    return [
        ScreenshotConfig(cardano_tx_views.CardanoTxOverviewView, dict(parsed_tx=parsed_tx)),
        ScreenshotConfig(cardano_tx_views.CardanoTxSummaryView, dict(parsed_tx=parsed_tx)),
        ScreenshotConfig(cardano_tx_views.CardanoTxSignView, dict(parsed_tx=parsed_tx)),
        # Sequential review — sample pages from different sections
        ScreenshotConfig(seq, dict(parsed_tx=parsed_tx, global_index=0), screenshot_name="SeqReview_output_first"),
        ScreenshotConfig(seq, dict(parsed_tx=parsed_tx, global_index=1), screenshot_name="SeqReview_output_with_tokens"),
        ScreenshotConfig(seq, dict(parsed_tx=parsed_tx, global_index=7), screenshot_name="SeqReview_fee"),
        ScreenshotConfig(seq, dict(parsed_tx=parsed_tx, global_index=8), screenshot_name="SeqReview_ttl"),
        ScreenshotConfig(seq, dict(parsed_tx=parsed_tx, global_index=9), screenshot_name="SeqReview_certificate"),
        ScreenshotConfig(seq, dict(parsed_tx=parsed_tx, global_index=29), screenshot_name="SeqReview_withdrawal"),
        ScreenshotConfig(seq, dict(parsed_tx=parsed_tx, global_index=32), screenshot_name="SeqReview_mint"),
        ScreenshotConfig(seq, dict(parsed_tx=parsed_tx, global_index=48), screenshot_name="SeqReview_collateral"),
        ScreenshotConfig(seq, dict(parsed_tx=parsed_tx, global_index=53), screenshot_name="SeqReview_voting"),
        ScreenshotConfig(seq, dict(parsed_tx=parsed_tx, global_index=56), screenshot_name="SeqReview_proposal"),
        ScreenshotConfig(seq, dict(parsed_tx=parsed_tx, global_index=52), screenshot_name="SeqReview_ref_input"),
    ]


def generate_screenshots(locale):
    """
        The `Renderer` class is mocked so that calls in the normal code are ignored
        (necessary to avoid having it trying to wire up hardware dependencies).

        When the `Renderer` instance is needed, we patch in our own test-only
        `ScreenshotRenderer`.
    """
    # Prep the ScreenshotRenderer that will be patched over the normal Renderer
    screenshot_root = os.path.join(os.getcwd(), "seedsigner-screenshots")
    ScreenshotRenderer.configure_instance()
    screenshot_renderer: ScreenshotRenderer = ScreenshotRenderer.get_instance()

    # Replace the core `Singleton` calls so that only our ScreenshotRenderer is used.
    Renderer.configure_instance = Mock()
    Renderer.get_instance = Mock(return_value=screenshot_renderer)


    def setup_screenshots(locale: str) -> dict[str, list[ScreenshotConfig]]:
        """ Set up some test data that we'll need in the `Controller` for certain Views """
        # Must reset the Controller so each locale gets a fresh start
        Controller.reset_instance()
        controller = Controller.get_instance()

        controller.settings.set_value(SettingsConstants.SETTING__SIG_TYPES, [attr for attr, name in SettingsConstants.ALL_SIG_TYPES])
        controller.settings.set_value(SettingsConstants.SETTING__SCRIPT_TYPES, [attr for attr, name in SettingsConstants.ALL_SCRIPT_TYPES])

        controller.storage.seeds.append(seed_12)
        controller.storage.seeds.append(seed_12b)
        controller.storage.seeds.append(seed_24)
        controller.storage.set_pending_seed(seed_24_w_passphrase)

        # Pending mnemonic for ToolsCalcFinalWordShowFinalWordView
        controller.storage.init_pending_mnemonic(num_words=12)
        for i, word in enumerate(mnemonic_12[:11]):
            controller.storage.update_pending_mnemonic(word=word, index=i)
        controller.storage.update_pending_mnemonic(word="satoshi", index=11)  # random last word; not supposed to be a valid checksum (yet)

        # Load a PSBT into memory
        decoder = DecodeQR()
        decoder.add_data(BASE64_MULTISIG_PSBT)
        controller.psbt = decoder.get_psbt()
        controller.psbt_seed = seed_12b

        # Message signing data
        derivation_path = "m/84h/0h/0h/0/0"
        controller.sign_message_data = {
            "seed_num": 0,
            "derivation_path": derivation_path,
            "message": "I attest that I control this bitcoin address blah blah blah",
            "addr_format": embit_utils.parse_derivation_path(derivation_path)
        }

        # so we get a choice for transcribe seed qr format
        controller.settings.set_value(
            attr_name=SettingsConstants.SETTING__COMPACT_SEEDQR,
            value=SettingsConstants.OPTION__ENABLED
        )

        # Automatically populate all Settings options Views
        settings_views_list = []
        def add_settings_entries(visibility = SettingsConstants.VISIBILITY__GENERAL):
            for settings_entry in SettingsDefinition.settings_entries:
                if settings_entry.visibility != visibility:
                    continue

                if settings_entry.attr_name == SettingsConstants.SETTING__LOCALE:
                    # Locale selection has its own dedicated View
                    settings_views_list.append(ScreenshotConfig(settings_views.LocaleSelectionView))
                else:
                    # Generic SettingsEntry selection View
                    settings_views_list.append(ScreenshotConfig(settings_views.SettingsEntryUpdateSelectionView, dict(attr_name=settings_entry.attr_name), screenshot_name=f"SettingsEntryUpdateSelectionView_{settings_entry.attr_name}"))

        # Add the top level "General" settings menu and entries
        settings_views_list.append(ScreenshotConfig(settings_views.SettingsMenuView))
        add_settings_entries(SettingsConstants.VISIBILITY__GENERAL)

        # Add the "Advanced" menu...
        settings_views_list.append(
            ScreenshotConfig(
                settings_views.SettingsMenuView,
                dict(
                    visibility=SettingsConstants.VISIBILITY__ADVANCED,
                ),
                screenshot_name="SettingsMenuView__Advanced"
            )
        )

        # ...and Advanced entries
        add_settings_entries(SettingsConstants.VISIBILITY__ADVANCED)

        # Render the nested "Advanced" -> "Hardware" submenu
        settings_views_list.append(
            ScreenshotConfig(
                settings_views.SettingsMenuView,
                dict(visibility=SettingsConstants.VISIBILITY__HARDWARE),
                screenshot_name="SettingsMenuView__Hardware"
            )
        )
        add_settings_entries(SettingsConstants.VISIBILITY__HARDWARE)

        settingsqr_data_persistent = f"settings::v1 name=English_noob_mode persistent=E coords=spa,spd denom=thr network=M qr_density=M xpub_export=E sigs=ss scripts=nat xpub_details=E passphrase=E camera=0 compact_seedqr=E bip85=D priv_warn=E dire_warn=E partners=E locale={locale}"
        settingsqr_data_not_persistent = f"settings::v1 name=Mode_Ephemeral persistent=D coords=spa,spd denom=thr network=M qr_density=M xpub_export=E sigs=ss scripts=nat xpub_details=E passphrase=E camera=0 compact_seedqr=E bip85=D priv_warn=E dire_warn=E partners=E locale={locale}"

        # Set up screenshot-specific callbacks to inject data before the View is run and
        # reset data after the View is run.
        def load_single_sig_psbt_cb():
            decoder = DecodeQR()
            decoder.add_data(BASE64_SINGLE_SIG_PSBT)
            controller.psbt = decoder.get_psbt()
            controller.psbt_seed = seed_12b
            controller.psbt_parser = PSBTParser(p=controller.psbt, seed=seed_12b)
            controller.multisig_wallet_descriptor = None


        def load_multisig_psbt_cb():
            decoder = DecodeQR()
            decoder.add_data(BASE64_MULTISIG_PSBT)
            controller.psbt = decoder.get_psbt()
            controller.psbt_seed = seed_12b
            controller.psbt_parser = PSBTParser(p=controller.psbt, seed=seed_12b)
            controller.multisig_wallet_descriptor = None


        def load_multisig_wallet_descriptor_cb():
            controller.multisig_wallet_descriptor = embit.descriptor.Descriptor.from_string(MULTISIG_WALLET_DESCRIPTOR)


        def load_address_verification_data_cb():
            controller.unverified_address = dict(
                # These are all totally fake data
                address="bc1q6p00wazu4nnqac29fvky6vhjnnhku5u2g9njss62rvy7e0yuperq86f5ek",
                network=SettingsConstants.MAINNET,
                sig_type=SettingsConstants.SINGLE_SIG,
                script_type=SettingsConstants.NATIVE_SEGWIT,
                derivation_path = "m/84h/0h/0h",
                verified_index=5,
                verified_index_is_change=False
            )


        def PSBTSelectSeedView_cb_before():
            # Have to ensure this is cleared out in order to get the seed selection screen
            controller.psbt_seed = None


        def PSBTOverviewView_op_return_cb_before():
            controller.psbt_seed = seed_12b
            decoder = DecodeQR()
            decoder.add_data(BASE64_PSBT_WITH_OP_RETURN_TEXT)
            controller.psbt = decoder.get_psbt()
            controller.psbt_parser = PSBTParser(p=controller.psbt, seed=seed_12b)
        

        def PSBTOpReturnView_raw_hex_data_cb_before():
            decoder.add_data(BASE64_PSBT_WITH_OP_RETURN_RAW_BYTES)
            controller.psbt = decoder.get_psbt()
            controller.psbt_parser = PSBTParser(p=controller.psbt, seed=seed_12b)


        screenshot_sections = {
            "Main Menu Views": [
                ScreenshotConfig(OpeningSplashView, dict(force_partner_logos=True)),
                ScreenshotConfig(OpeningSplashView, dict(force_partner_logos=False), screenshot_name="OpeningSplashView_no_partner_logos"),
                ScreenshotConfig(MainMenuView),
                ScreenshotConfig(MainMenuView, screenshot_name='MainMenuView_SDCardStateChangeToast_removed',  toast_thread=SDCardStateChangeToastManagerThread(action=MicroSD.ACTION__REMOVED, activation_delay=0, duration=0)),
                ScreenshotConfig(MainMenuView, screenshot_name='MainMenuView_SDCardStateChangeToast_inserted', toast_thread=SDCardStateChangeToastManagerThread(action=MicroSD.ACTION__INSERTED, activation_delay=0, duration=0)),
                ScreenshotConfig(MainMenuView, screenshot_name='MainMenuView_RemoveSDCardToast',               toast_thread=RemoveSDCardToastManagerThread(activation_delay=0, duration=0)),
                ScreenshotConfig(RemoveMicroSDWarningView),
                ScreenshotConfig(MainMenuView, screenshot_name='MainMenuView_DefaultToast',                    toast_thread=DefaultToast("This is a default text toast!", activation_delay=0, duration=0)),
                ScreenshotConfig(MainMenuView, screenshot_name='MainMenuView_InfoToast',                       toast_thread=InfoToast("This is an info toast!", activation_delay=0, duration=0)),
                ScreenshotConfig(MainMenuView, screenshot_name='MainMenuView_SuccessToast',                    toast_thread=SuccessToast("This is a success toast!", activation_delay=0, duration=0)),
                ScreenshotConfig(MainMenuView, screenshot_name='MainMenuView_WarningToast',                    toast_thread=WarningToast("This is a warning toast!", activation_delay=0, duration=0)),
                ScreenshotConfig(MainMenuView, screenshot_name='MainMenuView_DireWarningToast',                toast_thread=DireWarningToast("This is a dire warning toast!", activation_delay=0, duration=0)),
                ScreenshotConfig(MainMenuView, screenshot_name='MainMenuView_ErrorToast',                      toast_thread=ErrorToast("This is an error toast!", activation_delay=0, duration=0)),
                ScreenshotConfig(PowerOptionsView),
                ScreenshotConfig(RestartView),
                ScreenshotConfig(PowerOffView),
            ],
            "Seed Views": [
                ScreenshotConfig(seed_views.SeedsMenuView),
                ScreenshotConfig(seed_views.LoadSeedView),
                ScreenshotConfig(seed_views.SeedMnemonicEntryView),
                ScreenshotConfig(seed_views.SeedMnemonicInvalidView),
                ScreenshotConfig(seed_views.SeedFinalizeView),
                ScreenshotConfig(seed_views.SeedAddPassphraseView, screenshot_name="SeedAddPassphraseView_lowercase"),
                ScreenshotConfig(seed_views.SeedAddPassphraseView, dict(initial_keyboard=SeedAddPassphraseScreen.KEYBOARD__UPPERCASE_BUTTON_TEXT), screenshot_name="SeedAddPassphraseView_uppercase"),
                ScreenshotConfig(seed_views.SeedAddPassphraseView, dict(initial_keyboard=SeedAddPassphraseScreen.KEYBOARD__DIGITS_BUTTON_TEXT),    screenshot_name="SeedAddPassphraseView_digits"),
                ScreenshotConfig(seed_views.SeedAddPassphraseView, dict(initial_keyboard=SeedAddPassphraseScreen.KEYBOARD__SYMBOLS_1_BUTTON_TEXT), screenshot_name="SeedAddPassphraseView_symbols_1"),
                ScreenshotConfig(seed_views.SeedAddPassphraseView, dict(initial_keyboard=SeedAddPassphraseScreen.KEYBOARD__SYMBOLS_2_BUTTON_TEXT), screenshot_name="SeedAddPassphraseView_symbols_2"),
                ScreenshotConfig(seed_views.SeedAddPassphraseExitDialogView),
                ScreenshotConfig(seed_views.SeedReviewPassphraseView),
                
                ScreenshotConfig(seed_views.SeedOptionsView, dict(seed_num=0)),
                ScreenshotConfig(seed_views.SeedBackupView, dict(seed_num=0)),
                ScreenshotConfig(seed_views.SeedExportXpubSigTypeView, dict(seed_num=0)),
                ScreenshotConfig(seed_views.SeedExportXpubScriptTypeView, dict(seed_num=0, sig_type="msig")),
                ScreenshotConfig(seed_views.SeedExportXpubCustomDerivationView, dict(seed_num=0, sig_type="ss", script_type="")),
                ScreenshotConfig(seed_views.SeedExportXpubCoordinatorView, dict(seed_num=0, sig_type="ss", script_type="nat")),
                ScreenshotConfig(seed_views.SeedExportXpubWarningView, dict(seed_num=0, sig_type="msig", script_type="nes", coordinator="spd", custom_derivation="")),
                ScreenshotConfig(seed_views.SeedExportXpubDetailsView, dict(seed_num=0, sig_type="ss", script_type="nat", coordinator="bw", custom_derivation="")),
                ScreenshotConfig(SeedExportXpubQR_ScreenBrightnessView, dict(seed_num=0, coordinator="bw", derivation_path="m/84'/0'/0'")),

                ScreenshotConfig(seed_views.SeedWordsWarningView, dict(seed_num=0)),
                ScreenshotConfig(seed_views.SeedWordsView, dict(seed_num=0)),
                ScreenshotConfig(seed_views.SeedWordsView, dict(seed_num=0, page_index=2), screenshot_name="SeedWordsView_2"),
                ScreenshotConfig(seed_views.SeedBIP85SelectNumWordsView, dict(seed_num=0)),
                ScreenshotConfig(seed_views.SeedBIP85SelectChildIndexView, dict(seed_num=0, num_words=24)),
                ScreenshotConfig(seed_views.SeedBIP85InvalidChildIndexView, dict(seed_num=0, num_words=12)), 
                ScreenshotConfig(seed_views.SeedWordsBackupTestPromptView, dict(seed_num=0)),
                ScreenshotConfig(seed_views.SeedWordsBackupTestView, dict(seed_num=0, rand_seed=6102)),
                ScreenshotConfig(seed_views.SeedWordsBackupTestMistakeView, dict(seed_num=0, cur_index=7, wrong_word="satoshi")),
                ScreenshotConfig(seed_views.SeedWordsBackupTestSuccessView, dict(seed_num=0)),
                ScreenshotConfig(seed_views.SeedTranscribeSeedQRFormatView, dict(seed_num=0)),
                ScreenshotConfig(seed_views.SeedTranscribeSeedQRWarningView, dict(seed_num=0)),
                ScreenshotConfig(seed_views.SeedTranscribeSeedQRWholeQRView, dict(seed_num=0, seedqr_format=QRType.SEED__COMPACTSEEDQR, num_modules=21), screenshot_name="SeedTranscribeSeedQRWholeQRView_12_Compact"),
                ScreenshotConfig(seed_views.SeedTranscribeSeedQRWholeQRView, dict(seed_num=0, seedqr_format=QRType.SEED__SEEDQR, num_modules=25),        screenshot_name="SeedTranscribeSeedQRWholeQRView_12_Standard"),
                ScreenshotConfig(seed_views.SeedTranscribeSeedQRWholeQRView, dict(seed_num=2, seedqr_format=QRType.SEED__COMPACTSEEDQR, num_modules=25), screenshot_name="SeedTranscribeSeedQRWholeQRView_24_Compact"),
                ScreenshotConfig(seed_views.SeedTranscribeSeedQRWholeQRView, dict(seed_num=2, seedqr_format=QRType.SEED__SEEDQR, num_modules=29),        screenshot_name="SeedTranscribeSeedQRWholeQRView_24_Standard"),
                ScreenshotConfig(seed_views.SeedTranscribeSeedQRZoomedInView, dict(seed_num=0, seedqr_format=QRType.SEED__COMPACTSEEDQR, initial_zone_x=1, initial_zone_y=1), screenshot_name="SeedTranscribeSeedQRZoomedInView_12_Compact"),
                ScreenshotConfig(seed_views.SeedTranscribeSeedQRZoomedInView, dict(seed_num=0, seedqr_format=QRType.SEED__SEEDQR, initial_zone_x=2, initial_zone_y=2),        screenshot_name="SeedTranscribeSeedQRZoomedInView_12_Standard"),

                ScreenshotConfig(seed_views.SeedTranscribeSeedQRConfirmQRPromptView, dict(seed_num=0)),
                ScreenshotConfig(seed_views.SeedTranscribeSeedQRConfirmWrongSeedView),
                ScreenshotConfig(seed_views.SeedTranscribeSeedQRConfirmInvalidQRView),
                ScreenshotConfig(seed_views.SeedTranscribeSeedQRConfirmSuccessView, dict(seed_num=0)),

                # Screenshot can't render live preview screens
                # ScreenshotConfig(seed_views.SeedTranscribeSeedQRConfirmScanView, dict(seed_num=0)),

                ScreenshotConfig(seed_views.SeedSelectSeedView, dict(flow=Controller.FLOW__VERIFY_SINGLESIG_ADDR), screenshot_name="SeedSelectSeedView_address_verification"),
                ScreenshotConfig(seed_views.AddressVerificationSigTypeView),
                ScreenshotConfig(seed_views.SeedAddressVerificationView, dict(seed_num=0), run_before=load_address_verification_data_cb),
                ScreenshotConfig(seed_views.SeedAddressVerificationSuccessView, dict(seed_num=0)),  # Relies on callback above

                ScreenshotConfig(seed_views.LoadMultisigWalletDescriptorView),
                ScreenshotConfig(seed_views.MultisigWalletDescriptorView, run_before=load_multisig_wallet_descriptor_cb),
                ScreenshotConfig(seed_views.SeedDiscardView, dict(seed_num=0)),

                ScreenshotConfig(seed_views.SeedSelectSeedView, dict(flow=Controller.FLOW__SIGN_MESSAGE), screenshot_name="SeedSelectSeedView_sign_message"),
                ScreenshotConfig(seed_views.SeedSignMessageConfirmMessageView),
                ScreenshotConfig(seed_views.SeedSignMessageConfirmAddressView),

                ScreenshotConfig(seed_views.SeedElectrumMnemonicStartView),
            ],
            "PSBT Views": [
                ScreenshotConfig(psbt_views.PSBTSelectSeedView, run_before=PSBTSelectSeedView_cb_before),
                ScreenshotConfig(psbt_views.PSBTOverviewView, run_before=load_multisig_psbt_cb),
                ScreenshotConfig(psbt_views.PSBTUnsupportedScriptTypeWarningView),
                ScreenshotConfig(psbt_views.PSBTNoChangeWarningView),
                ScreenshotConfig(psbt_views.PSBTMathView),
                ScreenshotConfig(psbt_views.PSBTAddressDetailsView, dict(address_num=0)),

                ScreenshotConfig(psbt_views.PSBTChangeDetailsView, dict(change_address_num=0), screenshot_name="PSBTChangeDetailsView_single_sig_change_verified", run_before=load_single_sig_psbt_cb),
                ScreenshotConfig(psbt_views.PSBTChangeDetailsView, dict(change_address_num=1), screenshot_name="PSBTChangeDetailsView_single_sig_self_transfer_verified", run_before=load_single_sig_psbt_cb),
                ScreenshotConfig(psbt_views.PSBTChangeDetailsView, dict(change_address_num=0), screenshot_name="PSBTChangeDetailsView_multisig_unverified", run_before=load_multisig_psbt_cb),
                ScreenshotConfig(psbt_views.PSBTChangeDetailsView, dict(change_address_num=0), screenshot_name="PSBTChangeDetailsView_multisig_verified", run_before=load_multisig_wallet_descriptor_cb),
                ScreenshotConfig(psbt_views.PSBTOverviewView, screenshot_name="PSBTOverviewView_op_return", run_before=PSBTOverviewView_op_return_cb_before),
                ScreenshotConfig(psbt_views.PSBTOpReturnView, screenshot_name="PSBTOpReturnView_text"),  # Relies on callback above
                ScreenshotConfig(psbt_views.PSBTOpReturnView, screenshot_name="PSBTOpReturnView_raw_hex_data", run_before=PSBTOpReturnView_raw_hex_data_cb_before),
                ScreenshotConfig(psbt_views.PSBTAddressVerificationFailedView, dict(is_change=True, is_multisig=False),  screenshot_name="PSBTAddressVerificationFailedView_singlesig_change"),
                ScreenshotConfig(psbt_views.PSBTAddressVerificationFailedView, dict(is_change=False, is_multisig=False), screenshot_name="PSBTAddressVerificationFailedView_singlesig_selftransfer"),
                ScreenshotConfig(psbt_views.PSBTAddressVerificationFailedView, dict(is_change=True, is_multisig=True),   screenshot_name="PSBTAddressVerificationFailedView_multisig_change"),
                ScreenshotConfig(psbt_views.PSBTAddressVerificationFailedView, dict(is_change=False, is_multisig=True),  screenshot_name="PSBTAddressVerificationFailedView_multisig_selftransfer"),
                ScreenshotConfig(psbt_views.PSBTFinalizeView),
                #ScreenshotConfig(PSBTSignedQRDisplayViewScreenshotConfig),
                ScreenshotConfig(psbt_views.PSBTSigningErrorView),
            ],
            "Cardano TX Views": _build_cardano_screenshot_configs(),
            "Tools Views": [
                ScreenshotConfig(tools_views.ToolsMenuView),
                #ScreenshotConfig(ToolsImageEntropyLivePreviewView),
                #ScreenshotConfig(ToolsImageEntropyFinalImageView),
                ScreenshotConfig(tools_views.ToolsImageEntropyMnemonicLengthView),
                ScreenshotConfig(tools_views.ToolsDiceEntropyMnemonicLengthView),
                ScreenshotConfig(tools_views.ToolsDiceEntropyEntryView, dict(total_rolls=50)),
                ScreenshotConfig(tools_views.ToolsCalcFinalWordNumWordsView),
                ScreenshotConfig(tools_views.ToolsCalcFinalWordFinalizePromptView),
                ScreenshotConfig(tools_views.ToolsCalcFinalWordCoinFlipsView),
                ScreenshotConfig(tools_views.ToolsCalcFinalWordShowFinalWordView, screenshot_name="ToolsCalcFinalWordShowFinalWordView_pick_word"),
                ScreenshotConfig(tools_views.ToolsCalcFinalWordShowFinalWordView, dict(coin_flips="0010101"), screenshot_name="ToolsCalcFinalWordShowFinalWordView_coin_flips"),
                ScreenshotConfig(tools_views.ToolsCalcFinalWordDoneView),
                ScreenshotConfig(tools_views.ToolsAddressExplorerSelectSourceView),
                ScreenshotConfig(tools_views.ToolsAddressExplorerAddressTypeView),
                ScreenshotConfig(tools_views.ToolsAddressExplorerAddressListView),
                # ScreenshotConfig(tools_views.ToolsAddressExplorerAddressView),
            ],
            "Settings Views": settings_views_list + [
                ScreenshotConfig(settings_views.IOTestView),
                ScreenshotConfig(settings_views.DonateView),
                ScreenshotConfig(settings_views.SettingsIngestSettingsQRView, dict(data=settingsqr_data_persistent), screenshot_name="SettingsIngestSettingsQRView_persistent"),
                ScreenshotConfig(settings_views.SettingsIngestSettingsQRView, dict(data=settingsqr_data_not_persistent), screenshot_name="SettingsIngestSettingsQRView_not_persistent"),
            ],
            "Misc Error Views": [
                ScreenshotConfig(NotYetImplementedView),
                ScreenshotConfig(UnhandledExceptionView, dict(error=["IndexError", "line 1, in some_buggy_code.py", "list index out of range"])),
                ScreenshotConfig(CameraConnectionErrorView),
                ScreenshotConfig(NetworkMismatchErrorView, dict(derivation_path="m/84'/1'/0'")),
                ScreenshotConfig(OptionDisabledView, dict(settings_attr=SettingsConstants.SETTING__MESSAGE_SIGNING)),
                ScreenshotConfig(scan_views.ScanInvalidQRTypeView)
            ]
        }

        return screenshot_sections


    def screencap_view(screenshot_config: ScreenshotConfig):
        # Block until we have exclusive access to the screenshot renderer. Without this
        # we were occasionally running into confusing race conditions where the next
        # screenshot would begin rendering over the previous one. Claiming the lock
        # guarantees that the previous screenshot has been fully rendered and saved.
        with screenshot_renderer.lock:
            screenshot_renderer.set_screenshot_filename(f"{screenshot_config.screenshot_name}.png")

        controller = Controller.get_instance()
        toast_thread = screenshot_config.toast_thread
        try:
            print(f"Running {screenshot_config.screenshot_name}")
            try:
                cur_count = screenshot_renderer.render_count

                # Set up and run the target View
                screenshot_config.run_callback_before()
                screenshot_config.View_cls(**screenshot_config.view_kwargs).run()

                if screenshot_renderer.render_count == cur_count:
                    # The View didn't actually render anything
                    raise Exception(f"{screenshot_config.screenshot_name} did not render a screenshot. Verify that its `run_screen()` is reachable by the screenshot generator.")

            except ScreenshotComplete:
                # The target View has run and its Screen has rendered what it needs to
                if toast_thread is not None:
                    # Now run the Toast so it can render on top of the current image buffer
                    controller.activate_toast(toast_thread)
                    while controller.toast_notification_thread.is_alive():
                        # Give the Toast a moment to complete its work
                        time.sleep(0.01)

                print(f"Completed {screenshot_config.screenshot_name}")

        except Exception as e:
            # Something else went wrong
            from traceback import print_exc
            print_exc()
            raise e
        finally:
            if toast_thread and toast_thread.is_alive():
                toast_thread.stop()
                toast_thread.join()

            screenshot_config.run_callback_after()


    # Parse the main `l10n/messages.pot` for overall stats
    messages_source_path = os.path.join(pathlib.Path(__file__).parent.resolve().parent.resolve().parent.resolve(), "l10n", "messages.pot")
    with open(messages_source_path, 'r') as messages_source_file:
        num_source_messages = messages_source_file.read().count("msgid \"") - 1

    locale_tuple_list = [locale_tuple for locale_tuple in SettingsConstants.get_detected_languages() if locale_tuple[0] == locale]
    if not locale_tuple_list:
        raise Exception(f"Invalid locale: {locale}")

    locale, display_name = locale_tuple_list[0]

    Settings.get_instance().set_value(SettingsConstants.SETTING__LOCALE, value=locale)

    locale_readme = f"""# SeedSigner Screenshots: {display_name}\n"""

    # Report the translation progress
    if locale != SettingsConstants.LOCALE__ENGLISH:
        try:
            translated_messages_path = os.path.join(pathlib.Path(__file__).parent.resolve().parent.resolve().parent.resolve(), "l10n", "translations", locale, "LC_MESSAGES", "messages.po") 
            with open(translated_messages_path, 'r') as translation_file:
                locale_translations = translation_file.read()
                num_locale_translations = locale_translations.count("msgid \"") - locale_translations.count("""msgstr ""\n\n""") - 1

                if locale != "en":
                    locale_readme += f"## Translation progress: {num_locale_translations / num_source_messages:.1%}\n\n"
                locale_readme += "---\n\n"
        except Exception as e:
            from traceback import print_exc
            print_exc()

    for section_name, screenshot_list in setup_screenshots(locale).items():
        subdir = section_name.lower().replace(" ", "_")
        screenshot_renderer.set_screenshot_path(os.path.join(screenshot_root, locale, subdir))
        locale_readme += "\n\n---\n\n"
        locale_readme += f"## {section_name}\n\n"
        locale_readme += """<table style="border: 0;">"""
        locale_readme += f"""<tr><td align="center">"""
        for screenshot_config in screenshot_list:
            screencap_view(screenshot_config)
            locale_readme += """  <table align="left" style="border: 1px solid gray;">"""
            locale_readme += f"""<tr><td align="center">{screenshot_config.screenshot_name}<br/><br/><img src="{subdir}/{screenshot_config.screenshot_name}.png"></td></tr>"""
            locale_readme += """</table>\n"""

        locale_readme += "</td></tr></table>"

    with open(os.path.join(screenshot_root, locale, "README.md"), 'w') as readme_file:
        readme_file.write(locale_readme)

    print(f"Done with locale: {locale}.")

    # Write the main README; ensure it writes all locales, not just the one that may
    # have been specified for this run.
    with open(os.path.join("tests", "screenshot_generator", "template.md"), 'r') as readme_template:
        main_readme = readme_template.read()

    for locale, display_name in SettingsConstants.get_detected_languages():
        main_readme += f"* [{display_name}]({locale}/README.md)\n"

    with open(os.path.join(screenshot_root, "README.md"), 'w') as readme_file:
        readme_file.write(main_readme)

    print(f"Screenshots rendered: {screenshot_renderer.render_count}")
