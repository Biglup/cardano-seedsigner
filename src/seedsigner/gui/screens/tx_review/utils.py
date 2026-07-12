"""
Shared utilities for Cardano transaction review screens.

RET_CODE__LEFT_BUTTON and RET_CODE__RIGHT_BUTTON are the return codes for
sequential left/right navigation.
"""

from gettext import gettext as _


RET_CODE__LEFT_BUTTON = -2
RET_CODE__RIGHT_BUTTON = -3


CONTENT_LINE_TYPES = frozenset({
    "label",
    "label_own",
    "label_foreign",
    "value_highlight",
    "value_highlight_warn",
    "value_highlight_yes",
    "value_highlight_no",
    "value_large",
    "value_large_warn",
    "value_large_yes",
    "value_text",
    "mono_text",
    "hash_display",
    "hero_fields",
    "verified",
    "foreign",
    "spacer",
    "spacer_small",
})


class Line:
    """Typed constructors for CardanoContentSequentialScreen content entries.

    Each method returns the exact tuple the screen renders, so views build
    content by name instead of hand-writing variable-arity tuples. A
    misspelled constructor is an AttributeError at build time rather than a
    line type the screen silently drops.
    """

    @staticmethod
    def label(text):
        """White left-aligned section label."""
        return ("label", text)

    @staticmethod
    def label_own(text):
        """Section label with the word "Own" drawn green."""
        return ("label_own", text)

    @staticmethod
    def label_foreign(text):
        """Section label with "Foreign"/"Unknown" drawn red."""
        return ("label_foreign", text)

    @staticmethod
    def value_highlight(text):
        """Large blue centered value."""
        return ("value_highlight", text)

    @staticmethod
    def value_highlight_warn(text):
        """Large red centered value."""
        return ("value_highlight_warn", text)

    @staticmethod
    def value_highlight_yes(text):
        """Large green centered value."""
        return ("value_highlight_yes", text)

    @staticmethod
    def value_highlight_no(text):
        """Large red centered value for a negative vote."""
        return ("value_highlight_no", text)

    @staticmethod
    def value_large(text):
        """Large accent centered value (ADA amounts)."""
        return ("value_large", text)

    @staticmethod
    def value_large_warn(text):
        """Large red centered value (burn amounts)."""
        return ("value_large_warn", text)

    @staticmethod
    def value_large_yes(text):
        """Large green centered value (mint amounts)."""
        return ("value_large_yes", text)

    @staticmethod
    def value_text(text):
        """Regular centered body text."""
        return ("value_text", text)

    @staticmethod
    def mono_text(text):
        """Left-aligned monospace text (JSON, hex dumps)."""
        return ("mono_text", text)

    @staticmethod
    def hash(fmt, head=None, tail=None):
        """Monospace hash with first/last N chars highlighted.

        Pass head and tail to override the highlight ranges; omit both to
        use the screen's default highlight width.
        """
        if head is None and tail is None:
            return ("hash_display", fmt)
        return ("hash_display", fmt, head, tail)

    @staticmethod
    def hero_fields(fields):
        """Vertically centered stack of (label, suffix, value) fields."""
        return ("hero_fields", fields)

    @staticmethod
    def verified(text):
        """Green check icon and white text, centered (ownership badge)."""
        return ("verified", text)

    @staticmethod
    def foreign(text):
        """Red centered text (negative ownership badge)."""
        return ("foreign", text)

    @staticmethod
    def spacer():
        """Standard vertical spacing."""
        return ("spacer", "")

    @staticmethod
    def spacer_small():
        """Small vertical spacing."""
        return ("spacer_small", "")


def wrap_highlighted_line(display, chars_per_line, skip_boundary_space=True):
    """Wrap a space-annotated hex/bech32 string into fixed-width lines.

    ``display`` already carries single spaces at the highlight boundaries.
    Each line takes up to ``chars_per_line`` characters. When
    ``skip_boundary_space`` is set, a space that falls at the start of a
    wrapped line is dropped so it does not indent the line. Returns a list
    of ``(global_position, chunk)`` pairs, where ``global_position`` is the
    chunk's start index in ``display`` used later for head/tail accent
    lookup.
    """
    lines = []
    pos = 0
    while pos < len(display):
        if skip_boundary_space and display[pos] == " ":
            pos += 1
        chunk = display[pos:pos + chars_per_line]
        lines.append((pos, chunk))
        pos += len(chunk)
    return lines


def draw_highlighted_line(draw, text, gpos, display_len, head_n, tail_n, y,
                          center_x, char_w, normal_font, accent_font,
                          normal_color, accent_color):
    """Paint one wrapped line with accent-coloured head and tail characters.

    A character at global index ``gp`` is accented when ``gp < head_n`` or
    ``gp >= display_len - tail_n``; ``head_n`` and ``tail_n`` already
    include the extra character covering the separator space. Accent runs
    use ``accent_font``/``accent_color`` and the middle uses
    ``normal_font``/``normal_color``. The line is centered on ``center_x``
    with a fixed ``char_w`` advance per character.
    """
    line_w = char_w * len(text)
    x_cursor = int(center_x - line_w // 2)

    segments = []
    seg_start = 0
    cur_accent = None
    for ci in range(len(text)):
        gp = gpos + ci
        is_accent = gp < head_n or gp >= display_len - tail_n
        if cur_accent is None:
            cur_accent = is_accent
        if is_accent != cur_accent:
            segments.append((text[seg_start:ci], cur_accent))
            seg_start = ci
            cur_accent = is_accent
    segments.append((text[seg_start:], cur_accent))

    for seg_text, is_accent in segments:
        font = accent_font if is_accent else normal_font
        color = accent_color if is_accent else normal_color
        draw.text((x_cursor, y), seg_text, font=font, fill=color, anchor="lt")
        x_cursor += int(char_w * len(seg_text))


def format_ada(lovelace: int) -> str:
    """Format a lovelace amount as an exact ADA string using integer arithmetic."""
    sign = "-" if lovelace < 0 else ""
    whole, fraction = divmod(abs(lovelace), 1_000_000)
    formatted = f"{whole:,}"
    decimals = f"{fraction:06d}".rstrip('0')
    if decimals:
        formatted = f"{formatted}.{decimals}"
    return f"{sign}{formatted} ADA"
