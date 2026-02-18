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
    - ``** text``  → emphasis (accent text color)
    - ``^^ text``  → big centered value (accent text color, large font)
    - plain text   → body font
    """
    content_lines: List[str] = None

    BIG_LINE_HEIGHT = 36

    def __post_init__(self):
        if self.content_lines is None:
            self.content_lines = []
        self.line_height = 18
        super().__post_init__()

    def _line_height_for_content(self, line):
        if line.startswith("^^"):
            return self.BIG_LINE_HEIGHT
        return self.line_height

    def _calculate_scroll(self):
        self.scroll_unit = self.line_height * 2
        total = sum(self._line_height_for_content(l) for l in self.content_lines)
        self.max_scroll = max(0, total - self.content_height)

    def _render_content(self):
        if not self.content_lines:
            return

        font = Fonts.get_font(
            GUIConstants.get_body_font_name(), GUIConstants.BODY_FONT_MIN_SIZE
        )
        big_font = Fonts.get_font(
            GUIConstants.get_body_font_name(),
            GUIConstants.get_top_nav_title_font_size() + 4,
        )
        center_x = self.canvas_width // 2
        total_h = sum(self._line_height_for_content(l) for l in self.content_lines)
        if total_h <= self.content_height:
            y = (self.canvas_height - total_h) // 2
        else:
            y = self.content_y - self.scroll_offset

        for line in self.content_lines:
            h = self._line_height_for_content(line)
            if y + h > self.content_y and y < self.content_y + self.content_height:
                color = GUIConstants.BODY_FONT_COLOR
                if line.startswith("^^"):
                    line = line[2:].strip()
                    self.renderer.draw.text(
                        (center_x, y + h // 2),
                        line,
                        font=big_font,
                        fill=GUIConstants.ACCENT_TEXT_COLOR,
                        anchor="mm",
                    )
                else:
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
            y += h
