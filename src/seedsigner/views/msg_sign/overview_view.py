"""Message signing overview — first screen in the CIP-8 flow."""

from seedsigner.gui.screens import RET_CODE__BACK_BUTTON, ButtonListScreen
from seedsigner.gui.screens.screen import ButtonOption
from seedsigner.models.cardano_tx import CardanoMessageSignRequest

from seedsigner.views.view import View, Destination, BackStackView, MainMenuView


class CardanoMsgOverviewView(View):
    """Overview screen — 'Sign Message' with origin and Review button."""

    REVIEW = ButtonOption("Review details")

    def __init__(self, msg_request: CardanoMessageSignRequest):
        super().__init__()
        self.msg_request = msg_request

    def run(self):
        from seedsigner.gui.components import GUIConstants, TextArea
        from seedsigner.gui.screens.screen import DireWarningScreen
        from seedsigner.helpers.cardano_utils import verify_message_signing_address
        from .payload_view import _is_printable_ascii

        seed = self.controller.cardano_seed
        if seed is None:
            return Destination(MainMenuView, clear_history=True)

        # Verify the signing path matches the address
        if self.msg_request.address_bytes is not None:
            if not verify_message_signing_address(self.msg_request, seed):
                self._show_rejection(
                    DireWarningScreen, GUIConstants, TextArea,
                    title="Address Mismatch",
                    headline="Request Rejected",
                    lines=["Signing path does not", "match the given address."],
                )
                return Destination(MainMenuView, clear_history=True)

        # Reject 28-byte non-ASCII payloads (potential Blake2b-224 hash)
        payload = self.msg_request.message_payload
        if len(payload) == 28 and not _is_printable_ascii(payload):
            self._show_rejection(
                DireWarningScreen, GUIConstants, TextArea,
                title="Suspicious Payload",
                headline="Request Rejected",
                lines=[
                    "Payload is exactly 28 bytes",
                    "and may be a hash.",
                    "Signing hashes is unsafe.",
                ],
            )
            return Destination(MainMenuView, clear_history=True)

        from .address_view import CardanoMsgAddressView

        from .sign_view import _get_address_info
        from seedsigner.helpers.cardano_utils import (
            classify_signing_credential,
            CREDENTIAL_SHORT_LABEL,
        )

        network, _ = _get_address_info(self.msg_request.address_bytes)
        if self.msg_request.address_bytes:
            kind = classify_signing_credential(
                self.msg_request.address_bytes,
                self.msg_request.required_signing_path.path,
            )
            addr_type = CREDENTIAL_SHORT_LABEL[kind]
        else:
            addr_type = None

        payload_size = f"{len(self.msg_request.message_payload)} bytes"

        origin = _sanitize_origin(self.msg_request.origin)

        selected_menu_num = self.run_screen(
            _MsgOverviewScreen,
            origin=origin,
            network=network,
            addr_type=addr_type,
            payload_size=payload_size,
        )

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        return Destination(
            CardanoMsgAddressView,
            view_args=dict(msg_request=self.msg_request, page_index=0),
        )

    def _show_rejection(self, DireWarningScreen, GUIConstants, TextArea,
                        title, headline, lines):
        """Display a DireWarningScreen with rejection message."""
        self.screen = DireWarningScreen(
            title=title,
            status_headline=headline,
        )
        last = self.screen.components[-1]
        cur_y = last.screen_y + last.height + GUIConstants.COMPONENT_PADDING
        for text in lines:
            ta = TextArea(
                text=text,
                font_size=GUIConstants.get_body_font_size(),
                font_color=GUIConstants.BODY_FONT_COLOR,
                screen_x=0,
                screen_y=cur_y,
                is_text_centered=True,
                auto_line_break=False,
            )
            self.screen.components.append(ta)
            cur_y += ta.height + 2
        self.screen.display()


def _sanitize_origin(origin):
    """Strip non-printable chars and cap at 30 characters."""
    if not origin:
        return origin
    cleaned = "".join(c for c in origin if c.isprintable())
    if len(cleaned) > 20:
        cleaned = cleaned[:20] + "..."
    return cleaned or None


from dataclasses import dataclass

from seedsigner.gui.components import GUIConstants, TextArea


@dataclass
class _MsgOverviewScreen(ButtonListScreen):
    """Overview screen for message signing."""
    origin: str = None
    network: str = None
    addr_type: str = None
    payload_size: str = None

    def __post_init__(self):
        self.title = "Sign Message"
        self.is_bottom_list = True
        self.button_data = [CardanoMsgOverviewView.REVIEW]

        super().__post_init__()

        rows = []
        if self.origin:
            rows.append(("Origin:", self.origin))
        if self.network:
            rows.append(("Network:", self.network))
        if self.addr_type:
            rows.append(("Sign With:", self.addr_type))
        if self.payload_size:
            rows.append(("Payload:", self.payload_size))

        row_spacing = 6
        cur_y = 50

        # Fixed row advance heights (use "y" to include descender space)
        label_h = TextArea(text="y", font_size=GUIConstants.get_body_font_size() - 2,
                           auto_line_break=False).height
        value_h = TextArea(text="y", font_size=GUIConstants.get_body_font_size(),
                           auto_line_break=False).height

        for label, value in rows:
            cur_y = self._add_row(cur_y, label, value, row_spacing,
                                  label_h, value_h)

    def _add_row(self, cur_y, label, value, spacing, label_h, value_h):
        label_area = TextArea(
            text=label,
            font_size=GUIConstants.get_body_font_size() - 2,
            font_color=GUIConstants.BODY_FONT_COLOR,
            screen_x=GUIConstants.EDGE_PADDING,
            screen_y=cur_y,
            is_text_centered=False,
            auto_line_break=False,
        )
        self.components.append(label_area)
        cur_y += label_h + 4

        value_area = TextArea(
            text=value,
            font_size=GUIConstants.get_body_font_size(),
            font_color=GUIConstants.ACCENT_TEXT_COLOR,
            screen_x=0,
            screen_y=cur_y,
            is_text_centered=True,
            auto_line_break=False,
        )
        self.components.append(value_area)
        cur_y += value_h + spacing
        return cur_y
