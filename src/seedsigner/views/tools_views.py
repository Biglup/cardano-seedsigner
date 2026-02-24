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
from seedsigner.views.seed_views import SeedDiscardView, SeedFinalizeView, SeedMnemonicEntryView, SeedOptionsView, SeedWordsWarningView, SeedExportXpubScriptTypeView

from .view import View, Destination, BackStackView

logger = logging.getLogger(__name__)



class ToolsMenuView(View):
    # Mock Cardano TX review (for development) - FIRST for easy access
    CARDANO_TX_MOCK = ButtonOption("Review Cardano TX", SeedSignerIconConstants.CHECK)
    CARDANO_MSG_MOCK = ButtonOption("Review Cardano Msg", SeedSignerIconConstants.CHECK)
    IMAGE = ButtonOption("New seed", FontAwesomeIconConstants.CAMERA)
    DICE = ButtonOption("New seed", FontAwesomeIconConstants.DICE)
    KEYBOARD = ButtonOption("Calc 12th/24th word", FontAwesomeIconConstants.KEYBOARD)
    ADDRESS_EXPLORER = ButtonOption("Address explorer")
    VERIFY_ADDRESS = ButtonOption("Verify address")

    def run(self):
        button_data = [self.CARDANO_TX_MOCK, self.CARDANO_MSG_MOCK, self.IMAGE, self.DICE, self.KEYBOARD, self.ADDRESS_EXPLORER, self.VERIFY_ADDRESS]

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

        elif button_data[selected_menu_num] == self.ADDRESS_EXPLORER:
            return Destination(ToolsAddressExplorerSelectSourceView)

        elif button_data[selected_menu_num] == self.VERIFY_ADDRESS:
            from seedsigner.views.scan_views import ScanAddressView
            return Destination(ScanAddressView)

        elif button_data[selected_menu_num] == self.CARDANO_MSG_MOCK:
            return Destination(CardanoMsgMockMenuView)

        elif button_data[selected_menu_num] == self.CARDANO_TX_MOCK:
            from seedsigner.views.tx_review import CardanoTxOverviewView
            from seedsigner.models.cardano_tx import CardanoSignRequest, CardanoParsedTx, SigningInput, ChangeOutput, ExtraSigner
            from seedsigner.helpers.cardano_utils import verify_change_outputs
            from cometa import NetworkId

            # TODO: REMOVE - preloaded test mnemonic for development only
            test_mnemonic = "device blind mail nose voice aware link achieve tattoo pulse divide tail nut taste upper fork debris helmet fatal myth genre brick champion february".split()
            test_seed = Seed(mnemonic=test_mnemonic, wordlist_language_code=SettingsConstants.WORDLIST_LANGUAGE__ENGLISH)
            self.controller.storage.set_pending_seed(test_seed)
            self.controller.storage.finalize_pending_seed()

            sign_request = CardanoSignRequest(
                request_id="c4218ca2-6bc2-4f54-9559-66edf0e9a58f",
                origin="Lace",
                sign_data=bytes.fromhex("b400818258200f3abbc8fc19c2e61bab6059bf8a466e6e754833a08a62a6c56fe0e78f19d9d500018782583900350d57fd8f9f49f429449d89c893df74210ba70b9f13fc6c9736b7e31fa4a08fd7daf8f2ede99a7dd4ff3f9bd93b307f7ae16e47f071e60e1a004c4b408258390040a5da568e7941c588ce882389613c40719534a06800aae92745c14a1fa4a08fd7daf8f2ede99a7dd4ff3f9bd93b307f7ae16e47f071e60e821a00989680a5581c2a286ad895d091f2b3d168a6091ad2627d30a72761a5bc36eef00740a1401864581c3a286ad895d091f2b3d168a6091ad2627d30a72761a5bc36eef00741a14018fa581c4a286ad895d091f2b3d168a6091ad2627d30a72761a5bc36eef00742a1401901f4581c5a286ad895d091f2b3d168a6091ad2627d30a72761a5bc36eef00743a1401903e8581c6a286ad895d091f2b3d168a6091ad2627d30a72761a5bc36eef00744a140184b83583900e1caeff6682bf553eecc96a3ae020b2878e7aa433259884b2eb495891fa4a08fd7daf8f2ede99a7dd4ff3f9bd93b307f7ae16e47f071e60e821a003567e0a1581c7a286ad895d091f2b3d168a6091ad2627d30a72761a5bc36eef00745a14019012c5820abcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcda300583900a158650cba5554cb499dcef3bf8b01bf6396e1845e3b3052eae534951fa4a08fd7daf8f2ede99a7dd4ff3f9bd93b307f7ae16e47f071e60e01821a006acfc0a2581c8a286ad895d091f2b3d168a6091ad2627d30a72761a5bc36eef00746a1401896581c9a286ad895d091f2b3d168a6091ad2627d30a72761a5bc36eef00747a14018c8028201d81857d8799f182a4b48656c6c6f20576f726c649f010203ffffa300583900606b741406e74ac6ff6acba2eb47a7d72789282744223b977a16e5581fa4a08fd7daf8f2ede99a7dd4ff3f9bd93b307f7ae16e47f071e60e01821a003d0900a1581caa286ad895d091f2b3d168a6091ad2627d30a72761a5bc36eef00748a140185003d818582c82008201828200581c6199186adb51974690d7247d2646097d2c62763b767b528816fb7ed382041a02aea540a300583900350d57fd8f9f49f429449d89c893df74210ba70b9f13fc6c9736b7e31fa4a08fd7daf8f2ede99a7dd4ff3f9bd93b307f7ae16e47f071e60e01821a005b8d80a3581cba286ad895d091f2b3d168a6091ad2627d30a72761a5bc36eef00749a1401878581cca286ad895d091f2b3d168a6091ad2627d30a72761a5bc36eef0074aa140185a581cda286ad895d091f2b3d168a6091ad2627d30a72761a5bc36eef0074ba140183c03d81857820254590a0e590a0b01000032323232323232323232328358390040a5da568e7941c588ce882389613c40719534a06800aae92745c14a1fa4a08fd7daf8f2ede99a7dd4ff3f9bd93b307f7ae16e47f071e60e821a00e4e1c0a8581c0b286ad895d091f2b3d168a6091ad2627d30a72761a5bc36eef0074ea140190bb8581c1b286ad895d091f2b3d168a6091ad2627d30a72761a5bc36eef0074fa140190fa0581c2b286ad895d091f2b3d168a6091ad2627d30a72761a5bc36eef00750a140191388581c3b286ad895d091f2b3d168a6091ad2627d30a72761a5bc36eef00751a1401901f4581c4b286ad895d091f2b3d168a6091ad2627d30a72761a5bc36eef00752a1401902ee581c5b286ad895d091f2b3d168a6091ad2627d30a72761a5bc36eef00753a14018fa581cea286ad895d091f2b3d168a6091ad2627d30a72761a5bc36eef0074ca1401903e8581cfa286ad895d091f2b3d168a6091ad2627d30a72761a5bc36eef0074da1401907d05820fedcbafedcbafedcbafedcbafedcbafedcbafedcbafedcbafedcbafedcbafede021a0007a120031a0fcec490049483078200581c3542acb3a64d80c29302260d62c3b87a742ad14abf855ebc6733081e1a001e848083088200581c3542acb3a64d80c29302260d62c3b87a742ad14abf855ebc6733081e1a001e848083028200581c3542acb3a64d80c29302260d62c3b87a742ad14abf855ebc6733081e581c0f292fcaa02b8b2f9b3c8f9fd8e0bb21abedb692a6d5058df3ef273583098200581c3542acb3a64d80c29302260d62c3b87a742ad14abf855ebc6733081e8200581c4542acb3a64d80c29302260d62c3b87a742ad14abf855ebc6733081f840a8200581c3542acb3a64d80c29302260d62c3b87a742ad14abf855ebc6733081e581c0f292fcaa02b8b2f9b3c8f9fd8e0bb21abedb692a6d5058df3ef27358200581c4542acb3a64d80c29302260d62c3b87a742ad14abf855ebc6733081f830e8200581c3542acb3a64d80c29302260d62c3b87a742ad14abf855ebc6733081e8200581c4542acb3a64d80c29302260d62c3b87a742ad14abf855ebc6733081f830f8200581c3542acb3a64d80c29302260d62c3b87a742ad14abf855ebc6733081e82782468747470733a2f2f6578616d706c652e636f6d2f72657369676e6174696f6e2e6a736f6e5820000000000000000000000000000000000000000000000000000000000000000084108200581c4542acb3a64d80c29302260d62c3b87a742ad14abf855ebc6733081f1a1dcd650082781d68747470733a2f2f6578616d706c652e636f6d2f647265702e6a736f6e5820111111111111111111111111111111111111111111111111111111111111111183118200581c4542acb3a64d80c29302260d62c3b87a742ad14abf855ebc6733081f1a1dcd650083128200581c4542acb3a64d80c29302260d62c3b87a742ad14abf855ebc6733081f82782568747470733a2f2f6578616d706c652e636f6d2f647265702d757064617465642e6a736f6e58202222222222222222222222222222222222222222222222222222222222222222840b8200581c3542acb3a64d80c29302260d62c3b87a742ad14abf855ebc6733081e581c0f292fcaa02b8b2f9b3c8f9fd8e0bb21abedb692a6d5058df3ef27351a001e8480840c8200581c3542acb3a64d80c29302260d62c3b87a742ad14abf855ebc6733081e8200581c4542acb3a64d80c29302260d62c3b87a742ad14abf855ebc6733081f1a001e8480850d8200581c3542acb3a64d80c29302260d62c3b87a742ad14abf855ebc6733081e581c0f292fcaa02b8b2f9b3c8f9fd8e0bb21abedb692a6d5058df3ef27358200581c4542acb3a64d80c29302260d62c3b87a742ad14abf855ebc6733081f1a001e848082008200581c3542acb3a64d80c29302260d62c3b87a742ad14abf855ebc6733081e82018200581c3542acb3a64d80c29302260d62c3b87a742ad14abf855ebc6733081e8a03581c0f292fcaa02b8b2f9b3c8f9fd8e0bb21abedb692a6d5058df3ef273558208dd154228946bd12967c12bedb1cb6038b78f8b84a1760b1a788fa72a4af3db01b000000174876e8001a1443fd00d81e82031864581de01fa4a08fd7daf8f2ede99a7dd4ff3f9bd93b307f7ae16e47f071e60e81581c1fa4a08fd7daf8f2ede99a7dd4ff3f9bd93b307f7ae16e47f071e60e818400190bb944c0a80101f682782668747470733a2f2f6578616d706c652e636f6d2f706f6f6c2d6d657461646174612e6a736f6e582033333333333333333333333333333333333333333333333333333333333333338a03581c0f292fcaa02b8b2f9b3c8f9fd8e0bb21abedb692a6d5058df3ef273558209dd154228946bd12967c12bedb1cb6038b78f8b84a1760b1a788fa72a4af3db11b0000000ba43b74001a1443fd00d81e82051864581de01fa4a08fd7daf8f2ede99a7dd4ff3f9bd93b307f7ae16e47f071e60e81581c1fa4a08fd7daf8f2ede99a7dd4ff3f9bd93b307f7ae16e47f071e60e818400190bbaf65020010db885a3000000008a2e0370733482782768747470733a2f2f6578616d706c652e636f6d2f706f6f6c322d6d657461646174612e6a736f6e582066666666666666666666666666666666666666666666666666666666666666668a03581c0f292fcaa02b8b2f9b3c8f9fd8e0bb21abedb692a6d5058df3ef27355820add154228946bd12967c12bedb1cb6038b78f8b84a1760b1a788fa72a4af3db21b0000001176592e001a1443fd00d81e82041864581de01fa4a08fd7daf8f2ede99a7dd4ff3f9bd93b307f7ae16e47f071e60e81581c1fa4a08fd7daf8f2ede99a7dd4ff3f9bd93b307f7ae16e47f071e60e818301190bbb7272656c6179312e6578616d706c652e636f6d82782768747470733a2f2f6578616d706c652e636f6d2f706f6f6c332d6d657461646174612e6a736f6e582077777777777777777777777777777777777777777777777777777777777777778a03581c0f292fcaa02b8b2f9b3c8f9fd8e0bb21abedb692a6d5058df3ef27355820bdd154228946bd12967c12bedb1cb6038b78f8b84a1760b1a788fa72a4af3db31b0000001bf08eb0001a1443fd00d81e82021864581de01fa4a08fd7daf8f2ede99a7dd4ff3f9bd93b307f7ae16e47f071e60e81581c1fa4a08fd7daf8f2ede99a7dd4ff3f9bd93b307f7ae16e47f071e60e8182027772656c6179732e706f6f6c2e6578616d706c652e636f6d82782768747470733a2f2f6578616d706c652e636f6d2f706f6f6c342d6d657461646174612e6a736f6e582088888888888888888888888888888888888888888888888888888888888888888304581c0f292fcaa02b8b2f9b3c8f9fd8e0bb21abedb692a6d5058df3ef27351901f405a1581de01fa4a08fd7daf8f2ede99a7dd4ff3f9bd93b307f7ae16e47f071e60e1a000f42400758201010101010101010101010101010101010101010101010101010101010101010081a06e5ffef09af581c0b286ad895d091f2b3d168a6091ad2627d30a72761a5bc36eef0074ea140197530581c2a286ad895d091f2b3d168a6091ad2627d30a72761a5bc36eef00740a1401903e8581c3a286ad895d091f2b3d168a6091ad2627d30a72761a5bc36eef00741a1401909c4581c4a286ad895d091f2b3d168a6091ad2627d30a72761a5bc36eef00742a1401901f4581c5a286ad895d091f2b3d168a6091ad2627d30a72761a5bc36eef00743a140192710581c6a286ad895d091f2b3d168a6091ad2627d30a72761a5bc36eef00744a1401902ee581c7a286ad895d091f2b3d168a6091ad2627d30a72761a5bc36eef00745a140190bb8581c8a286ad895d091f2b3d168a6091ad2627d30a72761a5bc36eef00746a1401905dc581c9a286ad895d091f2b3d168a6091ad2627d30a72761a5bc36eef00747a1401907d0581caa286ad895d091f2b3d168a6091ad2627d30a72761a5bc36eef00748a1403863581cba286ad895d091f2b3d168a6091ad2627d30a72761a5bc36eef00749a14038f9581cca286ad895d091f2b3d168a6091ad2627d30a72761a5bc36eef0074aa1403831581cda286ad895d091f2b3d168a6091ad2627d30a72761a5bc36eef0074ba140190258581cea286ad895d091f2b3d168a6091ad2627d30a72761a5bc36eef0074ca140192710581cfa286ad895d091f2b3d168a6091ad2627d30a72761a5bc36eef0074da140194e200b5820ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff0d818258202f3abbc8fc19c2e61bab6059bf8a466e6e754833a08a62a6c56fe0e78f19d9d7000e81581c6199186adb51974690d7247d2646097d2c62763b767b528816fb7ed30f001083583900a158650cba5554cb499dcef3bf8b01bf6396e1845e3b3052eae534951fa4a08fd7daf8f2ede99a7dd4ff3f9bd93b307f7ae16e47f071e60e821a007a1200a5581c1b286ad895d091f2b3d168a6091ad2627d30a72761a5bc36eef0074fa140190190581c2b286ad895d091f2b3d168a6091ad2627d30a72761a5bc36eef00750a140190226581c3b286ad895d091f2b3d168a6091ad2627d30a72761a5bc36eef00751a140190258581c4b286ad895d091f2b3d168a6091ad2627d30a72761a5bc36eef00752a1401902ee581c5b286ad895d091f2b3d168a6091ad2627d30a72761a5bc36eef00753a14018fa5820c0ffeebadc0ffeebadc0ffeebadc0ffeebadc0ffeebadc0ffeebadc0ffeebade111a004c4b4012818258203f3abbc8fc19c2e61bab6059bf8a466e6e754833a08a62a6c56fe0e78f19d9d80013a38200581c12345678901234567890123456789012345678901234567890abcdefa1825820dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd00820182782168747470733a2f2f6578616d706c652e636f6d2f766f74652d7965732e6a736f6e5820eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee8202581c23456789012345678901234567890123456789012345678901234567a1825820dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd008200f68204581c34567890123456789012345678901234567890123456789012345678a1825820dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd008202f61487841b00000002540be400581de01fa4a08fd7daf8f2ede99a7dd4ff3f9bd93b307f7ae16e47f071e60e8400825820444444444444444444444444444444444444444444444444444444444444444400a100182c581c5555555555555555555555555555555555555555555555555555555582781e68747470733a2f2f6578616d706c652e636f6d2f706172616d2e6a736f6e58203333333333333333333333333333333333333333333333333333333333333333841b00000002540be400581de01fa4a08fd7daf8f2ede99a7dd4ff3f9bd93b307f7ae16e47f071e60e8301f6820a0082782168747470733a2f2f6578616d706c652e636f6d2f68617264666f726b2e6a736f6e58206666666666666666666666666666666666666666666666666666666666666666841b00000002540be400581de01fa4a08fd7daf8f2ede99a7dd4ff3f9bd93b307f7ae16e47f071e60e8302a1581de01fa4a08fd7daf8f2ede99a7dd4ff3f9bd93b307f7ae16e47f071e60e1b000000174876e800f682782168747470733a2f2f6578616d706c652e636f6d2f74726561737572792e6a736f6e58207777777777777777777777777777777777777777777777777777777777777777841b00000002540be400581de01fa4a08fd7daf8f2ede99a7dd4ff3f9bd93b307f7ae16e47f071e60e8203f682781f68747470733a2f2f6578616d706c652e636f6d2f6e6f636f6e662e6a736f6e58208888888888888888888888888888888888888888888888888888888888888888841b00000002540be400581de01fa4a08fd7daf8f2ede99a7dd4ff3f9bd93b307f7ae16e47f071e60e8504f6828200581c3542acb3a64d80c29302260d62c3b87a742ad14abf855ebc6733081e8200581c6542acb3a64d80c29302260d62c3b87a742ad14abf855ebc6733081aa38200581c4542acb3a64d80c29302260d62c3b87a742ad14abf855ebc6733081f1901f48200581c7542acb3a64d80c29302260d62c3b87a742ad14abf855ebc6733081b1901f98201581c8542acb3a64d80c29302260d62c3b87a742ad14abf855ebc6733081c1901fed81e82020382782268747470733a2f2f6578616d706c652e636f6d2f636f6d6d69747465652e6a736f6e58209999999999999999999999999999999999999999999999999999999999999999841b00000002540be400581de01fa4a08fd7daf8f2ede99a7dd4ff3f9bd93b307f7ae16e47f071e60e8305f68282781e68747470733a2f2f6578616d706c652e636f6d2f636f6e73742e6a736f6e5820bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbf682782568747470733a2f2f6578616d706c652e636f6d2f636f6e737469747574696f6e2e6a736f6e5820aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa841b00000002540be400581de01fa4a08fd7daf8f2ede99a7dd4ff3f9bd93b307f7ae16e47f071e60e810682781d68747470733a2f2f6578616d706c652e636f6d2f696e666f2e6a736f6e5820cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc151a05f5e100161a000f4240"),
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
                network=NetworkId.TESTNET,
                extra_signers=[
                    ExtraSigner(
                        xfp=bytes.fromhex("b2743478"),
                        path=[2147485500, 2147485463, 2147483648, 2, 0],
                    ),
                    ExtraSigner(
                        xfp=bytes.fromhex("b2743478"),
                        path=[2147485500, 2147485463, 2147483648, 0, 1],
                    ),
                ],
            )

            # Parse TX body and verify change outputs
            parsed_tx = CardanoParsedTx(sign_request, verified_change_indices=[])
            seed = self.controller.storage.seeds[-1]
            parsed_tx.verified_change_indices = verify_change_outputs(sign_request, seed, parsed_tx.body)

            return Destination(CardanoTxOverviewView, view_args=dict(parsed_tx=parsed_tx))



class CardanoMsgMockMenuView(View):
    """Submenu for CIP-8 message signing test cases."""
    PAYMENT_JSON = ButtonOption("Payment + JSON")
    STAKE_TEXT = ButtonOption("Stake + Text")
    DREP_HEX = ButtonOption("DRep + Hex")
    HASH_PAYLOAD = ButtonOption("28-byte Hash")
    INVALID = ButtonOption("Invalid Path")
    LONG_ORIGIN = ButtonOption("Long Origin")

    # Test mnemonic (shared with TX mock)
    _TEST_MNEMONIC = "device blind mail nose voice aware link achieve tattoo pulse divide tail nut taste upper fork debris helmet fatal myth genre brick champion february"

    def _ensure_seed(self):
        test_mnemonic = self._TEST_MNEMONIC.split()
        test_seed = Seed(mnemonic=test_mnemonic, wordlist_language_code=SettingsConstants.WORDLIST_LANGUAGE__ENGLISH)
        self.controller.storage.set_pending_seed(test_seed)
        self.controller.storage.finalize_pending_seed()

    def run(self):
        from seedsigner.views.msg_sign import CardanoMsgOverviewView
        from seedsigner.models.cardano_tx import CardanoMessageSignRequest, SigningPath

        button_data = [self.PAYMENT_JSON, self.STAKE_TEXT, self.DREP_HEX, self.HASH_PAYLOAD, self.INVALID, self.LONG_ORIGIN]

        selected_menu_num = self.run_screen(
            ButtonListScreen,
            title="Message Mock",
            is_button_text_centered=False,
            button_data=button_data,
        )

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        self._ensure_seed()
        choice = button_data[selected_menu_num]

        if choice == self.PAYMENT_JSON:
            # Base address at m/1852'/1815'/0'/0/0 with JSON payload
            msg_request = CardanoMessageSignRequest(
                request_id="a1111111-1111-1111-1111-111111111111",
                origin="Lace",
                message_payload=b'{"action":"login","domain":"app.example.com","timestamp":"2026-02-19T12:00:00Z","nonce":"f47ac10b58cc","permissions":["read","write"]}',
                address_bytes=bytes.fromhex(
                    "00"
                    "350d57fd8f9f49f429449d89c893df74210ba70b9f13fc6c9736b7e3"
                    "1fa4a08fd7daf8f2ede99a7dd4ff3f9bd93b307f7ae16e47f071e60e"
                ),
                required_signing_path=SigningPath(
                    index=0,
                    path=[2147485500, 2147485463, 2147483648, 0, 0],
                ),
            )

        elif choice == self.STAKE_TEXT:
            # Reward address at m/1852'/1815'/0'/2/0 with plain text
            msg_request = CardanoMessageSignRequest(
                request_id="b2222222-2222-2222-2222-222222222222",
                origin="Eternl",
                message_payload=b"Please sign this message to verify ownership of your stake address.\n\nNonce: abc123\nTimestamp: 2026-02-19T12:00:00Z",
                address_bytes=bytes.fromhex(
                    "e01fa4a08fd7daf8f2ede99a7dd4ff3f9bd93b307f7ae16e47f071e60e"
                ),
                required_signing_path=SigningPath(
                    index=0,
                    path=[2147485500, 2147485463, 2147483648, 2, 0],
                ),
            )

        elif choice == self.DREP_HEX:
            # DRep key at m/1852'/1815'/0'/3/0, raw 28-byte credential, binary payload
            msg_request = CardanoMessageSignRequest(
                request_id="c3333333-3333-3333-3333-333333333333",
                origin="GovTool",
                message_payload=bytes(range(256)) + bytes(range(128)),
                address_bytes=bytes.fromhex(
                    # Raw 28-byte DRep credential key hash
                    "6f238b48d0d20b8737c462a0f6b35d6bc3c379bd2f09258207ef8bb5"
                ),
                required_signing_path=SigningPath(
                    index=0,
                    path=[2147485500, 2147485463, 2147483648, 3, 0],
                ),
            )

        elif choice == self.HASH_PAYLOAD:
            # 28-byte non-ASCII payload (should trigger hash rejection)
            msg_request = CardanoMessageSignRequest(
                request_id="e5555555-5555-5555-5555-555555555555",
                origin="SuspiciousApp",
                message_payload=bytes.fromhex(
                    "350d57fd8f9f49f429449d89c893df74210ba70b9f13fc6c9736b7e3"
                ),
                address_bytes=bytes.fromhex(
                    "00"
                    "350d57fd8f9f49f429449d89c893df74210ba70b9f13fc6c9736b7e3"
                    "1fa4a08fd7daf8f2ede99a7dd4ff3f9bd93b307f7ae16e47f071e60e"
                ),
                required_signing_path=SigningPath(
                    index=0,
                    path=[2147485500, 2147485463, 2147483648, 0, 0],
                ),
            )

        elif choice == self.LONG_ORIGIN:
            # Long origin with non-printable chars to test sanitization
            msg_request = CardanoMessageSignRequest(
                request_id="f6666666-6666-6666-6666-666666666666",
                origin="Super\x00Long\x01Origin\x02Name That Exceeds Thirty Characters Easily",
                message_payload=b"Test message",
                address_bytes=bytes.fromhex(
                    "00"
                    "350d57fd8f9f49f429449d89c893df74210ba70b9f13fc6c9736b7e3"
                    "1fa4a08fd7daf8f2ede99a7dd4ff3f9bd93b307f7ae16e47f071e60e"
                ),
                required_signing_path=SigningPath(
                    index=0,
                    path=[2147485500, 2147485463, 2147483648, 0, 0],
                ),
            )

        elif choice == self.INVALID:
            # Base address but wrong signing path (index 5 instead of 0)
            msg_request = CardanoMessageSignRequest(
                request_id="d4444444-4444-4444-4444-444444444444",
                origin="MaliciousApp",
                message_payload=b"Sign to claim your airdrop!",
                address_bytes=bytes.fromhex(
                    "00"
                    "350d57fd8f9f49f429449d89c893df74210ba70b9f13fc6c9736b7e3"
                    "1fa4a08fd7daf8f2ede99a7dd4ff3f9bd93b307f7ae16e47f071e60e"
                ),
                required_signing_path=SigningPath(
                    index=0,
                    path=[2147485500, 2147485463, 2147483648, 0, 5],
                ),
            )

        return Destination(CardanoMsgOverviewView, view_args=dict(msg_request=msg_request))


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
    TWENTY_FOUR = ButtonOption("24 words", return_data=24)

    def run(self):
        button_data = [self.TWELVE, self.TWENTY_FOUR]

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
        if mnemonic_length == 12:
            num_entropy_bits = 7
        else:
            num_entropy_bits = 3

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

        if mnemonic_length == 12:
            total_flips = 7
        else:
            total_flips = 3
        
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
        num_checksum_bits = 4 if mnemonic_length == 12 else 8
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
            fingerprint=self.controller.storage.get_pending_mnemonic_fingerprint(SettingsConstants.MAINNET),
            button_data=button_data,
        )

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)
        
        self.controller.storage.convert_pending_mnemonic_to_pending_seed()

        if button_data[selected_menu_num] == self.LOAD:
            return Destination(SeedFinalizeView)
        
        elif button_data[selected_menu_num] == self.DISCARD:
            return Destination(SeedDiscardView)



"""****************************************************************************
    Address Explorer Views
****************************************************************************"""
class ToolsAddressExplorerSelectSourceView(View):
    SCAN_SEED = ButtonOption("Scan a seed", SeedSignerIconConstants.QRCODE)
    SCAN_DESCRIPTOR = ButtonOption("Scan wallet descriptor", SeedSignerIconConstants.QRCODE)
    TYPE_12WORD = ButtonOption("Enter 12-word seed", FontAwesomeIconConstants.KEYBOARD, return_data=12)
    TYPE_24WORD = ButtonOption("Enter 24-word seed", FontAwesomeIconConstants.KEYBOARD, return_data=24)
    TYPE_ELECTRUM = ButtonOption("Enter Electrum seed", FontAwesomeIconConstants.KEYBOARD)

    def run(self):
        from seedsigner.controller import Controller

        seeds = self.controller.storage.seeds
        button_data = []
        for seed in seeds:
            button_str = seed.get_fingerprint(SettingsConstants.MAINNET)
            button_data.append(ButtonOption(button_str, SeedSignerIconConstants.FINGERPRINT, icon_color=GUIConstants.ACCENT_TEXT_COLOR))
        button_data = button_data + [self.SCAN_SEED, self.SCAN_DESCRIPTOR, self.TYPE_12WORD, self.TYPE_24WORD]
        selected_menu_num = self.run_screen(
            ButtonListScreen,
            title=_("Address Explorer"),
            button_data=button_data,
            is_button_text_centered=False,
            is_bottom_list=True,
        )

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        # Most of the options require us to go through a side flow(s) before we can
        # continue to the address explorer. Set the Controller-level flow so that it
        # knows to re-route us once the side flow is complete.        
        self.controller.resume_main_flow = Controller.FLOW__ADDRESS_EXPLORER

        if len(seeds) > 0 and selected_menu_num < len(seeds):
            # User selected one of the n seeds
            return Destination(
                SeedExportXpubScriptTypeView,
                view_args=dict(
                    seed_num=selected_menu_num,
                    sig_type=SettingsConstants.SINGLE_SIG,
                )
            )

        elif button_data[selected_menu_num] == self.SCAN_SEED:
            from seedsigner.views.scan_views import ScanSeedQRView
            return Destination(ScanSeedQRView)

        elif button_data[selected_menu_num] == self.SCAN_DESCRIPTOR:
            from seedsigner.views.scan_views import ScanWalletDescriptorView
            return Destination(ScanWalletDescriptorView)

        elif button_data[selected_menu_num] in [self.TYPE_12WORD, self.TYPE_24WORD]:
            from seedsigner.views.seed_views import SeedMnemonicEntryView
            self.controller.storage.init_pending_mnemonic(num_words=button_data[selected_menu_num].return_data)
            return Destination(SeedMnemonicEntryView)

        elif button_data[selected_menu_num] == self.TYPE_ELECTRUM:
            from seedsigner.views.seed_views import SeedElectrumMnemonicStartView
            return Destination(SeedElectrumMnemonicStartView)



class ToolsAddressExplorerAddressTypeView(View):
    # TRANSLATOR_NOTE: label for addresses where others send us incoming payments
    RECEIVE = ButtonOption("Receive addresses")

    # TRANSLATOR_NOTE: label for addresses that collect the change from our own outgoing payments
    CHANGE = ButtonOption("Change addresses")


    def __init__(self, seed_num: int = None, script_type: str = None, custom_derivation: str = None):
        """
            If the explorer source is a seed, `seed_num` and `script_type` must be
            specified. `custom_derivation` can be specified as needed.

            If the source is a multisig or single sig wallet descriptor, `seed_num`,
            `script_type`, and `custom_derivation` should be `None`.
        """
        super().__init__()
        self.seed_num = seed_num
        self.script_type = script_type
        self.custom_derivation = custom_derivation
    
        network = SettingsConstants.MAINNET

        # Store everything in the Controller's `address_explorer_data` so we don't have
        # to keep passing vals around from View to View and recalculating.
        data = dict(
            seed_num=seed_num,
            network=SettingsConstants.MAINNET,
            embit_network=SettingsConstants.map_network_to_embit(network),
            script_type=script_type,
        )
        if self.seed_num is not None:
            self.seed = self.controller.storage.seeds[seed_num]
            data["seed_num"] = self.seed
            seed_derivation_override = self.seed.derivation_override(sig_type=SettingsConstants.SINGLE_SIG)

            if self.script_type == SettingsConstants.CUSTOM_DERIVATION:
                derivation_path = self.custom_derivation
            elif seed_derivation_override:
                derivation_path = seed_derivation_override
            else:
                from seedsigner.helpers import embit_utils
                derivation_path = embit_utils.get_standard_derivation_path(
                    network=SettingsConstants.MAINNET,
                    wallet_type=SettingsConstants.SINGLE_SIG,
                    script_type=self.script_type,
                )

            data["derivation_path"] = derivation_path
            data["xpub"] = self.seed.get_xpub(derivation_path, network=network)
        
        else:
            data["wallet_descriptor"] = self.controller.multisig_wallet_descriptor

        self.controller.address_explorer_data = data


    def run(self):
        from seedsigner.gui.screens.tools_screens import ToolsAddressExplorerAddressTypeScreen
        data = self.controller.address_explorer_data

        wallet_descriptor_display_name = None
        if "wallet_descriptor" in data:
            wallet_descriptor_display_name = data["wallet_descriptor"].brief_policy.replace(" (sorted)", "")
            wallet_descriptor_display_name = " / ".join(wallet_descriptor_display_name.split(" of ")) # i18n w/o l10n since coming from non-l10n embit

        script_type = data["script_type"] if "script_type" in data else None

        button_data = [self.RECEIVE, self.CHANGE]

        selected_menu_num = self.run_screen(
            ToolsAddressExplorerAddressTypeScreen,
            button_data=button_data,
            fingerprint=self.seed.get_fingerprint() if self.seed_num is not None else None,
            wallet_descriptor_display_name=wallet_descriptor_display_name,
            script_type=script_type,
            custom_derivation_path=self.custom_derivation,
        )

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            # If we entered this flow via an already-loaded seed's SeedOptionsView, we
            # need to clear the `resume_main_flow` so that we don't get stuck in a 
            # SeedOptionsView redirect loop.
            # TODO: Refactor to a cleaner `BackStack.get_previous_View_cls()`
            if len(self.controller.back_stack) > 1 and self.controller.back_stack[-2].View_cls == SeedOptionsView:
                # The BackStack has the current View on the top with the real "back" in second position.
                self.controller.resume_main_flow = None
                self.controller.address_explorer_data = None
            return Destination(BackStackView)
        
        elif button_data[selected_menu_num] in [self.RECEIVE, self.CHANGE]:
            return Destination(ToolsAddressExplorerAddressListView, view_args=dict(is_change=button_data[selected_menu_num] == self.CHANGE))



class ToolsAddressExplorerAddressListView(View):
    def __init__(self, is_change: bool = False, start_index: int = 0, selected_button_index: int = 0, initial_scroll: int = 0):
        super().__init__()
        self.is_change = is_change
        self.start_index = start_index
        self.selected_button_index = selected_button_index
        self.initial_scroll = initial_scroll


    def run(self):
        from seedsigner.gui.screens.tools_screens import ToolsAddressExplorerAddressListScreen
        self.loading_screen = None

        addresses = []
        button_data = []
        data = self.controller.address_explorer_data
        addrs_per_screen = 10

        addr_storage_key = "receive_addrs"
        if self.is_change:
            addr_storage_key = "change_addrs"

        if addr_storage_key in data and len(data[addr_storage_key]) >= self.start_index + addrs_per_screen:
            # We already calculated this range of addresses; just retrieve them
            addresses = data[addr_storage_key][self.start_index:self.start_index + addrs_per_screen]

        else:
            try:
                from seedsigner.gui.screens.screen import LoadingScreenThread
                from seedsigner.helpers import embit_utils
                # TRANSLATOR_NOTE: a status message that our payment addresses are being calculated
                self.loading_screen = LoadingScreenThread(text=_("Calculating addrs..."))
                self.loading_screen.start()

                if addr_storage_key not in data:
                    data[addr_storage_key] = []

                if "xpub" in data:
                    # Single sig explore from seed
                    if "script_type" in data and data["script_type"] != SettingsConstants.CUSTOM_DERIVATION:
                        # Standard derivation path
                        for i in range(self.start_index, self.start_index + addrs_per_screen):
                            address = embit_utils.get_single_sig_address(xpub=data["xpub"], script_type=data["script_type"], index=i, is_change=self.is_change, embit_network=data["embit_network"])
                            addresses.append(address)
                            data[addr_storage_key].append(address)
                    else:
                        # TODO: Custom derivation path
                        raise Exception(_("Custom Derivation address explorer not yet implemented"))

                elif "wallet_descriptor" in data:
                    from embit.descriptor import Descriptor
                    descriptor: Descriptor = data["wallet_descriptor"]
                    if descriptor.is_basic_multisig:
                        for i in range(self.start_index, self.start_index + addrs_per_screen):
                            address = embit_utils.get_multisig_address(descriptor=descriptor, index=i, is_change=self.is_change, embit_network=data["embit_network"])
                            addresses.append(address)
                            data[addr_storage_key].append(address)

                    else:
                        raise Exception(_("Single sig descriptors not yet supported"))
            finally:
                # Everything is set. Stop the loading screen
                self.loading_screen.stop()

        selected_menu_num = self.run_screen(
            ToolsAddressExplorerAddressListScreen,
            title=_("Receive Addrs") if not self.is_change else _("Change Addrs"),
            start_index=self.start_index,
            addresses=addresses,
            selected_button=self.selected_button_index,
            scroll_y_initial_offset=self.initial_scroll,
        )

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)
        
        if selected_menu_num == len(addresses):
            # User clicked NEXT
            return Destination(ToolsAddressExplorerAddressListView, view_args=dict(is_change=self.is_change, start_index=self.start_index + addrs_per_screen))
        
        # Preserve the list's current scroll so we can return to the same spot
        initial_scroll = self.screen.buttons[0].scroll_y

        index = selected_menu_num + self.start_index
        return Destination(ToolsAddressExplorerAddressView, view_args=dict(index=index, address=addresses[selected_menu_num], is_change=self.is_change, start_index=self.start_index, parent_initial_scroll=initial_scroll), skip_current_view=True)



class ToolsAddressExplorerAddressView(View):
    # TODO: pull address str from controller.address_explorer_data and pass addr_storage_key and addr_index instead
    def __init__(self, index: int, address: str, is_change: bool, start_index: int, parent_initial_scroll: int = 0):
        super().__init__()
        self.index = index
        self.address = address
        self.is_change = is_change
        self.start_index = start_index
        self.parent_initial_scroll = parent_initial_scroll

    
    def run(self):
        from seedsigner.gui.screens.screen import QRDisplayScreen
        from seedsigner.models.encode_qr import GenericStaticQrEncoder

        qr_encoder = GenericStaticQrEncoder(data=self.address)
        self.run_screen(
            QRDisplayScreen,
            qr_encoder=qr_encoder,
        )
    
        # Exiting/Cancelling the QR display screen always returns to the list
        return Destination(ToolsAddressExplorerAddressListView, view_args=dict(is_change=self.is_change, start_index=self.start_index, selected_button_index=self.index - self.start_index, initial_scroll=self.parent_initial_scroll), skip_current_view=True)
