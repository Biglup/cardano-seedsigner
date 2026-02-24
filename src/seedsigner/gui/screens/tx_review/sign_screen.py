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


@dataclass
class CardanoTxSignScreen(ButtonListScreen):
    """
    Final confirmation screen before signing.
    """
    sending_amount: int = 0
    fee_amount: int = 0

    def __post_init__(self):
        self.title = _("Sign Transaction")
        self.is_bottom_list = True
        self.button_data = [
            ButtonOption(_("Cancel"), FontAwesomeIconConstants.X),
            ButtonOption(_("Sign"), SeedSignerIconConstants.CHECK),
        ]

        super().__post_init__()

        cur_y = self.top_nav.height + GUIConstants.COMPONENT_PADDING * 2

        confirm_text = TextArea(
            text="Sign?",
            font_size=GUIConstants.get_top_nav_title_font_size() + 8,
            font_color=GUIConstants.BODY_FONT_COLOR,
            screen_x=0,
            screen_y=cur_y,
            is_text_centered=True,
            auto_line_break=False,
        )
        self.components.append(confirm_text)
        cur_y += confirm_text.height + GUIConstants.COMPONENT_PADDING * 2

        summary_lines = [
            _("Sending: {}").format(format_ada(self.sending_amount)),
            _("Fee: {}").format(format_ada(self.fee_amount)),
        ]

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
