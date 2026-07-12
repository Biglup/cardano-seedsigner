"""Final confirmation screen before signing a Cardano transaction, and the
animated QR view that transmits the resulting witness set back to the host."""

import logging
from gettext import gettext as _

from seedsigner.gui.screens import RET_CODE__BACK_BUTTON
from seedsigner.gui.screens.screen import ButtonOption
from seedsigner.models.cardano_tx import CardanoParsedTx, CardanoTxSignResponse
from seedsigner.models.settings import SettingsConstants

from seedsigner.views.view import View, Destination, BackStackView, MainMenuView


logger = logging.getLogger(__name__)


class CardanoTxSignView(View):
    """Sign Transaction - Final confirmation screen."""

    def __init__(self, parsed_tx: CardanoParsedTx):
        super().__init__()
        self.parsed_tx = parsed_tx

    def run(self):
        """Confirm and sign the reviewed transaction.

        The request signed is taken from parsed_tx so it is exactly the
        transaction the user reviewed, not a controller field that a later
        scan could have overwritten.

        The selected seed must sign at least one required signer. An empty
        match means the wrong seed was chosen (it would emit an empty
        witness set that looks like success). A partial match is valid
        (cross-device multisig) and proceeds.

        The confirmation screen returns 0 for Cancel and 1 for Sign.
        """
        from seedsigner.gui.screens.tx_review import CardanoTxSignScreen
        from seedsigner.gui.screens.screen import WarningScreen
        from seedsigner.helpers.cardano_signing import (
            matching_signing_paths,
            build_tx_sign_response,
        )

        seed = self.controller.cardano_seed
        request = self.parsed_tx.sign_request

        if seed is not None and request is not None and not matching_signing_paths(request, seed):
            self.run_screen(
                WarningScreen,
                title=_("Cannot Sign"),
                status_headline=_("Wrong Seed"),
                text=_("This seed does not sign any of the inputs in this transaction."),
                show_back_button=False,
                button_data=[ButtonOption("OK")],
            )
            return Destination(MainMenuView, clear_history=True)

        selected_menu_num = self.run_screen(
            CardanoTxSignScreen,
            sending_amount=self.parsed_tx.sending_amount,
            fee_amount=self.parsed_tx.fee,
            output_amounts=(self.parsed_tx.output_amounts
                            if self.parsed_tx.has_unverified_outputs else None),
        )

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        if selected_menu_num == 0:
            return Destination(MainMenuView, clear_history=True)

        elif selected_menu_num == 1:
            if seed is None or request is None:
                return Destination(MainMenuView, clear_history=True)
            try:
                response = build_tx_sign_response(seed, request)
            except Exception as e:
                logger.info(repr(e), exc_info=True)
                self.run_screen(
                    WarningScreen,
                    title=_("Cannot Sign"),
                    status_headline=_("Rejected"),
                    text=_("The transaction could not be signed with this seed."),
                    show_back_button=False,
                    button_data=[ButtonOption("OK")],
                )
                return Destination(MainMenuView, clear_history=True)
            return Destination(
                CardanoTxSignedQRView,
                view_args=dict(response=response),
            )


class CardanoTxSignedQRView(View):
    """Transmit the signed witness set back to the host as an animated QR."""

    def __init__(self, response: CardanoTxSignResponse):
        super().__init__()
        from seedsigner.models.encode_qr import CardanoTxSigResponseQrEncoder

        self.qr_encoder = CardanoTxSigResponseQrEncoder(
            response=response,
            qr_density=self.settings.get_value(SettingsConstants.SETTING__QR_DENSITY),
        )

    def run(self):
        """Display the witness-set QR, clear the pending request, and exit to the menu."""
        from seedsigner.gui.screens.screen import QRDisplayScreen

        self.run_screen(QRDisplayScreen, qr_encoder=self.qr_encoder)

        self.controller.cardano_tx_sign_request = None
        self.controller.cardano_seed = None
        return Destination(MainMenuView, clear_history=True)
