"""
Generic sequential screen that renders content_lines with markdown-like formatting.
"""

from dataclasses import dataclass
from typing import List

from seedsigner.gui.components import GUIConstants, Fonts

from .sequential_base_screen import CardanoSequentialBaseScreen


@dataclass
class CardanoTxSequentialScreen(CardanoSequentialBaseScreen):
    """
    Renders a list of text lines with simple markup:
    - ``### text`` → header (accent color, larger font)
    - ``** text`` → emphasis (accent text color)
    - plain text  → body font
    """
    content_lines: List[str] = None

    def __post_init__(self):
        if self.content_lines is None:
            self.content_lines = []
        self.line_height = 18
        super().__post_init__()

    def _calculate_scroll(self):
        self.scroll_unit = self.line_height * 2
        self.max_scroll = max(
            0, len(self.content_lines) * self.line_height - self.content_height
        )

    def _render_content(self):
        if not self.content_lines:
            return

        font = Fonts.get_font(
            GUIConstants.get_body_font_name(), GUIConstants.BODY_FONT_MIN_SIZE
        )
        y = self.content_y - self.scroll_offset

        for line in self.content_lines:
            if y >= self.content_y - self.line_height and y < self.content_y + self.content_height:
                color = GUIConstants.BODY_FONT_COLOR
                if line.startswith("###"):
                    line = line[3:].strip()
                    color = GUIConstants.ACCENT_COLOR
                    font = Fonts.get_font(
                        GUIConstants.get_body_font_name(), GUIConstants.get_body_font_size()
                    )
                elif line.startswith("**"):
                    line = line[2:].strip()
                    color = GUIConstants.ACCENT_TEXT_COLOR
                else:
                    font = Fonts.get_font(
                        GUIConstants.get_body_font_name(), GUIConstants.BODY_FONT_MIN_SIZE
                    )

                self.renderer.draw.text(
                    (self.content_x + 4, y),
                    line,
                    font=font,
                    fill=color,
                    anchor="lt",
                )
            y += self.line_height
