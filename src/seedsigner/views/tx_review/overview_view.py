"""Transaction overview view with summary fields."""

from gettext import gettext as _

from seedsigner.gui.screens import RET_CODE__BACK_BUTTON
from seedsigner.gui.screens.screen import ButtonOption
from seedsigner.models.cardano_tx import CardanoParsedTx

from seedsigner.views.view import View, Destination, BackStackView, MainMenuView


class CardanoTxOverviewView(View):
    """TX Overview — summary of key transaction fields."""

    REVIEW = ButtonOption("Review details")

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

        from seedsigner.gui.screens.tx_review.utils import format_ada
        from .sequential_review_view import CardanoTxSequentialReviewView

        if self.parsed_tx.has_unverified_outputs and not self.parsed_tx.unverified_warning_acknowledged:
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
            self.parsed_tx.unverified_warning_acknowledged = True

        origin = _sanitize_origin(self.parsed_tx.sign_request.origin)

        selected_menu_num = self.run_screen(
            _TxOverviewScreen,
            sending=format_ada(self.parsed_tx.sending_amount),
            fee=format_ada(self.parsed_tx.fee),
            network=self.parsed_tx.network.name.capitalize(),
            origin=origin,
            unverified_outputs=self.parsed_tx.has_unverified_outputs,
            num_outputs=len(self.parsed_tx.outputs),
        )

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        # "Review details" button pressed - enter sequential review
        return Destination(
            CardanoTxSequentialReviewView,
            view_args=dict(parsed_tx=self.parsed_tx, global_index=0)
        )


def _sanitize_origin(origin):
    """Strip non-printable chars and cap at 20 characters."""
    if not origin:
        return origin
    cleaned = "".join(c for c in origin if c.isprintable())
    if len(cleaned) > 20:
        cleaned = cleaned[:20] + "..."
    return cleaned or None


from dataclasses import dataclass

from seedsigner.gui.screens import ButtonListScreen
from seedsigner.gui.components import GUIConstants, TextArea


@dataclass
class _TxOverviewScreen(ButtonListScreen):
    """TX overview with left-aligned label/value rows.

    When no output could be verified as this wallet's change, the single
    "Sending" figure is a net the device cannot prove, so it is replaced by
    the output count (per-output amounts follow in the sequential review and
    on the sign confirmation).
    """
    sending: str = ""
    fee: str = ""
    network: str = ""
    origin: str = None
    unverified_outputs: bool = False
    num_outputs: int = 0

    def __post_init__(self):
        self.title = _("Sign Transaction")
        self.is_bottom_list = True
        self.button_data = [CardanoTxOverviewView.REVIEW]

        super().__post_init__()

        rows = []
        if self.origin:
            rows.append(("Origin:", self.origin))
        if self.unverified_outputs:
            rows.append(("Outputs:", str(self.num_outputs)))
        else:
            rows.append(("Sending:", self.sending))
        rows += [
            ("Fee:", self.fee),
            ("Network:", self.network),
        ]

        row_spacing = 6
        cur_y = 50

        # Fixed row advance heights (use "y" to include descender space)
        label_h = TextArea(text="y", font_size=GUIConstants.get_body_font_size() - 2,
                           auto_line_break=False).height
        value_h = TextArea(text="y", font_size=GUIConstants.get_body_font_size(),
                           auto_line_break=False).height

        for label, value in rows:
            cur_y = self._add_row(cur_y, label, value, row_spacing,
                                  label_h, value_h)

    def _add_row(self, cur_y, label, value, spacing, label_h, value_h):
        label_area = TextArea(
            text=label,
            font_size=GUIConstants.get_body_font_size() - 2,
            font_color=GUIConstants.BODY_FONT_COLOR,
            screen_x=GUIConstants.EDGE_PADDING,
            screen_y=cur_y,
            is_text_centered=False,
            auto_line_break=False,
        )
        self.components.append(label_area)
        cur_y += label_h + 4

        value_area = TextArea(
            text=value,
            font_size=GUIConstants.get_body_font_size(),
            font_color=GUIConstants.ACCENT_TEXT_COLOR,
            screen_x=0,
            screen_y=cur_y,
            is_text_centered=True,
            auto_line_break=False,
        )
        self.components.append(value_area)
        cur_y += value_h + spacing
        return cur_y
