"""Centered hash display screen for auxiliary data hash."""

from dataclasses import dataclass

from seedsigner.gui.components import GUIConstants, Fonts, SeedSignerIconConstants

from .sequential_base_screen import CardanoSequentialBaseScreen


@dataclass
class CardanoAuxDataHashScreen(CardanoSequentialBaseScreen):
    """Displays a single hex hash centered on screen with head/tail highlighting.

    When `badge_text` is set, an ownership badge is rendered below the hash:
    a green check icon + white text when `badge_own` is True, red text when
    False.
    """

    hash_hex: str = ""
    highlight_n: int = 8
    head_n: int = 0  # Override head highlight size (0 = use highlight_n)
    tail_n: int = 0  # Override tail highlight size (0 = use highlight_n)
    badge_text: str = ""
    badge_own: bool = False

    def __post_init__(self):
        from seedsigner.gui.renderer import Renderer
        renderer = Renderer.get_instance()

        side_button_width = 20
        content_margin = 8
        usable_width = renderer.canvas_width - 2 * side_button_width - 2 * content_margin
        self._hash_font = Fonts.get_font(GUIConstants.FIXED_WIDTH_FONT_NAME, 22)
        self._hash_accent_font = Fonts.get_font(GUIConstants.FIXED_WIDTH_EMPHASIS_FONT_NAME, 22)
        char_w = self._hash_font.getlength("A")
        chars_per_line = max(10, int(usable_width / char_w))

        # Insert spaces at highlight boundaries for visual separation
        hn_head = self.head_n if self.head_n > 0 else self.highlight_n
        hn_tail = self.tail_n if self.tail_n > 0 else self.highlight_n
        h = self.hash_hex
        if len(h) > hn_head + hn_tail:
            display = f"{h[:hn_head]} {h[hn_head:-hn_tail]} {h[-hn_tail:]}"
        else:
            display = h

        self._display_len = len(display)
        self._head_n = hn_head + 1  # +1 for space
        self._tail_n = hn_tail + 1

        # Split into lines, skipping leading spaces
        self._hash_lines = []
        pos = 0
        while pos < len(display):
            if display[pos] == " ":
                pos += 1
            chunk = display[pos:pos + chars_per_line]
            self._hash_lines.append((pos, chunk))
            pos += len(chunk)

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
            line_w = char_w * len(text)
            x_cursor = int(center_x - line_w // 2)

            # Build segments with accent boundaries
            segments = []
            seg_start = 0
            for ci in range(len(text)):
                gp = gpos + ci
                is_accent = gp < self._head_n or gp >= self._display_len - self._tail_n
                if ci == 0:
                    cur_accent = is_accent
                if is_accent != cur_accent:
                    segments.append((text[seg_start:ci], cur_accent))
                    seg_start = ci
                    cur_accent = is_accent
            segments.append((text[seg_start:], cur_accent))

            for seg_text, is_accent in segments:
                font = self._hash_accent_font if is_accent else self._hash_font
                color = GUIConstants.ACCENT_TEXT_COLOR if is_accent else GUIConstants.LABEL_FONT_COLOR
                self.renderer.draw.text(
                    (x_cursor, y),
                    seg_text,
                    font=font,
                    fill=color,
                    anchor="lt",
                )
                x_cursor += int(char_w * len(seg_text))

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
