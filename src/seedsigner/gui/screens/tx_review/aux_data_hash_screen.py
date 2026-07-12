"""Centered hash display screen for auxiliary data hash."""

from dataclasses import dataclass

from seedsigner.gui.components import GUIConstants, Fonts, SeedSignerIconConstants

from .sequential_base_screen import CardanoSequentialBaseScreen
from .utils import wrap_highlighted_line, draw_highlighted_line


@dataclass
class CardanoAuxDataHashScreen(CardanoSequentialBaseScreen):
    """Displays a single hex hash centered on screen with head/tail highlighting.

    When `badge_text` is set, an ownership badge is rendered below the hash:
    a green check icon + white text when `badge_own` is True, red text when
    False.

    `head_n` and `tail_n` override the head/tail highlight sizes; 0 falls
    back to `highlight_n` for that end.
    """

    hash_hex: str = ""
    highlight_n: int = 8
    head_n: int = 0
    tail_n: int = 0
    badge_text: str = ""
    badge_own: bool = False

    def __post_init__(self):
        """Prepare the wrapped display lines for the hash.

        Spaces are inserted at the highlight boundaries for visual
        separation, so the stored head/tail highlight counts are one larger
        than requested. Wrapped lines skip a leading space at line
        boundaries and record their global position in the display string.
        """
        from seedsigner.gui.renderer import Renderer
        renderer = Renderer.get_instance()

        side_button_width = 20
        content_margin = 8
        usable_width = renderer.canvas_width - 2 * side_button_width - 2 * content_margin
        self._hash_font = Fonts.get_font(GUIConstants.FIXED_WIDTH_FONT_NAME, 22)
        self._hash_accent_font = Fonts.get_font(GUIConstants.FIXED_WIDTH_EMPHASIS_FONT_NAME, 22)
        char_w = self._hash_font.getlength("A")
        chars_per_line = max(10, int(usable_width / char_w))

        hn_head = self.head_n if self.head_n > 0 else self.highlight_n
        hn_tail = self.tail_n if self.tail_n > 0 else self.highlight_n
        h = self.hash_hex
        if len(h) > hn_head + hn_tail:
            display = f"{h[:hn_head]} {h[hn_head:-hn_tail]} {h[-hn_tail:]}"
        else:
            display = h

        self._display_len = len(display)
        self._head_n = hn_head + 1
        self._tail_n = hn_tail + 1

        self._hash_lines = wrap_highlighted_line(display, chars_per_line)

        super().__post_init__()

    def _render_content(self):
        line_h = 28
        badge_h = line_h if self.badge_text else 0
        total_h = line_h * len(self._hash_lines) + badge_h
        visible_top = self.top_nav_height
        visible_bottom = self.canvas_height - self.bottom_bar_height
        y = visible_top + (visible_bottom - visible_top - total_h) // 2
        center_x = self.canvas_width // 2
        char_w = self._hash_font.getlength("A")

        for gpos, text in self._hash_lines:
            draw_highlighted_line(
                self.renderer.draw, text, gpos, self._display_len,
                self._head_n, self._tail_n, y, center_x, char_w,
                self._hash_font, self._hash_accent_font,
                GUIConstants.LABEL_FONT_COLOR, GUIConstants.ACCENT_TEXT_COLOR,
            )
            y += line_h

        if self.badge_text:
            label_font = Fonts.get_font(
                GUIConstants.get_body_font_name(), GUIConstants.get_body_font_size() + 2
            )
            y += 4

            if not self.badge_own:
                self.renderer.draw.text(
                    (center_x, y),
                    self.badge_text,
                    font=label_font,
                    fill="#CF6679",
                    anchor="mt",
                )
                return

            icon_font = Fonts.get_font(
                GUIConstants.ICON_FONT_NAME__SEEDSIGNER, 18, file_extension="otf"
            )
            icon_char = SeedSignerIconConstants.SUCCESS
            icon_bbox = icon_font.getbbox(icon_char)
            icon_w = icon_bbox[2] - icon_bbox[0]
            text_bbox = label_font.getbbox(self.badge_text)
            text_w = text_bbox[2] - text_bbox[0]
            gap = 6
            total_w = icon_w + gap + text_w
            start_x = center_x - total_w // 2

            self.renderer.draw.text(
                (start_x, y),
                icon_char,
                font=icon_font,
                fill=GUIConstants.SUCCESS_COLOR,
                anchor="lt",
            )
            self.renderer.draw.text(
                (start_x + icon_w + gap, y),
                self.badge_text,
                font=label_font,
                fill="#ffffff",
                anchor="lt",
            )
