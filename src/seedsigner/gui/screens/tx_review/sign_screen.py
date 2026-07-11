"""
Final confirmation screen before signing a Cardano transaction.
"""

from dataclasses import dataclass
from gettext import gettext as _

from seedsigner.gui.components import (
    GUIConstants,
    TextArea,
    FontAwesomeIconConstants,
    SeedSignerIconConstants,
)

from ..screen import ButtonListScreen, ButtonOption
from .utils import format_ada


_MAX_OUTPUT_LINES = 2


@dataclass
class CardanoTxSignScreen(ButtonListScreen):
    """
    Final confirmation screen before signing.

    When no output could be verified as change (`output_amounts` provided),
    the single "Sending" total is replaced by per-output amounts + fee: the
    total would be a net the device cannot prove, while each output amount is
    provable directly from the transaction body.
    """
    sending_amount: int = 0
    fee_amount: int = 0
    output_amounts: list = None

    def __post_init__(self):
        self.title = _("Sign Transaction")
        self.is_bottom_list = True
        self.button_data = [
            ButtonOption(_("Cancel"), FontAwesomeIconConstants.X),
            ButtonOption(_("Sign"), SeedSignerIconConstants.CHECK),
        ]

        super().__post_init__()

        per_output_mode = self.output_amounts is not None
        heading_pad = (GUIConstants.COMPONENT_PADDING if per_output_mode
                       else GUIConstants.COMPONENT_PADDING * 2)
        cur_y = self.top_nav.height + heading_pad

        confirm_text = TextArea(
            text="Sign?",
            font_size=GUIConstants.get_top_nav_title_font_size() + (2 if per_output_mode else 8),
            font_color=GUIConstants.BODY_FONT_COLOR,
            screen_x=0,
            screen_y=cur_y,
            is_text_centered=True,
            auto_line_break=False,
        )
        self.components.append(confirm_text)
        cur_y += confirm_text.height + heading_pad

        if per_output_mode:
            if len(self.output_amounts) <= _MAX_OUTPUT_LINES + 1:
                shown = self.output_amounts
            else:
                shown = self.output_amounts[:_MAX_OUTPUT_LINES]
            summary_lines = [
                _("Output {}: {}").format(i + 1, format_ada(amount))
                for i, amount in enumerate(shown)
            ]
            hidden = self.output_amounts[len(shown):]
            if hidden:
                summary_lines.append(
                    _("+{} more: {}").format(len(hidden), format_ada(sum(hidden))))
        else:
            summary_lines = [
                _("Sending: {}").format(format_ada(self.sending_amount)),
            ]
        summary_lines.append(_("Fee: {}").format(format_ada(self.fee_amount)))

        for line in summary_lines:
            line_area = TextArea(
                text=line,
                font_size=GUIConstants.get_body_font_size(),
                font_color=GUIConstants.BODY_FONT_COLOR,
                screen_x=0,
                screen_y=cur_y,
                is_text_centered=True,
                auto_line_break=False,
            )
            self.components.append(line_area)
            cur_y += line_area.height + 4
