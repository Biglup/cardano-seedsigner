"""
Screen for displaying a Cardano address/credential with the same rendering
style as the TX review output screen (accent-colored prefix and suffix).
"""

from dataclasses import dataclass
from gettext import gettext as _

from seedsigner.gui.components import (
    GUIConstants,
    Fonts,
)

from .screen import ButtonListScreen, ButtonOption


@dataclass
class CardanoAddressDetailScreen(ButtonListScreen):
    """
    Displays a full Cardano address or credential (bech32) with accent-colored
    prefix and suffix, matching the TX review output screen style.
    """
    address: str = ""
    address_title: str = ""

    def __post_init__(self):
        self.title = self.address_title
        self.is_bottom_list = True
        self.button_data = [ButtonOption(_("Show QR"))]

        super().__post_init__()

        # Detect Cardano bech32 prefix for accent coloring
        addr = self.address
        prefixes = ("addr_test1", "addr1", "stake_test1", "stake1", "drep1", "drep_test1", "acct_xvk")
        prefix_len = 0
        for p in prefixes:
            if addr.startswith(p):
                prefix_len = len(p)
                break

        self._tail_n = 6
        self._head_n = prefix_len + self._tail_n

        # Build the display string with spaces separating head/middle/tail
        head_n = self._head_n
        tail_n = self._tail_n
        if len(addr) > head_n + tail_n:
            self._addr_display = f"{addr[:head_n]} {addr[head_n:-tail_n]} {addr[-tail_n:]}"
        else:
            self._addr_display = addr

        # Compute chars per line from available width
        from seedsigner.gui.renderer import Renderer
        renderer = Renderer.get_instance()
        content_margin = GUIConstants.EDGE_PADDING
        usable_width = renderer.canvas_width - 2 * content_margin
        addr_font = Fonts.get_font(GUIConstants.FIXED_WIDTH_FONT_NAME, 22)
        char_w = addr_font.getlength("A")
        self._chars_per_line = max(10, int(usable_width / char_w))
        self._char_w = char_w

        # Split into lines
        self._addr_lines = []
        self._addr_line_gpos = []
        pos = 0
        while pos < len(self._addr_display):
            if self._addr_display[pos] == " ":
                pos += 1
            chunk = self._addr_display[pos:pos + self._chars_per_line]
            self._addr_line_gpos.append(pos)
            self._addr_lines.append(chunk)
            pos += len(chunk)

        # Vertically center the address block between top nav and buttons
        line_height = 24
        total_text_height = len(self._addr_lines) * line_height
        top_y = self.top_nav.height
        # buttons area starts roughly at canvas_height - button_height - padding
        bottom_y = self.canvas_height - 60  # approximate button area top
        available_height = bottom_y - top_y
        self._start_y = top_y + max(GUIConstants.COMPONENT_PADDING, (available_height - total_text_height) // 2)


    def _render(self):
        super()._render()

        addr_font = Fonts.get_font(GUIConstants.FIXED_WIDTH_FONT_NAME, 22)
        addr_accent_font = Fonts.get_font(GUIConstants.FIXED_WIDTH_EMPHASIS_FONT_NAME, 22)

        center_x = self.canvas_width // 2
        display_len = len(self._addr_display)
        head_n = self._head_n + 1  # +1 for space after head
        tail_n = self._tail_n + 1  # +1 for space before tail
        line_height = 24

        y = self._start_y

        for line_idx, text in enumerate(self._addr_lines):
            gpos = self._addr_line_gpos[line_idx]
            line_w = self._char_w * len(text)
            x_cursor = int(center_x - line_w // 2)

            # Split line into accent/non-accent segments
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
                font = addr_accent_font if is_accent else addr_font
                color = GUIConstants.ACCENT_TEXT_COLOR if is_accent else GUIConstants.LABEL_FONT_COLOR
                self.renderer.draw.text(
                    (x_cursor, y),
                    seg_text,
                    font=font,
                    fill=color,
                    anchor="lt",
                )
                x_cursor += int(self._char_w * len(seg_text))

            y += line_height
