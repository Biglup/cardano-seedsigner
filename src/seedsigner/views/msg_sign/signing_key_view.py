"""Signing-key inspection step for CIP-8 message signing.

A CIP-8 request signs a single path, so this shows one key page (the seed
fingerprint and the full derivation path, centered), gating the final sign
confirmation exactly like the transaction flow's signing-keys step.
"""

from seedsigner.gui.screens import RET_CODE__BACK_BUTTON
from seedsigner.gui.screens.tx_review import (
    RET_CODE__LEFT_BUTTON,
    RET_CODE__RIGHT_BUTTON,
)
from seedsigner.models.cardano_tx import CardanoMessageSignRequest
from seedsigner.views.view import View, Destination, BackStackView, MainMenuView

_TOTAL_PAGES = 3


class CardanoMsgSigningKeyView(View):
    """The single signing key the CIP-8 request names, shown before Sign."""

    def __init__(self, msg_request: CardanoMessageSignRequest):
        super().__init__()
        self.msg_request = msg_request

    def run(self):
        from seedsigner.gui.screens.tx_review import CardanoContentSequentialScreen
        from seedsigner.views.tx_review.signing_keys_view import build_signing_key_content

        seed = self.controller.cardano_seed
        if seed is None:
            return Destination(MainMenuView, clear_history=True)

        content = build_signing_key_content(
            seed,
            self.msg_request.required_signing_path.path,
        )

        result = self.run_screen(
            CardanoContentSequentialScreen,
            title="Signing Key",
            page_num=3,
            total_pages=_TOTAL_PAGES,
            has_left=True,
            has_right=True,
            content=content,
        )
        return self._handle_navigation(result)

    def _handle_navigation(self, result):
        """Route the screen result on to the final sign confirmation, or back."""
        from .sign_view import CardanoMsgSignView

        if result == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        if result == RET_CODE__LEFT_BUTTON:
            return Destination(BackStackView)

        if result == RET_CODE__RIGHT_BUTTON:
            return Destination(
                CardanoMsgSignView,
                view_args=dict(msg_request=self.msg_request),
            )

        return Destination(BackStackView)
