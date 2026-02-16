"""
Transaction summary screen showing overview with tokens and fee.
"""

from dataclasses import dataclass
from gettext import gettext as _

from seedsigner.gui.components import (
    GUIConstants,
    TextArea,
    SeedSignerIconConstants,
)

from ..screen import ButtonListScreen, ButtonOption
from .utils import format_ada


@dataclass
class CardanoTxSummaryScreen(ButtonListScreen):
    """
    Summary screen showing transaction overview.
    Kept for compatibility during transition to sequential navigation.
    """
    sending_amount: int = 0
    sending_tokens: dict = None
    fee_amount: int = 0
    num_recipients: int = 0
    change_amount: int = 0
    network: str = "mainnet"

    def __post_init__(self):
        self.title = _("Review Tx")
        self.is_bottom_list = True
        self.button_data = [
            ButtonOption(_("View Details")),
            ButtonOption(_("Sign Transaction"), SeedSignerIconConstants.CHECK),
        ]

        super().__post_init__()

        cur_y = self.top_nav.height + GUIConstants.COMPONENT_PADDING

        # Network badge (if testnet)
        if self.network != "mainnet":
            network_text = TextArea(
                text=_("TESTNET"),
                font_size=GUIConstants.BODY_FONT_MIN_SIZE,
                font_color=GUIConstants.WARNING_COLOR,
                screen_x=GUIConstants.EDGE_PADDING,
                screen_y=cur_y,
            )
            self.components.append(network_text)
            cur_y += network_text.height + GUIConstants.COMPONENT_PADDING

        # "SENDING" label
        sending_label = TextArea(
            text=_("SENDING"),
            font_size=GUIConstants.BODY_FONT_MIN_SIZE,
            font_color=GUIConstants.LABEL_FONT_COLOR,
            screen_x=0,
            screen_y=cur_y,
            is_text_centered=True,
            auto_line_break=False,
        )
        self.components.append(sending_label)
        cur_y += sending_label.height + int(GUIConstants.COMPONENT_PADDING / 2)

        # Main ADA amount
        ada_text = TextArea(
            text=format_ada(self.sending_amount),
            font_size=GUIConstants.get_top_nav_title_font_size() + 4,
            font_color=GUIConstants.BODY_FONT_COLOR,
            screen_x=0,
            screen_y=cur_y,
            is_text_centered=True,
            auto_line_break=False,
        )
        self.components.append(ada_text)
        cur_y += ada_text.height + GUIConstants.COMPONENT_PADDING

        # Tokens (if any)
        if self.sending_tokens:
            tokens_list = list(self.sending_tokens.items())[:3]
            for token_name, amount in tokens_list:
                token_text = f"+ {amount:,} {token_name}"
                token_area = TextArea(
                    text=token_text,
                    font_size=GUIConstants.get_body_font_size(),
                    font_color=GUIConstants.ACCENT_TEXT_COLOR,
                    screen_x=0,
                    screen_y=cur_y,
                    is_text_centered=True,
                    auto_line_break=False,
                )
                self.components.append(token_area)
                cur_y += token_area.height + 2

            if len(self.sending_tokens) > 3:
                more_text = TextArea(
                    text=_("+ {} more tokens").format(len(self.sending_tokens) - 3),
                    font_size=GUIConstants.BODY_FONT_MIN_SIZE,
                    font_color=GUIConstants.LABEL_FONT_COLOR,
                    screen_x=0,
                    screen_y=cur_y,
                    is_text_centered=True,
                    auto_line_break=False,
                )
                self.components.append(more_text)
                cur_y += more_text.height

            cur_y += GUIConstants.COMPONENT_PADDING

        # Recipients count
        if self.num_recipients == 1:
            recipients_text = _("To: 1 address")
        else:
            recipients_text = _("To: {} addresses").format(self.num_recipients)

        recipients_area = TextArea(
            text=recipients_text,
            font_size=GUIConstants.get_body_font_size(),
            font_color=GUIConstants.BODY_FONT_COLOR,
            screen_x=0,
            screen_y=cur_y,
            is_text_centered=True,
            auto_line_break=False,
        )
        self.components.append(recipients_area)
        cur_y += recipients_area.height + int(GUIConstants.COMPONENT_PADDING / 2)

        # Fee
        fee_text = _("Fee: {}").format(format_ada(self.fee_amount))
        fee_area = TextArea(
            text=fee_text,
            font_size=GUIConstants.get_body_font_size(),
            font_color=GUIConstants.LABEL_FONT_COLOR,
            screen_x=0,
            screen_y=cur_y,
            is_text_centered=True,
            auto_line_break=False,
        )
        self.components.append(fee_area)
