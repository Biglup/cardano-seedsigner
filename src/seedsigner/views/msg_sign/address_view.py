"""Address display screen for CIP-8 message signing."""

from seedsigner.gui.screens import RET_CODE__BACK_BUTTON
from seedsigner.gui.screens.tx_review import (
    RET_CODE__LEFT_BUTTON,
    RET_CODE__RIGHT_BUTTON,
)
from seedsigner.models.cardano_tx import CardanoMessageSignRequest
from seedsigner.views.view import View, Destination, BackStackView

# Total pages in the message signing flow (address, payload)
_TOTAL_PAGES = 2


class CardanoMsgAddressView(View):
    """Shows the signing address in bech32."""

    def __init__(self, msg_request: CardanoMessageSignRequest, page_index: int = 0):
        super().__init__()
        self.msg_request = msg_request
        self.page_index = page_index

    def run(self):
        from seedsigner.gui.screens.tx_review import CardanoCertificateSequentialScreen
        from seedsigner.views.tx_review.certificate_view import _format_bech32

        content = []

        if self.msg_request.address_bytes:
            from seedsigner.helpers.cardano_utils import describe_signing_credential
            signing_path = self.msg_request.required_signing_path.path
            label, bech32_str = describe_signing_credential(
                self.msg_request.address_bytes, signing_path)
            content.append(("label", label))
            content.append(("spacer_small", ""))
            fmt, hn, tn = _format_bech32(bech32_str)
            content.append(("hash_display", fmt, hn, tn))
        else:
            content.append(("label", "Address:"))
            content.append(("spacer_small", ""))
            content.append(("value_highlight", "(not provided)"))

        result = self.run_screen(
            CardanoCertificateSequentialScreen,
            title="Sign With",
            page_num=1,
            total_pages=_TOTAL_PAGES,
            has_left=True,
            has_right=True,
            content=content,
        )

        return self._handle_navigation(result)

    def _handle_navigation(self, result):
        from .payload_view import CardanoMsgPayloadView

        if result == RET_CODE__BACK_BUTTON or result == -1:
            return Destination(BackStackView)

        if result == RET_CODE__LEFT_BUTTON:
            return Destination(BackStackView)

        if result == RET_CODE__RIGHT_BUTTON:
            return Destination(
                CardanoMsgPayloadView,
                view_args=dict(msg_request=self.msg_request, page_index=1),
                skip_current_view=True,
            )

        return Destination(BackStackView)
