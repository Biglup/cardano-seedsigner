"""Transaction summary view with tokens and fee overview."""

from seedsigner.gui.screens import RET_CODE__BACK_BUTTON
from seedsigner.models.cardano_tx import CardanoParsedTx
from seedsigner.views.view import View, Destination, BackStackView

class CardanoTxSummaryView(View):
    """TX Summary - Shows detailed summary with tokens."""

    def __init__(self, parsed_tx: CardanoParsedTx = None):
        super().__init__()
        self.parsed_tx = parsed_tx

    def run(self):
        from seedsigner.gui.screens.tx_review import CardanoTxSummaryScreen
        from .sequential_review_view import CardanoTxSequentialReviewView
        from .sign_view import CardanoTxSignView

        selected_menu_num = self.run_screen(
            CardanoTxSummaryScreen,
            sending_amount=self.parsed_tx.sending_amount,
            sending_tokens=self.parsed_tx.sending_tokens,
            fee_amount=self.parsed_tx.fee,
            num_recipients=self.parsed_tx.num_recipients,
            change_amount=self.parsed_tx.change_amount,
            network=self.parsed_tx.network,
        )

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        if selected_menu_num == 0:
            return Destination(
                CardanoTxSequentialReviewView,
                view_args=dict(parsed_tx=self.parsed_tx, global_index=0)
            )
        elif selected_menu_num == 1:
            return Destination(
                CardanoTxSignView,
                view_args=dict(parsed_tx=self.parsed_tx)
            )
