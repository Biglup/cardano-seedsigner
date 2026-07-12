"""Final confirmation screen before signing a CIP-8 message, and the animated QR
view that transmits the resulting COSE_Sign1 + COSE_Key back to the host."""

import logging
from gettext import gettext as _

from seedsigner.gui.screens import RET_CODE__BACK_BUTTON
from seedsigner.gui.screens.screen import ButtonOption
from seedsigner.models.cardano_tx import CardanoMessageSignRequest, CardanoCip8SignResponse
from seedsigner.models.settings import SettingsConstants

from seedsigner.views.view import View, Destination, BackStackView, MainMenuView


logger = logging.getLogger(__name__)


def _get_address_info(address_bytes):
    """Return (network, address_type) strings, or (None, None) if unavailable."""
    if address_bytes is None:
        return None, None

    from cometa import Address, AddressType

    try:
        addr = Address.from_bytes(address_bytes)
        addr_type = AddressType(addr.type)
        network = "Mainnet" if addr.network_id == 1 else "Testnet"

        type_labels = {
            AddressType.BASE_PAYMENT_KEY_STAKE_KEY: "Payment",
            AddressType.BASE_PAYMENT_KEY_STAKE_SCRIPT: "Payment",
            AddressType.ENTERPRISE_KEY: "Enterprise",
            AddressType.REWARD_KEY: "Stake",
            AddressType.REWARD_SCRIPT: "Stake",
        }
        label = type_labels.get(addr_type, "Unknown")
        return network, label
    except Exception:
        pass

    if len(address_bytes) == 28:
        return None, "DRep"

    return None, None


def _compute_payload_hash(payload):
    """Compute Blake2b-256 hash of the payload, return hex string."""
    from cometa import Blake2bHash
    h = Blake2bHash.compute(payload, hash_size=32)
    return h.to_bytes().hex()


class CardanoMsgSignView(View):
    """Sign Message - Final confirmation screen."""

    def __init__(self, msg_request: CardanoMessageSignRequest):
        super().__init__()
        self.msg_request = msg_request

    def run(self):
        """Confirm and sign the reviewed message.

        The request may name a specific signer (xfp); the selected seed
        must match it, otherwise the signature would be from the wrong
        key. The confirmation screen returns 0 for Cancel and 1 for Sign.
        """
        from seedsigner.gui.screens.screen import WarningScreen
        from seedsigner.helpers.cardano_signing import build_cip8_sign_response

        seed = self.controller.cardano_seed
        request = self.msg_request

        if seed is not None and request.xfp and request.xfp != bytes.fromhex(seed.get_fingerprint()):
            self.run_screen(
                WarningScreen,
                title=_("Cannot Sign"),
                status_headline=_("Wrong Seed"),
                text=_("This seed does not match the requested signer."),
                show_back_button=False,
                button_data=[ButtonOption("OK")],
            )
            return Destination(MainMenuView, clear_history=True)

        payload_hash = _compute_payload_hash(self.msg_request.message_payload)

        selected_menu_num = self.run_screen(
            _MsgSignScreen,
            payload_hash=payload_hash,
        )

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        if selected_menu_num == 0:
            return Destination(MainMenuView, clear_history=True)

        elif selected_menu_num == 1:
            if seed is None:
                return Destination(MainMenuView, clear_history=True)
            try:
                response = build_cip8_sign_response(seed, request)
            except Exception as e:
                logger.info(repr(e), exc_info=True)
                self.run_screen(
                    WarningScreen,
                    title=_("Cannot Sign"),
                    status_headline=_("Rejected"),
                    text=_("The message could not be signed for this address."),
                    show_back_button=False,
                    button_data=[ButtonOption("OK")],
                )
                return Destination(MainMenuView, clear_history=True)
            return Destination(
                CardanoMsgSignedQRView,
                view_args=dict(response=response),
            )


class CardanoMsgSignedQRView(View):
    """Transmit the COSE_Sign1 + COSE_Key back to the host as an animated QR."""

    def __init__(self, response: CardanoCip8SignResponse):
        super().__init__()
        from seedsigner.models.encode_qr import CardanoCip8SigResponseQrEncoder

        self.qr_encoder = CardanoCip8SigResponseQrEncoder(
            response=response,
            qr_density=self.settings.get_value(SettingsConstants.SETTING__QR_DENSITY),
        )

    def run(self):
        from seedsigner.gui.screens.screen import QRDisplayScreen

        self.run_screen(QRDisplayScreen, qr_encoder=self.qr_encoder)

        self.controller.cardano_cip8_sign_request = None
        self.controller.cardano_seed = None
        return Destination(MainMenuView, clear_history=True)


from dataclasses import dataclass

from seedsigner.gui.components import (
    GUIConstants,
    TextArea,
    FontAwesomeIconConstants,
    SeedSignerIconConstants,
)
from seedsigner.gui.screens.screen import ButtonListScreen


@dataclass
class _MsgSignScreen(ButtonListScreen):
    """Final confirmation screen before signing a message."""
    payload_hash: str = ""

    def __post_init__(self):
        self.title = "Sign Message"
        self.is_bottom_list = True
        self.button_data = [
            ButtonOption("Cancel", FontAwesomeIconConstants.X),
            ButtonOption("Sign", SeedSignerIconConstants.CHECK),
        ]

        super().__post_init__()

        cur_y = self.top_nav.height + GUIConstants.COMPONENT_PADDING * 2

        confirm_text = TextArea(
            text="Sign?",
            font_size=GUIConstants.get_top_nav_title_font_size() + 8,
            font_color=GUIConstants.BODY_FONT_COLOR,
            screen_x=0,
            screen_y=cur_y,
            is_text_centered=True,
            auto_line_break=False,
        )
        self.components.append(confirm_text)
        cur_y += confirm_text.height + GUIConstants.COMPONENT_PADDING * 2

        if self.payload_hash:
            hash_label = TextArea(
                text="Payload Hash:",
                font_size=GUIConstants.get_body_font_size(),
                font_color=GUIConstants.BODY_FONT_COLOR,
                screen_x=0,
                screen_y=cur_y,
                is_text_centered=True,
                auto_line_break=False,
            )
            self.components.append(hash_label)
            cur_y += hash_label.height + 4

            h = self.payload_hash
            if len(h) > 16:
                truncated = f"{h[:8]}...{h[-8:]}"
            else:
                truncated = h

            hash_area = TextArea(
                text=truncated,
                font_name=GUIConstants.FIXED_WIDTH_FONT_NAME,
                font_size=22,
                font_color=GUIConstants.ACCENT_TEXT_COLOR,
                screen_x=0,
                screen_y=cur_y,
                is_text_centered=True,
                auto_line_break=False,
            )
            self.components.append(hash_area)
