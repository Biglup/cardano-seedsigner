"""Message signing overview, the first screen in the CIP-8 flow."""

from seedsigner.gui.components import GUIConstants
from seedsigner.gui.screens import RET_CODE__BACK_BUTTON
from seedsigner.gui.screens.screen import ButtonOption
from seedsigner.helpers.cardano_utils import sanitize_origin
from seedsigner.models.cardano_tx import CardanoMessageSignRequest

from seedsigner.views.view import View, Destination, BackStackView, MainMenuView


class CardanoMsgOverviewView(View):
    """Overview screen: 'Sign Message' with origin and Review button."""

    REVIEW = ButtonOption("Review details")

    def __init__(self, msg_request: CardanoMessageSignRequest):
        super().__init__()
        self.msg_request = msg_request

    def run(self):
        """Validate the request, then show the overview.

        Rejects the request when the declared signing path does not derive
        the given address, and rejects any 28-byte non-ASCII payload since
        it may be a Blake2b-224 hash (blind hash signing is unsafe).
        """
        from seedsigner.helpers.cardano_utils import verify_message_signing_address
        from .payload_view import _is_printable_ascii

        seed = self.controller.cardano_seed
        if seed is None:
            return Destination(MainMenuView, clear_history=True)

        if self.msg_request.address_bytes is not None:
            if not verify_message_signing_address(self.msg_request, seed):
                self._show_rejection(
                    title="Address Mismatch",
                    headline="Request Rejected",
                    lines=["Signing path does not", "match the given address."],
                )
                return Destination(MainMenuView, clear_history=True)

        payload = self.msg_request.message_payload
        if len(payload) == 28 and not _is_printable_ascii(payload):
            self._show_rejection(
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

        origin = sanitize_origin(self.msg_request.origin)

        rows = []
        if origin:
            rows.append(("Origin:", origin))
        if network:
            rows.append(("Network:", network))
        if addr_type:
            rows.append(("Sign With:", addr_type))
        if payload_size:
            rows.append(("Payload:", payload_size))

        from seedsigner.gui.screens.tx_review import CardanoOverviewScreen

        selected_menu_num = self.run_screen(
            CardanoOverviewScreen,
            title="Sign Message",
            button_data=[self.REVIEW],
            rows=rows,
        )

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        return Destination(
            CardanoMsgAddressView,
            view_args=dict(msg_request=self.msg_request),
        )

    def _show_rejection(self, title, headline, lines):
        """Reject the request with a dire warning and plain detail lines."""
        from seedsigner.gui.screens.tx_review import RejectionDetailScreen

        self.run_screen(
            RejectionDetailScreen,
            title=title,
            status_headline=headline,
            extra_lines=[(line, GUIConstants.BODY_FONT_COLOR) for line in lines],
        )
