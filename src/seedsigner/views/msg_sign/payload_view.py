"""Payload display screen for CIP-8 message signing."""

import json

from seedsigner.gui.screens import RET_CODE__BACK_BUTTON
from seedsigner.gui.screens.tx_review import (
    RET_CODE__LEFT_BUTTON,
    RET_CODE__RIGHT_BUTTON,
)
from seedsigner.models.cardano_tx import CardanoMessageSignRequest
from seedsigner.views.view import View, Destination, BackStackView

_TOTAL_PAGES = 3


def _is_printable_ascii(data: bytes) -> bool:
    """Check if all bytes are printable ASCII (0x20-0x7E) or common whitespace."""
    for b in data:
        if b == 0x0A or b == 0x0D or b == 0x09:  # newline, CR, tab
            continue
        if b < 0x20 or b > 0x7E:
            return False
    return True


class CardanoMsgPayloadView(View):
    """Shows the message payload as ASCII text, JSON, or hex."""

    def __init__(self, msg_request: CardanoMessageSignRequest, page_index: int = 1):
        super().__init__()
        self.msg_request = msg_request
        self.page_index = page_index

    def run(self):
        from seedsigner.gui.screens.tx_review import CardanoCertificateSequentialScreen

        payload = self.msg_request.message_payload
        content = []
        size = len(payload)

        if size == 0:
            content.append(("label", "Empty Message"))
        else:
            # Try UTF-8 decode → printable check → JSON check
            try:
                text = payload.decode("utf-8")
                if _is_printable_ascii(payload):
                    # Try JSON pretty-print
                    try:
                        parsed = json.loads(text)
                        pretty = json.dumps(parsed, indent=2)
                        content.append(("label", f"JSON ({size} bytes):"))
                        content.append(("spacer_small", ""))
                        for line in pretty.split("\n"):
                            content.append(("mono_text", line))
                    except (json.JSONDecodeError, ValueError, RecursionError):
                        # Plain ASCII text
                        content.append(("label", f"Plain Text ({size} bytes):"))
                        content.append(("spacer_small", ""))
                        for line in text.split("\n"):
                            content.append(("value_highlight", line))
                else:
                    content.append(("label", f"Raw Binary ({size} bytes):"))
                    content.append(("spacer_small", ""))
                    self._add_hex_display(content, payload)
            except UnicodeDecodeError:
                content.append(("label", f"Raw Binary ({size} bytes):"))
                content.append(("spacer_small", ""))
                self._add_hex_display(content, payload)

        result = self.run_screen(
            CardanoCertificateSequentialScreen,
            title="Payload",
            page_num=2,
            total_pages=_TOTAL_PAGES,
            has_left=True,
            has_right=True,
            content=content,
        )

        return self._handle_navigation(result)

    def _add_hex_display(self, content, data: bytes):
        """Add hex data as left-aligned monospace lines."""
        hex_str = data.hex()
        content.append(("mono_text", hex_str))

    def _handle_navigation(self, result):
        from .address_view import CardanoMsgAddressView
        from .signing_key_view import CardanoMsgSigningKeyView

        if result == RET_CODE__BACK_BUTTON or result == -1:
            return Destination(BackStackView)

        if result == RET_CODE__LEFT_BUTTON:
            return Destination(
                CardanoMsgAddressView,
                view_args=dict(msg_request=self.msg_request, page_index=0),
                skip_current_view=True,
            )

        if result == RET_CODE__RIGHT_BUTTON:
            return Destination(
                CardanoMsgSigningKeyView,
                view_args=dict(msg_request=self.msg_request),
            )

        return Destination(BackStackView)
