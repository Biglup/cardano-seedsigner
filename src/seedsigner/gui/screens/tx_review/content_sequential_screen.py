"""
Sequential labelled-content screen for Cardano review flows.

Renders a scrollable list of typed content lines using the same visual
patterns as the output screen: white labels for field names, blue
highlighted values, address-style hashes, and large accent amounts. Used
by the certificate, withdrawal, voting, proposal, mint and signing-key
review steps as well as the whole CIP-8 message signing flow.
"""

from dataclasses import dataclass, field
from seedsigner.gui.components import GUIConstants, Fonts, SeedSignerIconConstants

from .sequential_base_screen import CardanoSequentialBaseScreen
from .utils import CONTENT_LINE_TYPES

_FOREIGN_COLOR = "#CF6679"

_VH_COLORS = {
    "value_highlight_warn": "#CF6679",
    "value_highlight_yes": "#66BB6A",
    "value_highlight_no": "#CF6679",
}

_VL_COLORS = {
    "value_large_warn": "#CF6679",
    "value_large_yes": "#66BB6A",
}


@dataclass
class CardanoContentSequentialScreen(CardanoSequentialBaseScreen):
    """
    Generic labelled-content screen with scrollable fields.

    Accepts pre-built content as a list of tuples. Each entry is either a
    2-tuple (type, text) or a 4-tuple (type, text, head_n, tail_n) for
    hash_display entries with custom highlight ranges. Build entries with
    the ``Line`` constructors in ``utils`` rather than hand-written tuples.

    Supported line types:
    - label: white left-aligned section label
    - label_own / label_foreign: like label, but the ownership tag word
      ("Own" / "Foreign" / "Unknown") inside the text is drawn green/red
    - value_highlight: big blue centered text (certificate type name, key values)
    - value_large: big accent centered text (ADA amounts)
    - hash_display: monospace hash with first/last N chars highlighted (auto-split)
    - mono_text: left-aligned monospace text (JSON, hex dumps)
    - value_text: regular centered text
    - verified: green check icon + white text, centered (ownership badge)
    - foreign: red centered text (negative ownership badge)
    - hero_fields: 2-tuple (type, fields) where fields is a list of
      (label, label_suffix, value); each field is a small centered label
      (suffix in accent color) over a large fixed-width value, and the whole
      stack is centered vertically in the viewport
    - spacer / spacer_small: vertical spacing
    """
    content: list = field(default_factory=list)
    highlight_n: int = 7

    def __post_init__(self):
        """Expand content entries into renderable ``_lines`` with position tracking.

        Each entry's line type is validated against ``CONTENT_LINE_TYPES``
        first, so a misspelled or unknown type is a hard error here rather
        than a line the renderer silently ignores.

        ``_hash_segments`` records, per hash_display entry, the index of its
        first hash_line, the global display position of each wrapped line,
        the display length and the head/tail highlight sizes. A hero_fields
        entry keeps its field list; every remaining entry lands in
        ``_lines`` as a 2-tuple of (line type, text).

        Head and tail highlight sizes are stored one character larger than
        requested to cover the separator space after the head and before
        the tail.
        """
        for entry in self.content:
            if entry[0] not in CONTENT_LINE_TYPES:
                raise ValueError(f"unknown content line type: {entry[0]!r}")

        from seedsigner.gui.renderer import Renderer
        renderer = Renderer.get_instance()
        side_button_width = 20
        content_margin = 8
        usable_width = renderer.canvas_width - 2 * side_button_width - 2 * content_margin
        hash_font = Fonts.get_font(GUIConstants.FIXED_WIDTH_FONT_NAME, 22)
        char_w = hash_font.getlength("A")
        self._chars_per_line = max(10, int(usable_width / char_w))

        max_w = renderer.canvas_width - 2 * side_button_width - 16
        vh_font = Fonts.get_font(
            GUIConstants.get_body_font_name(),
            GUIConstants.get_top_nav_title_font_size() + 2,
        )
        vt_font = Fonts.get_font(
            GUIConstants.get_body_font_name(), GUIConstants.get_body_font_size(),
        )

        self._lines = []
        self._hash_segments = []

        for entry in self.content:
            line_type = entry[0]
            text = entry[1]

            if line_type == "hero_fields":
                fields = []
                for field_label, label_suffix, field_value in entry[1]:
                    font_size = 24
                    font = Fonts.get_font(GUIConstants.FIXED_WIDTH_FONT_NAME, font_size)
                    while font_size > 16 and font.getlength(field_value) > max_w:
                        font_size -= 1
                        font = Fonts.get_font(GUIConstants.FIXED_WIDTH_FONT_NAME, font_size)
                    if font.getlength(field_value) <= max_w:
                        value_lines = [field_value]
                    else:
                        value_lines = self._wrap_path(field_value, font, max_w)
                    fields.append((field_label, label_suffix, value_lines, font_size))
                self._lines.append(("hero_fields", fields))
            elif line_type in ("value_highlight", "value_highlight_warn", "value_highlight_yes", "value_highlight_no") and vh_font.getlength(text) > max_w:
                for wrapped in self._wrap_text(text, vh_font, max_w):
                    self._lines.append((line_type, wrapped))
            elif line_type == "mono_text":
                if len(text) > self._chars_per_line:
                    for i in range(0, len(text), self._chars_per_line):
                        self._lines.append(("mono_text", text[i:i + self._chars_per_line]))
                else:
                    self._lines.append(("mono_text", text))
            elif line_type == "value_text" and vt_font.getlength(text) > max_w:
                for wrapped in self._wrap_text(text, vt_font, max_w):
                    self._lines.append(("value_text", wrapped))
            elif line_type == "hash_display":
                display = text
                display_len = len(display)
                if len(entry) >= 4:
                    head_n = entry[2] + 1
                    tail_n = entry[3] + 1
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
                self._lines.append((line_type, text))

        super().__post_init__()

    def _calculate_scroll(self):
        self._label_height = 22
        self._value_highlight_height = 28
        self._value_large_height = 30
        self._hash_line_height = 28
        self._mono_text_height = 26
        self._value_text_height = 20
        self._spacer_height = 16
        self._spacer_small_height = 8

        self._hero_fields_height = self.content_height - self._spacer_height
        for line_type, payload in self._lines:
            if line_type == "hero_fields":
                self._hero_fields_height = max(
                    self._hero_fields_height, self._hero_block_height(payload))

        bottom_padding = self._spacer_height
        total = sum(self._line_height_for(t) for t, _ in self._lines) + bottom_padding
        self.scroll_unit = 40
        self.max_scroll = max(0, total - self.content_height)

    def _line_height_for(self, line_type):
        heights = {
            "label": self._label_height,
            "label_own": self._label_height,
            "label_foreign": self._label_height,
            "foreign": self._label_height,
            "value_highlight": self._value_highlight_height,
            "value_highlight_warn": self._value_highlight_height,
            "value_highlight_yes": self._value_highlight_height,
            "value_highlight_no": self._value_highlight_height,
            "value_large": self._value_large_height,
            "value_large_warn": self._value_large_height,
            "value_large_yes": self._value_large_height,
            "hash_line": self._hash_line_height,
            "mono_text": self._mono_text_height,
            "value_text": self._value_text_height,
            "verified": self._label_height,
            "hero_fields": self._hero_fields_height,
            "spacer": self._spacer_height,
            "spacer_small": self._spacer_small_height,
        }
        return heights.get(line_type, self._value_text_height)

    def _build_draw_context(self):
        """Build the fonts and geometry shared by every draw helper for one
        render pass."""
        return {
            "label_font": Fonts.get_font(
                GUIConstants.get_body_font_name(), GUIConstants.get_body_font_size() + 2
            ),
            "value_large_font": Fonts.get_font(
                GUIConstants.get_body_font_name(),
                GUIConstants.get_top_nav_title_font_size() + 4,
            ),
            "value_highlight_font": Fonts.get_font(
                GUIConstants.get_body_font_name(),
                GUIConstants.get_top_nav_title_font_size() + 2,
            ),
            "hash_font": Fonts.get_font(GUIConstants.FIXED_WIDTH_FONT_NAME, 22),
            "hash_accent_font": Fonts.get_font(
                GUIConstants.FIXED_WIDTH_EMPHASIS_FONT_NAME, 22
            ),
            "value_text_font": Fonts.get_font(
                GUIConstants.get_body_font_name(), GUIConstants.get_body_font_size()
            ),
            "icon_font": Fonts.get_font(
                GUIConstants.ICON_FONT_NAME__SEEDSIGNER, 18, file_extension="otf"
            ),
            "center_x": self.canvas_width // 2,
        }

    def _render_content(self):
        """Draw the visible content lines, dispatching each to its draw helper.

        Lines are laid out top to bottom from the scroll offset; only lines
        intersecting the viewport are drawn. spacer lines advance ``y``
        without drawing.
        """
        ctx = self._build_draw_context()
        y = self.content_y - self.scroll_offset
        hash_line_idx = 0

        for line_type, text in self._lines:
            h = self._line_height_for(line_type)

            if y + h > self.content_y and y < self.content_y + self.content_height:
                handler = self._DRAW_DISPATCH.get(line_type)
                if handler is not None:
                    handler(self, line_type, text, y, h, hash_line_idx, ctx)

            if line_type == "hash_line":
                hash_line_idx += 1
            y += h

    def _draw_label(self, line_type, text, y, h, hash_line_idx, ctx):
        """White left-aligned section label."""
        self.renderer.draw.text(
            (self.content_x + 4, y),
            text,
            font=ctx["label_font"],
            fill="#ffffff",
            anchor="lt",
        )

    def _draw_tag_label(self, line_type, text, y, h, hash_line_idx, ctx):
        """Section label with the ownership tag word coloured green or red."""
        label_font = ctx["label_font"]
        if line_type == "label_own":
            tag_word = "Own"
        else:
            tag_word = next(
                (w for w in ("Foreign", "Unknown") if w in text), "")
        tag_color = (GUIConstants.SUCCESS_COLOR
                     if line_type == "label_own" else _FOREIGN_COLOR)
        if not tag_word or tag_word not in text:
            before, tag_word, after = text, "", ""
        else:
            before, _, after = text.partition(tag_word)
        x_cursor = self.content_x + 4
        for part_text, part_color in [
            (before, "#ffffff"),
            (tag_word, tag_color),
            (after, "#ffffff"),
        ]:
            if not part_text:
                continue
            self.renderer.draw.text(
                (int(x_cursor), y),
                part_text,
                font=label_font,
                fill=part_color,
                anchor="lt",
            )
            x_cursor += label_font.getlength(part_text)

    def _draw_value_highlight(self, line_type, text, y, h, hash_line_idx, ctx):
        """Large centered value in blue, or a warn/yes/no colour variant."""
        color = _VH_COLORS.get(line_type, GUIConstants.ACCENT_TEXT_COLOR)
        self.renderer.draw.text(
            (ctx["center_x"], y + h // 2),
            text,
            font=ctx["value_highlight_font"],
            fill=color,
            anchor="mm",
        )

    def _draw_value_large(self, line_type, text, y, h, hash_line_idx, ctx):
        """Large centered accent value, or a warn/yes colour variant."""
        color = _VL_COLORS.get(line_type, GUIConstants.ACCENT_TEXT_COLOR)
        self.renderer.draw.text(
            (ctx["center_x"], y + 2),
            text,
            font=ctx["value_large_font"],
            fill=color,
            anchor="mt",
        )

    def _draw_hash_line(self, line_type, text, y, h, hash_line_idx, ctx):
        """One wrapped line of a hash, highlighting its head/tail characters."""
        center_x = ctx["center_x"]
        hash_font = ctx["hash_font"]
        hash_accent_font = ctx["hash_accent_font"]
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

    def _draw_hero_fields(self, line_type, text, y, h, hash_line_idx, ctx):
        """Vertically centered stack of labelled hero values."""
        center_x = ctx["center_x"]
        fields = text
        field_label_font = Fonts.get_font(
            GUIConstants.get_body_font_name(),
            GUIConstants.get_body_font_size() - 2,
        )
        field_gap = 24
        block_h = self._hero_block_height(fields)
        cur_y = y + max(0, (h - block_h) // 2)

        for field_label, label_suffix, value_lines, font_size in fields:
            label_w = field_label_font.getlength(field_label)
            suffix_w = (field_label_font.getlength(" " + label_suffix)
                        if label_suffix else 0)
            label_x = center_x - (label_w + suffix_w) / 2
            self.renderer.draw.text(
                (label_x, cur_y),
                field_label,
                font=field_label_font,
                fill=GUIConstants.LABEL_FONT_COLOR,
                anchor="lt",
            )
            if label_suffix:
                self.renderer.draw.text(
                    (label_x + field_label_font.getlength(field_label + " "), cur_y),
                    label_suffix,
                    font=field_label_font,
                    fill=GUIConstants.ACCENT_TEXT_COLOR,
                    anchor="lt",
                )
            cur_y += 20 + 6
            value_font = Fonts.get_font(GUIConstants.FIXED_WIDTH_FONT_NAME, font_size)
            for value_line in value_lines:
                self.renderer.draw.text(
                    (center_x, cur_y),
                    value_line,
                    font=value_font,
                    fill=GUIConstants.BODY_FONT_COLOR,
                    anchor="mt",
                )
                cur_y += font_size + 8
            cur_y += field_gap

    def _draw_mono_text(self, line_type, text, y, h, hash_line_idx, ctx):
        """Left-aligned monospace body text."""
        self.renderer.draw.text(
            (self.content_x + 4, y),
            text,
            font=ctx["hash_font"],
            fill=GUIConstants.BODY_FONT_COLOR,
            anchor="lt",
        )

    def _draw_value_text(self, line_type, text, y, h, hash_line_idx, ctx):
        """Regular centered body text."""
        self.renderer.draw.text(
            (ctx["center_x"], y),
            text,
            font=ctx["value_text_font"],
            fill=GUIConstants.BODY_FONT_COLOR,
            anchor="mt",
        )

    def _draw_foreign(self, line_type, text, y, h, hash_line_idx, ctx):
        """Red centered text for a negative ownership badge."""
        self.renderer.draw.text(
            (ctx["center_x"], y),
            text,
            font=ctx["label_font"],
            fill=_FOREIGN_COLOR,
            anchor="mt",
        )

    def _draw_verified(self, line_type, text, y, h, hash_line_idx, ctx):
        """Green check icon and white text, centered as an ownership badge."""
        center_x = ctx["center_x"]
        icon_font = ctx["icon_font"]
        label_font = ctx["label_font"]
        icon_char = SeedSignerIconConstants.SUCCESS
        icon_bbox = icon_font.getbbox(icon_char)
        icon_w = icon_bbox[2] - icon_bbox[0]
        text_bbox = label_font.getbbox(text)
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
            text,
            font=label_font,
            fill="#ffffff",
            anchor="lt",
        )

    _DRAW_DISPATCH = {
        "label": _draw_label,
        "label_own": _draw_tag_label,
        "label_foreign": _draw_tag_label,
        "value_highlight": _draw_value_highlight,
        "value_highlight_warn": _draw_value_highlight,
        "value_highlight_yes": _draw_value_highlight,
        "value_highlight_no": _draw_value_highlight,
        "value_large": _draw_value_large,
        "value_large_warn": _draw_value_large,
        "value_large_yes": _draw_value_large,
        "hash_line": _draw_hash_line,
        "hero_fields": _draw_hero_fields,
        "mono_text": _draw_mono_text,
        "value_text": _draw_value_text,
        "foreign": _draw_foreign,
        "verified": _draw_verified,
    }

    @staticmethod
    def _hero_block_height(fields) -> int:
        """Pixel height of a hero_fields stack. Sized so an unusually long
        value (e.g. a many-component derivation path) makes the page
        scrollable rather than silently cropping lines the user must see."""
        field_gap = 24
        block_h = sum(20 + 6 + len(value_lines) * (font_size + 8)
                      for _, _, value_lines, font_size in fields)
        return block_h + field_gap * (len(fields) - 1)

    @staticmethod
    def _wrap_path(value, font, max_w):
        """Break a derivation path into lines at '/' boundaries; continuation
        lines start with '/' so the split reads unambiguously."""
        segments = value.split("/")
        lines = []
        current = segments[0]
        for segment in segments[1:]:
            candidate = f"{current}/{segment}"
            if font.getlength(candidate) <= max_w:
                current = candidate
            else:
                lines.append(current)
                current = f"/{segment}"
        lines.append(current)
        return lines

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
