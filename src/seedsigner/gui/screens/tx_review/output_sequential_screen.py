"""
Sequential output screen for navigating Cardano transaction outputs.
"""

from dataclasses import dataclass
from gettext import gettext as _

from seedsigner.gui.components import GUIConstants, Fonts, SeedSignerIconConstants

from .sequential_base_screen import CardanoSequentialBaseScreen
from .utils import format_ada, wrap_highlighted_line, draw_highlighted_line


@dataclass
class CardanoOutputSequentialScreen(CardanoSequentialBaseScreen):
    """
    Output screen with scrollable fields:
    - Amount (ADA)
    - Address
    - Tokens (full asset ID + amount, each on own lines)

    Each field has a white left-aligned label, followed by
    centered content on the next line(s).
    The entire screen scrolls as one unit.

    Fields:
        address: bech32 output address.
        amount: output value in lovelace.
        tokens: {name: amount} map of native assets.
        is_change: whether the output verified as this wallet's change.
        datum_type: "Inline" or "Hash", None when the output has no datum.
        datum_hex: hex string of the datum hash or inline datum CBOR.
        script_ref_lang: "Plutus V1"/"V2"/"V3" or "Native Script".
    """
    address: str = ""
    amount: int = 0
    tokens: dict = None
    is_change: bool = False
    datum_type: str = None
    datum_hex: str = None
    script_ref_lang: str = None

    def __post_init__(self):
        """Compute chars_per_line from the screen width and pre-build lines.

        The Renderer singleton is already available before
        super().__post_init__(), and the renderable lines must exist before
        calling super so _calculate_scroll can compute the total height.
        """
        if self.tokens:
            self.token_list = list(self.tokens.items())
        else:
            self.token_list = []

        from seedsigner.gui.renderer import Renderer
        renderer = Renderer.get_instance()
        side_button_width = 20
        content_margin = 8
        usable_width = renderer.canvas_width - 2 * side_button_width - 2 * content_margin
        addr_font = Fonts.get_font(GUIConstants.FIXED_WIDTH_FONT_NAME, 22)
        char_w = addr_font.getlength("A")
        self._chars_per_line = max(10, int(usable_width / char_w))

        self._build_lines()
        super().__post_init__()

    def _build_lines(self):
        """Build a list of (type, text) tuples representing the content.

        Content order: amount, address (labelled Own or Foreign, with a
        Verified Address indicator for change outputs), tokens, datum, and
        reference script.

        Addresses and CIP-14 asset fingerprints are shown with the bech32
        prefix (addr1, addr_test1, stake1, stake_test1, asset1) plus a few
        characters highlighted at the start and end, with spaces separating
        head, middle, and tail. ``_addr_tail_n`` is the number of trailing
        address characters highlighted; ``_token_highlight_n`` the number
        highlighted at each end of an asset ID beyond its prefix.
        ``_token_ranges`` records (start_idx, end_idx, display_len, head_n,
        tail_n) per token's fingerprint lines. Wrapped lines skip a leading
        space at line boundaries.

        Datum display: a hash is always 64 chars and is shown in full; an
        inline datum up to 64 chars is shown in full (a very small one
        entirely highlighted); a longer inline datum is truncated with an
        ellipsis in the middle. Head and tail highlight counts include the
        separator space where one is inserted. Token amounts carry an
        "Unknown decimals" warning.
        """
        self._lines = []
        self._token_ranges = []
        self._addr_tail_n = 6
        self._token_highlight_n = 7

        self._lines.append(("label", "Amount:"))
        self._lines.append(("spacer", ""))
        self._lines.append(("value_large", format_ada(self.amount)))

        self._lines.append(("spacer", ""))
        if self.is_change:
            self._lines.append(("label_own", "Address (Own):"))
        else:
            self._lines.append(("label_foreign", "Address (Foreign):"))
        self._lines.append(("spacer", ""))

        addr = self.address
        prefixes = ("addr_test1", "addr1", "stake_test1", "stake1")
        prefix_len = 0
        for p in prefixes:
            if addr.startswith(p):
                prefix_len = len(p)
                break
        self._addr_head_n = prefix_len + self._addr_tail_n
        head_n = self._addr_head_n
        tail_n = self._addr_tail_n
        if len(addr) > head_n + tail_n:
            self._addr_display = f"{addr[:head_n]} {addr[head_n:-tail_n]} {addr[-tail_n:]}"
        else:
            self._addr_display = addr
        addr_wrapped = wrap_highlighted_line(self._addr_display, self._chars_per_line)
        self._addr_line_gpos = [gp for gp, chunk in addr_wrapped]
        for gp, chunk in addr_wrapped:
            self._lines.append(("addr_line", chunk))

        if self.is_change:
            self._lines.append(("spacer_small", ""))
            self._lines.append(("verified", _("Verified Address")))

        if self.token_list:
            self._lines.append(("spacer", ""))
            self._lines.append(("label", f"Tokens ({len(self.token_list)}):"))

            for idx, (token_name, token_amount) in enumerate(self.token_list):
                if idx > 0:
                    self._lines.append(("spacer", ""))
                    self._lines.append(("spacer", ""))
                else:
                    self._lines.append(("spacer_small", ""))
                fingerprint = str(token_name) if str(token_name) else "(unnamed)"
                fp_prefix_len = len("asset1") if fingerprint.startswith("asset1") else 0
                head_n = fp_prefix_len + self._token_highlight_n
                tail_n = self._token_highlight_n
                if len(fingerprint) > head_n + tail_n:
                    fp_display = f"{fingerprint[:head_n]} {fingerprint[head_n:-tail_n]} {fingerprint[-tail_n:]}"
                else:
                    fp_display = fingerprint
                token_start = len(self._lines)
                for gp, chunk in wrap_highlighted_line(fp_display, self._chars_per_line, skip_boundary_space=False):
                    self._lines.append(("token_id_line", chunk))
                token_end = len(self._lines)
                self._token_ranges.append((token_start, token_end, len(fp_display), head_n, tail_n))
                self._lines.append(("spacer_small", ""))
                self._lines.append(("token_amount", f"{token_amount:,}"))
                self._lines.append(("warning_small", _("Unknown decimals")))

        if self.datum_type:
            self._lines.append(("spacer", ""))
            self._lines.append(("label", f"Datum ({self.datum_type}):"))
            self._lines.append(("spacer", ""))
            if self.datum_hex:
                hex_str = self.datum_hex
                highlight = 7
                if self.datum_type == "Hash":
                    display = f"{hex_str[:highlight]} {hex_str[highlight:-highlight]} {hex_str[-highlight:]}"
                    self._datum_head_n = highlight + 1
                    self._datum_tail_n = highlight + 1
                elif len(hex_str) <= 64:
                    if len(hex_str) > 2 * highlight:
                        display = f"{hex_str[:highlight]} {hex_str[highlight:-highlight]} {hex_str[-highlight:]}"
                        self._datum_head_n = highlight + 1
                        self._datum_tail_n = highlight + 1
                    else:
                        display = hex_str
                        self._datum_head_n = len(display)
                        self._datum_tail_n = 0
                else:
                    n = 28
                    display = f"{hex_str[:n]} ... {hex_str[-n:]}"
                    self._datum_head_n = highlight
                    self._datum_tail_n = highlight
                self._datum_display = display
                for gp, chunk in wrap_highlighted_line(display, self._chars_per_line, skip_boundary_space=False):
                    self._lines.append(("datum_hex_line", chunk))

        if self.script_ref_lang:
            self._lines.append(("spacer", ""))
            self._lines.append(("label", "Ref Script:"))
            self._lines.append(("spacer", ""))
            self._lines.append(("value_highlight", self.script_ref_lang))

    def _calculate_scroll(self):
        self._label_height = 22
        self._value_height = 20
        self._value_large_height = 30
        self._addr_line_height = 28
        self._token_id_line_height = 28
        self._token_amount_height = 26
        self._datum_hex_line_height = 28
        self._value_highlight_height = 28
        self._warning_small_height = 16
        self._spacer_height = 16
        self._spacer_small_height = 8

        total = 0
        for line_type, _ in self._lines:
            total += self._line_height_for(line_type)

        self.scroll_unit = 40
        self.max_scroll = max(0, total - self.content_height)

    def _line_height_for(self, line_type):
        if line_type in ("label", "label_own", "label_foreign", "verified"):
            return self._label_height
        elif line_type == "value_large":
            return self._value_large_height
        elif line_type == "addr_line":
            return self._addr_line_height
        elif line_type == "token_id_line":
            return self._token_id_line_height
        elif line_type == "token_amount":
            return self._token_amount_height
        elif line_type == "datum_hex_line":
            return self._datum_hex_line_height
        elif line_type == "value_highlight":
            return self._value_highlight_height
        elif line_type == "warning_small":
            return self._warning_small_height
        elif line_type == "spacer":
            return self._spacer_height
        elif line_type == "spacer_small":
            return self._spacer_small_height
        else:
            return self._value_height

    def _render_content(self):
        """Draw the lines that fall inside the visible content area.

        Address, token id, and datum hex lines render in segments: the
        emphasis font in accent color for the head and tail highlights,
        grey for the middle. Spacer lines render nothing. The per-type
        counters track the global character position across wrapped lines;
        the token position counter resets after each token amount.
        """
        label_font = Fonts.get_font(
            GUIConstants.get_body_font_name(), GUIConstants.get_body_font_size() + 2
        )
        value_large_font = Fonts.get_font(
            GUIConstants.get_body_font_name(),
            GUIConstants.get_top_nav_title_font_size() + 4,
        )
        mono_font = Fonts.get_font(GUIConstants.FIXED_WIDTH_FONT_NAME, 16)
        addr_font = Fonts.get_font(GUIConstants.FIXED_WIDTH_FONT_NAME, 22)
        addr_accent_font = Fonts.get_font(GUIConstants.FIXED_WIDTH_EMPHASIS_FONT_NAME, 22)
        token_amount_font = Fonts.get_font(
            GUIConstants.get_body_font_name(),
            GUIConstants.get_top_nav_title_font_size() + 2,
        )
        warning_font = Fonts.get_font(
            GUIConstants.get_body_font_name(), GUIConstants.get_body_font_size() - 2
        )
        icon_font = Fonts.get_font(
            GUIConstants.ICON_FONT_NAME__SEEDSIGNER, 18, file_extension="otf"
        )

        y = self.content_y - self.scroll_offset
        center_x = self.canvas_width // 2
        addr_line_idx = 0
        token_char_offset = 0
        token_range_idx = 0
        datum_char_offset = 0

        for line_idx, (line_type, text) in enumerate(self._lines):
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
                elif line_type in ("label_own", "label_foreign"):
                    tag_word = "Own" if line_type == "label_own" else "Foreign"
                    tag_color = GUIConstants.SUCCESS_COLOR if line_type == "label_own" else "#CF6679"
                    x_cursor = self.content_x + 4
                    for part_text, part_color in [
                        ("Address (", "#ffffff"),
                        (tag_word, tag_color),
                        ("):", "#ffffff"),
                    ]:
                        self.renderer.draw.text(
                            (int(x_cursor), y),
                            part_text,
                            font=label_font,
                            fill=part_color,
                            anchor="lt",
                        )
                        x_cursor += label_font.getlength(part_text)
                elif line_type == "value_large":
                    self.renderer.draw.text(
                        (center_x, y + 2),
                        text,
                        font=value_large_font,
                        fill=GUIConstants.ACCENT_TEXT_COLOR,
                        anchor="mt",
                    )
                elif line_type == "addr_line":
                    head_n = self._addr_head_n + 1
                    tail_n = self._addr_tail_n + 1
                    display_len = len(self._addr_display)
                    gpos = self._addr_line_gpos[addr_line_idx]
                    char_w = addr_font.getlength("A")
                    draw_highlighted_line(
                        self.renderer.draw, text, gpos, display_len, head_n,
                        tail_n, y, center_x, char_w, addr_font, addr_accent_font,
                        GUIConstants.LABEL_FONT_COLOR, GUIConstants.ACCENT_TEXT_COLOR,
                    )
                elif line_type == "token_id_line":
                    if token_range_idx < len(self._token_ranges):
                        _, _, display_len, tok_head_n, tok_tail_n = self._token_ranges[token_range_idx]
                    else:
                        display_len = len(text)
                        tok_head_n = self._token_highlight_n
                        tok_tail_n = self._token_highlight_n
                    head_accent = tok_head_n + 1
                    tail_accent = tok_tail_n + 1
                    char_w = addr_font.getlength("A")
                    draw_highlighted_line(
                        self.renderer.draw, text, token_char_offset, display_len,
                        head_accent, tail_accent, y, center_x, char_w, addr_font,
                        addr_accent_font, GUIConstants.LABEL_FONT_COLOR,
                        GUIConstants.ACCENT_TEXT_COLOR,
                    )
                elif line_type == "token_amount":
                    self.renderer.draw.text(
                        (center_x, y),
                        text,
                        font=token_amount_font,
                        fill=GUIConstants.ACCENT_TEXT_COLOR,
                        anchor="mt",
                    )
                elif line_type == "warning_small":
                    self.renderer.draw.text(
                        (center_x, y),
                        text,
                        font=warning_font,
                        fill=GUIConstants.LABEL_FONT_COLOR,
                        anchor="mt",
                    )
                elif line_type == "value_mono":
                    self.renderer.draw.text(
                        (center_x, y),
                        text,
                        font=mono_font,
                        fill=GUIConstants.BODY_FONT_COLOR,
                        anchor="mt",
                    )
                elif line_type == "datum_hex_line":
                    datum_display = getattr(self, '_datum_display', text)
                    head_n = getattr(self, '_datum_head_n', 12)
                    tail_n = getattr(self, '_datum_tail_n', 12)
                    display_len = len(datum_display)
                    char_w = addr_font.getlength("A")
                    draw_highlighted_line(
                        self.renderer.draw, text, datum_char_offset, display_len,
                        head_n, tail_n, y, center_x, char_w, addr_font,
                        addr_accent_font, GUIConstants.LABEL_FONT_COLOR,
                        GUIConstants.ACCENT_TEXT_COLOR,
                    )
                elif line_type == "value_highlight":
                    self.renderer.draw.text(
                        (center_x, y),
                        text,
                        font=token_amount_font,
                        fill=GUIConstants.ACCENT_TEXT_COLOR,
                        anchor="mt",
                    )
                elif line_type == "verified":
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

            if line_type == "addr_line":
                addr_line_idx += 1
            elif line_type == "token_id_line":
                token_char_offset += len(text)
            elif line_type == "datum_hex_line":
                datum_char_offset += len(text)
            elif line_type == "token_amount":
                token_char_offset = 0
                token_range_idx += 1
            y += h
