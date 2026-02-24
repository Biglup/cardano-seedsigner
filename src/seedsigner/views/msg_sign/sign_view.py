"""Final confirmation screen before signing a CIP-8 message."""

from seedsigner.gui.screens import RET_CODE__BACK_BUTTON
from seedsigner.models.cardano_tx import CardanoMessageSignRequest

from seedsigner.views.view import View, Destination, BackStackView, MainMenuView


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
        payload_hash = _compute_payload_hash(self.msg_request.message_payload)

        selected_menu_num = self.run_screen(
            _MsgSignScreen,
            payload_hash=payload_hash,
        )

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        if selected_menu_num == 0:  # Cancel
            return Destination(MainMenuView)
        elif selected_menu_num == 1:  # Sign
            return Destination(MainMenuView, clear_history=True)


from dataclasses import dataclass

from seedsigner.gui.components import (
    GUIConstants,
    TextArea,
    FontAwesomeIconConstants,
    SeedSignerIconConstants,
)
from seedsigner.gui.screens.screen import ButtonListScreen, ButtonOption


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

        # Payload hash
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

            # Show first 8 + last 8 hex chars
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
