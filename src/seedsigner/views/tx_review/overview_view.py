"""Transaction overview view with summary fields."""

from gettext import gettext as _

from seedsigner.gui.components import GUIConstants
from seedsigner.gui.screens import RET_CODE__BACK_BUTTON
from seedsigner.gui.screens.screen import ButtonOption
from seedsigner.helpers.cardano_utils import sanitize_origin
from seedsigner.models.cardano_tx import CardanoParsedTx

from seedsigner.views.view import View, Destination, BackStackView, MainMenuView


class CardanoTxOverviewView(View):
    """TX Overview: summary of key transaction fields."""

    REVIEW = ButtonOption("Review details")

    def __init__(self, parsed_tx: CardanoParsedTx = None):
        super().__init__()
        self.parsed_tx = parsed_tx

    def run(self):
        """Show the overview, or reject the transaction on a network mismatch.

        A mismatch between the sign request's network and the transaction
        body's network id rejects the transaction outright, showing the
        targeted vs. specified networks as colored detail lines under the
        warning headline.
        """
        if self.parsed_tx.network_mismatch_error:
            from seedsigner.gui.screens.tx_review import RejectionDetailScreen

            self.run_screen(
                RejectionDetailScreen,
                title=_("Network Mismatch"),
                status_headline=_("TX Rejected"),
                extra_lines=[
                    (_("Sign request targets:"), GUIConstants.BODY_FONT_COLOR),
                    (self.parsed_tx.sign_request.network.name, GUIConstants.ACCENT_COLOR),
                    (_("but tx body specifies:"), GUIConstants.BODY_FONT_COLOR),
                    (self.parsed_tx.body.network_id.name, GUIConstants.ACCENT_COLOR),
                ],
            )
            return Destination(MainMenuView, clear_history=True)

        from seedsigner.gui.screens.tx_review import CardanoOverviewScreen, format_ada
        from .sequential_review_view import CardanoTxSequentialReviewView

        if self.parsed_tx.has_unverified_outputs and not self.controller.cardano_unverified_warning_acknowledged:
            from seedsigner.gui.screens.screen import WarningScreen

            if self.parsed_tx.has_failed_change_claims:
                status_headline = _("Cannot Verify Change")
                text = _("The declared change is not this wallet's. Confirm the destinations in your host wallet.")
            else:
                status_headline = _("All Amounts Leaving")
                text = _("No outputs belong to this wallet. Confirm the destinations in your host wallet.")

            selected_menu_num = self.run_screen(
                WarningScreen,
                title=_("Unverified Outputs"),
                status_headline=status_headline,
                text=text,
            )
            if selected_menu_num == RET_CODE__BACK_BUTTON:
                return Destination(BackStackView)
            self.controller.cardano_unverified_warning_acknowledged = True

        origin = sanitize_origin(self.parsed_tx.sign_request.origin)

        rows = []
        if origin:
            rows.append(("Origin:", origin))
        if self.parsed_tx.has_unverified_outputs:
            rows.append(("Outputs:", str(len(self.parsed_tx.outputs))))
        else:
            rows.append(("Sending:", format_ada(self.parsed_tx.sending_amount)))
        rows += [
            ("Fee:", format_ada(self.parsed_tx.fee)),
            ("Network:", self.parsed_tx.network.name.capitalize()),
        ]

        selected_menu_num = self.run_screen(
            CardanoOverviewScreen,
            title=_("Sign Transaction"),
            button_data=[self.REVIEW],
            rows=rows,
        )

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        return Destination(
            CardanoTxSequentialReviewView,
            view_args=dict(parsed_tx=self.parsed_tx, global_index=0)
        )
