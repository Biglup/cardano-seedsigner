"""
Output detail screen showing a single transaction output.
"""

from dataclasses import dataclass
from gettext import gettext as _

from seedsigner.gui.components import (
    GUIConstants,
    TextArea,
)

from ..screen import ButtonListScreen, ButtonOption
from .utils import format_ada


@dataclass
class CardanoTxOutputScreen(ButtonListScreen):
    """
    Screen showing details of a single output.
    """
    output_num: int = 1
    total_outputs: int = 1
    address: str = ""
    amount: int = 0
    tokens: dict = None
    is_change: bool = False

    def __post_init__(self):
        self.title = _("Output {} of {}").format(self.output_num, self.total_outputs)
        self.is_bottom_list = True
        self.button_data = [ButtonOption(_("Done"))]

        super().__post_init__()

        cur_y = self.top_nav.height + GUIConstants.COMPONENT_PADDING

        if self.is_change:
            change_badge = TextArea(
                text=_("YOUR CHANGE"),
                font_size=GUIConstants.BODY_FONT_MIN_SIZE,
                font_color=GUIConstants.ACCENT_TEXT_COLOR,
                background_color="#003300",
                screen_x=0,
                screen_y=cur_y,
                is_text_centered=True,
                auto_line_break=False,
            )
            self.components.append(change_badge)
            cur_y += change_badge.height + GUIConstants.COMPONENT_PADDING

        ada_text = TextArea(
            text=format_ada(self.amount),
            font_size=GUIConstants.get_top_nav_title_font_size(),
            font_color=GUIConstants.BODY_FONT_COLOR,
            screen_x=0,
            screen_y=cur_y,
            is_text_centered=True,
            auto_line_break=False,
        )
        self.components.append(ada_text)
        cur_y += ada_text.height + GUIConstants.COMPONENT_PADDING

        addr_display = self._format_address_multiline(self.address)
        for line in addr_display:
            addr_line = TextArea(
                text=line,
                font_size=GUIConstants.BODY_FONT_MIN_SIZE,
                font_color=GUIConstants.LABEL_FONT_COLOR,
                screen_x=0,
                screen_y=cur_y,
                is_text_centered=True,
                auto_line_break=False,
            )
            self.components.append(addr_line)
            cur_y += addr_line.height + 2

        cur_y += GUIConstants.COMPONENT_PADDING

        if self.tokens:
            tokens_label = TextArea(
                text=_("Tokens ({})").format(len(self.tokens)),
                font_size=GUIConstants.BODY_FONT_MIN_SIZE,
                font_color=GUIConstants.LABEL_FONT_COLOR,
                screen_x=GUIConstants.EDGE_PADDING,
                screen_y=cur_y,
                auto_line_break=False,
            )
            self.components.append(tokens_label)
            cur_y += tokens_label.height + 4

            tokens_list = list(self.tokens.items())[:4]
            for token_name, amount in tokens_list:
                token_text = f"{token_name}: {amount:,}"
                token_area = TextArea(
                    text=token_text,
                    font_size=GUIConstants.get_body_font_size(),
                    font_color=GUIConstants.ACCENT_TEXT_COLOR,
                    screen_x=GUIConstants.EDGE_PADDING * 2,
                    screen_y=cur_y,
                    auto_line_break=False,
                )
                self.components.append(token_area)
                cur_y += token_area.height + 2

    def _format_address_multiline(self, address: str, chars_per_line: int = 28) -> list:
        lines = []
        for i in range(0, len(address), chars_per_line):
            lines.append(address[i:i + chars_per_line])
        if len(lines) > 3:
            lines = lines[:2] + ["..."]
        return lines
