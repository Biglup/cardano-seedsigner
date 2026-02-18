"""
Sequential certificate screen for Cardano transaction review.

Renders certificate fields with the same visual patterns as the output screen:
- White labels for field names
- Blue highlighted values for certificate type and key values
- Address-style rendering for credentials and hashes
- Large accent values for ADA amounts
"""

from dataclasses import dataclass, field
from seedsigner.gui.components import GUIConstants, Fonts

from .sequential_base_screen import CardanoSequentialBaseScreen


@dataclass
class CardanoCertificateSequentialScreen(CardanoSequentialBaseScreen):
    """
    Certificate screen with scrollable fields.

    Accepts pre-built content as a list of tuples. Each entry is either a
    2-tuple (type, text) or a 4-tuple (type, text, head_n, tail_n) for
    hash_display entries with custom highlight ranges.

    Supported line types:
    - label: white left-aligned section label
    - value_highlight: big blue centered text (certificate type name, key values)
    - value_large: big accent centered text (ADA amounts)
    - hash_display: monospace hash with first/last N chars highlighted (auto-split)
    - value_text: regular centered text
    - spacer / spacer_small: vertical spacing
    """
    content: list = field(default_factory=list)
    highlight_n: int = 7

    def __post_init__(self):
        from seedsigner.gui.renderer import Renderer
        renderer = Renderer.get_instance()
        side_button_width = 20
        content_margin = 8
        usable_width = renderer.canvas_width - 2 * side_button_width - 2 * content_margin
        hash_font = Fonts.get_font(GUIConstants.FIXED_WIDTH_FONT_NAME, 22)
        char_w = hash_font.getlength("A")
        self._chars_per_line = max(10, int(usable_width / char_w))

        # Pre-compute fonts for wrapping
        max_w = renderer.canvas_width - 2 * side_button_width - 16
        vh_font = Fonts.get_font(
            GUIConstants.get_body_font_name(),
            GUIConstants.get_top_nav_title_font_size() + 2,
        )
        vt_font = Fonts.get_font(
            GUIConstants.get_body_font_name(), GUIConstants.get_body_font_size(),
        )

        # Expand entries into renderable _lines with position tracking
        self._lines = []
        self._hash_segments = []  # [(first_line_idx, display_len, head_n, tail_n), ...]

        for entry in self.content:
            line_type = entry[0]
            text = entry[1]

            if line_type in ("value_highlight", "value_highlight_warn", "value_highlight_yes", "value_highlight_no") and vh_font.getlength(text) > max_w:
                for wrapped in self._wrap_text(text, vh_font, max_w):
                    self._lines.append((line_type, wrapped))
            elif line_type == "value_text" and vt_font.getlength(text) > max_w:
                for wrapped in self._wrap_text(text, vt_font, max_w):
                    self._lines.append(("value_text", wrapped))
            elif line_type == "hash_display":
                display = text
                display_len = len(display)
                if len(entry) >= 4:
                    head_n = entry[2] + 1  # +1 for space after head
                    tail_n = entry[3] + 1  # +1 for space before tail
                else:
                    head_n = self.highlight_n + 1
                    tail_n = self.highlight_n + 1
                first_idx = len([t for t, _ in self._lines if t == "hash_line"])

                pos = 0
                line_gpos = []
                while pos < len(display):
                    if display[pos] == " ":
                        pos += 1
                    chunk = display[pos:pos + self._chars_per_line]
                    line_gpos.append(pos)
                    self._lines.append(("hash_line", chunk))
                    pos += len(chunk)

                self._hash_segments.append((first_idx, line_gpos, display_len, head_n, tail_n))
            else:
                self._lines.append((line_type, text))  # always 2-tuple in _lines

        super().__post_init__()

    def _calculate_scroll(self):
        self._label_height = 22
        self._value_highlight_height = 28
        self._value_large_height = 30
        self._hash_line_height = 28
        self._value_text_height = 20
        self._spacer_height = 16
        self._spacer_small_height = 8

        total = sum(self._line_height_for(t) for t, _ in self._lines)
        self.scroll_unit = 40
        self.max_scroll = max(0, total - self.content_height)

    def _line_height_for(self, line_type):
        heights = {
            "label": self._label_height,
            "value_highlight": self._value_highlight_height,
            "value_highlight_warn": self._value_highlight_height,
            "value_highlight_yes": self._value_highlight_height,
            "value_highlight_no": self._value_highlight_height,
            "value_large": self._value_large_height,
            "value_large_warn": self._value_large_height,
            "value_large_yes": self._value_large_height,
            "hash_line": self._hash_line_height,
            "value_text": self._value_text_height,
            "spacer": self._spacer_height,
            "spacer_small": self._spacer_small_height,
        }
        return heights.get(line_type, self._value_text_height)

    def _render_content(self):
        label_font = Fonts.get_font(
            GUIConstants.get_body_font_name(), GUIConstants.get_body_font_size() + 2
        )
        value_large_font = Fonts.get_font(
            GUIConstants.get_body_font_name(),
            GUIConstants.get_top_nav_title_font_size() + 4,
        )
        value_highlight_font = Fonts.get_font(
            GUIConstants.get_body_font_name(),
            GUIConstants.get_top_nav_title_font_size() + 2,
        )
        hash_font = Fonts.get_font(GUIConstants.FIXED_WIDTH_FONT_NAME, 22)
        hash_accent_font = Fonts.get_font(GUIConstants.FIXED_WIDTH_EMPHASIS_FONT_NAME, 22)
        value_text_font = Fonts.get_font(
            GUIConstants.get_body_font_name(), GUIConstants.get_body_font_size()
        )

        y = self.content_y - self.scroll_offset
        center_x = self.canvas_width // 2
        hash_line_idx = 0

        for line_type, text in self._lines:
            h = self._line_height_for(line_type)

            if y + h > self.content_y and y < self.content_y + self.content_height:
                if line_type == "label":
                    self.renderer.draw.text(
                        (self.content_x + 4, y),
                        text,
                        font=label_font,
                        fill="#ffffff",
                        anchor="lt",
                    )
                elif line_type in ("value_highlight", "value_highlight_warn", "value_highlight_yes", "value_highlight_no"):
                    _VH_COLORS = {
                        "value_highlight_warn": "#CF6679",
                        "value_highlight_yes": "#66BB6A",
                        "value_highlight_no": "#CF6679",
                    }
                    color = _VH_COLORS.get(line_type, GUIConstants.ACCENT_TEXT_COLOR)
                    self.renderer.draw.text(
                        (center_x, y + h // 2),
                        text,
                        font=value_highlight_font,
                        fill=color,
                        anchor="mm",
                    )
                elif line_type in ("value_large", "value_large_warn", "value_large_yes"):
                    _VL_COLORS = {
                        "value_large_warn": "#CF6679",
                        "value_large_yes": "#66BB6A",
                    }
                    color = _VL_COLORS.get(line_type, GUIConstants.ACCENT_TEXT_COLOR)
                    self.renderer.draw.text(
                        (center_x, y + 2),
                        text,
                        font=value_large_font,
                        fill=color,
                        anchor="mt",
                    )
                elif line_type == "hash_line":
                    # Find which segment this hash_line belongs to
                    seg = self._find_segment(hash_line_idx)
                    if seg:
                        first_idx, line_gpos, display_len, head_n, tail_n = seg
                        local_idx = hash_line_idx - first_idx
                        gpos = line_gpos[local_idx]
                    else:
                        gpos = 0
                        display_len = len(text)
                        head_n = self.highlight_n
                        tail_n = self.highlight_n

                    char_w = hash_font.getlength("A")
                    line_w = char_w * len(text)
                    x_cursor = int(center_x - line_w // 2)

                    segments = []
                    seg_start = 0
                    for ci in range(len(text)):
                        gp = gpos + ci
                        is_accent = gp < head_n or gp >= display_len - tail_n
                        if ci == 0:
                            cur_accent = is_accent
                        if is_accent != cur_accent:
                            segments.append((text[seg_start:ci], cur_accent))
                            seg_start = ci
                            cur_accent = is_accent
                    segments.append((text[seg_start:], cur_accent))

                    for seg_text, is_accent in segments:
                        font = hash_accent_font if is_accent else hash_font
                        color = GUIConstants.ACCENT_TEXT_COLOR if is_accent else GUIConstants.LABEL_FONT_COLOR
                        self.renderer.draw.text(
                            (x_cursor, y),
                            seg_text,
                            font=font,
                            fill=color,
                            anchor="lt",
                        )
                        x_cursor += int(char_w * len(seg_text))
                elif line_type == "value_text":
                    self.renderer.draw.text(
                        (center_x, y),
                        text,
                        font=value_text_font,
                        fill=GUIConstants.BODY_FONT_COLOR,
                        anchor="mt",
                    )

            if line_type == "hash_line":
                hash_line_idx += 1
            y += h

    @staticmethod
    def _wrap_text(text, font, max_w):
        """Break text into lines that fit within max_w.

        Splits on spaces when possible; falls back to character-level
        breaking for long tokens like URLs.
        """
        words = text.split()
        lines = []
        current = ""
        for word in words:
            test = f"{current} {word}" if current else word
            if font.getlength(test) <= max_w:
                current = test
                continue
            if current:
                lines.append(current)
            # Break the word itself if it exceeds max_w
            if font.getlength(word) > max_w:
                chunk = ""
                for ch in word:
                    if font.getlength(chunk + ch) > max_w and chunk:
                        lines.append(chunk)
                        chunk = ch
                    else:
                        chunk += ch
                current = chunk
            else:
                current = word
        if current:
            lines.append(current)
        return lines

    def _find_segment(self, hash_line_idx):
        """Find the hash_segment that contains this hash_line index."""
        for seg in self._hash_segments:
            first_idx, line_gpos, display_len, head_n, tail_n = seg
            if first_idx <= hash_line_idx < first_idx + len(line_gpos):
                return seg
        return None
