"""Address display screen for CIP-8 message signing."""

from seedsigner.gui.screens import RET_CODE__BACK_BUTTON
from seedsigner.gui.screens.tx_review import (
    RET_CODE__LEFT_BUTTON,
    RET_CODE__RIGHT_BUTTON,
)
from seedsigner.models.cardano_tx import CardanoMessageSignRequest
from seedsigner.views.view import View, Destination, BackStackView

_TOTAL_PAGES = 3


class CardanoMsgAddressView(View):
    """Shows the signing credential: a payment address, stake address, DRep ID,
    or key hash, depending on the request."""

    def __init__(self, msg_request: CardanoMessageSignRequest):
        super().__init__()
        self.msg_request = msg_request

    def run(self):
        from seedsigner.gui.screens.tx_review import CardanoContentSequentialScreen, Line
        from seedsigner.views.tx_review.certificate_view import _format_bech32

        content = []

        if self.msg_request.address_bytes:
            from seedsigner.helpers.cardano_utils import describe_signing_credential
            signing_path = self.msg_request.required_signing_path.path
            label, bech32_str = describe_signing_credential(
                self.msg_request.address_bytes, signing_path)
            content.append(Line.label(label))
            content.append(Line.spacer_small())
            fmt, hn, tn = _format_bech32(bech32_str)
            content.append(Line.hash(fmt, hn, tn))
        else:
            content.append(Line.label("Address:"))
            content.append(Line.spacer_small())
            content.append(Line.value_highlight("(not provided)"))

        result = self.run_screen(
            CardanoContentSequentialScreen,
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
                view_args=dict(msg_request=self.msg_request),
                skip_current_view=True,
            )

        return Destination(BackStackView)
