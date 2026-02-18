"""Final confirmation screen before signing a Cardano transaction."""

from gettext import gettext as _

from seedsigner.gui.screens import RET_CODE__BACK_BUTTON
from seedsigner.models.cardano_tx import CardanoParsedTx

from seedsigner.views.view import View, Destination, BackStackView, MainMenuView


class CardanoTxSignView(View):
    """Sign Transaction - Final confirmation screen."""

    def __init__(self, parsed_tx: CardanoParsedTx):
        super().__init__()
        self.parsed_tx = parsed_tx

    def run(self):
        from seedsigner.gui.screens.tx_review import CardanoTxSignScreen

        selected_menu_num = self.run_screen(
            CardanoTxSignScreen,
            sending_amount=self.parsed_tx.sending_amount,
            fee_amount=self.parsed_tx.fee,
            network=self.parsed_tx.network,
        )

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        if selected_menu_num == 0:  # Cancel
            return Destination(MainMenuView)
        elif selected_menu_num == 1:  # Sign
            return Destination(MainMenuView, clear_history=True)
