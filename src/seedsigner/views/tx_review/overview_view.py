"""Transaction overview view with animated flow diagram."""

from gettext import gettext as _

from seedsigner.gui.screens import RET_CODE__BACK_BUTTON
from seedsigner.models.cardano_tx import CardanoParsedTx

from seedsigner.views.view import View, Destination, BackStackView, MainMenuView


class CardanoTxOverviewView(View):
    """
    TX Overview - First screen showing animated flow diagram.
    Shows: inputs -> recipients + fee + change with animated lines.
    Button: "Review details" -> enters sequential review
    """

    def __init__(self, parsed_tx: CardanoParsedTx = None):
        super().__init__()
        self.parsed_tx = parsed_tx

    def run(self):
        # Reject the transaction if the network doesn't match
        if self.parsed_tx.network_mismatch_error:
            from seedsigner.gui.components import GUIConstants, TextArea
            from seedsigner.gui.screens.screen import DireWarningScreen

            # Build the screen, then append colored TextAreas before displaying
            self.screen = DireWarningScreen(
                title=_("Network Mismatch"),
                status_headline=_("TX Rejected"),
            )

            # Find the y position after the last component (the headline)
            last = self.screen.components[-1]
            cur_y = last.screen_y + last.height + GUIConstants.COMPONENT_PADDING

            lines = [
                (_("Sign request targets:"), GUIConstants.BODY_FONT_COLOR),
                (self.parsed_tx.sign_request.network.name, GUIConstants.ACCENT_COLOR),
                (_("but tx body specifies:"), GUIConstants.BODY_FONT_COLOR),
                (self.parsed_tx.body.network_id.name, GUIConstants.ACCENT_COLOR),
            ]

            for text, color in lines:
                ta = TextArea(
                    text=text,
                    font_size=GUIConstants.get_body_font_size(),
                    font_color=color,
                    screen_x=0,
                    screen_y=cur_y,
                    is_text_centered=True,
                    auto_line_break=False,
                )
                self.screen.components.append(ta)
                cur_y += ta.height + 2

            self.screen.display()
            return Destination(MainMenuView, clear_history=True)

        from seedsigner.gui.screens.tx_review import CardanoTxOverviewScreen
        from .sequential_review_view import CardanoTxSequentialReviewView

        num_change = len(self.parsed_tx.verified_change_indices)

        selected_menu_num = self.run_screen(
            CardanoTxOverviewScreen,
            spend_amount=self.parsed_tx.sending_amount,
            num_inputs=len(self.parsed_tx.inputs),
            destination_addresses=self.parsed_tx.recipient_addresses,
            num_change_outputs=num_change,
            fee_amount=self.parsed_tx.fee,
            has_tokens=bool(self.parsed_tx.sending_tokens),
            network=self.parsed_tx.network,
        )

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        # "Review details" button pressed - enter sequential review
        return Destination(
            CardanoTxSequentialReviewView,
            view_args=dict(parsed_tx=self.parsed_tx, global_index=0)
        )
