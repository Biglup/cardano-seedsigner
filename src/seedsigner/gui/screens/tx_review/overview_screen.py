"""Shared overview screen for the transaction and message signing flows."""

from dataclasses import dataclass, field

from seedsigner.gui.components import GUIConstants, TextArea

from ..screen import ButtonListScreen


@dataclass
class CardanoOverviewScreen(ButtonListScreen):
    """Bottom-list overview with left-aligned labels above centered values.

    The view supplies the ordered ``rows`` of ``(label, value)`` pairs and
    decides which fields to include; this screen only lays them out. Row
    advance heights are fixed, measured from a "y" glyph so every row reserves
    descender space regardless of its actual text.
    """
    rows: list = field(default_factory=list)

    def __post_init__(self):
        self.is_bottom_list = True

        super().__post_init__()

        row_spacing = 6
        cur_y = 50

        label_h = TextArea(text="y", font_size=GUIConstants.get_body_font_size() - 2,
                           auto_line_break=False).height
        value_h = TextArea(text="y", font_size=GUIConstants.get_body_font_size(),
                           auto_line_break=False).height

        for label, value in self.rows:
            cur_y = self._add_row(cur_y, label, value, row_spacing,
                                  label_h, value_h)

    def _add_row(self, cur_y, label, value, spacing, label_h, value_h):
        """Append a left-aligned label and its centered value, returning the next y."""
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
