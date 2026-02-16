"""
Sequential output screen for navigating Cardano transaction outputs.
"""

from dataclasses import dataclass
from gettext import gettext as _

from seedsigner.gui.components import GUIConstants, Fonts
from seedsigner.hardware.buttons import HardwareButtonsConstants

from ..screen import BaseScreen
from .utils import RET_CODE__LEFT_BUTTON, RET_CODE__RIGHT_BUTTON


@dataclass
class CardanoOutputSequentialScreen(BaseScreen):
    """
    Sequential output screen with:
    - Big ADA amount
    - Formatted address with colored first/last chars
    - Scrollable list of tokens
    - Left/right navigation between outputs
    """
    title: str = "Output"
    page_num: int = 1
    total_pages: int = 1
    has_left: bool = True
    has_right: bool = True

    # Output data
    address: str = ""
    amount: int = 0  # lovelace
    tokens: dict = None  # {name: amount}
    is_change: bool = False

    def __post_init__(self):
        super().__post_init__()

        self.side_button_width = 16
        self.content_x = self.side_button_width
        self.content_width = self.canvas_width - 2 * self.side_button_width

        # Layout measurements
        self.top_nav_height = 24
        self.scroll_offset = 0
        self.token_line_height = 20

        # Calculate how many tokens can fit and total scroll height
        if self.tokens:
            self.token_list = list(self.tokens.items())
        else:
            self.token_list = []

        # Fixed content height (address + amount), tokens scroll below
        self.fixed_content_height = 95  # Space for amount + address
        self.scroll_area_y = self.top_nav_height + self.fixed_content_height
        self.scroll_area_height = self.canvas_height - self.scroll_area_y - 20

        # Calculate max scroll based on token count
        tokens_total_height = len(self.token_list) * self.token_line_height
        self.max_scroll = max(0, tokens_total_height - self.scroll_area_height)

    def _render(self):
        # Clear background
        self.renderer.draw.rectangle(
            (0, 0, self.canvas_width, self.canvas_height),
            fill=GUIConstants.BACKGROUND_COLOR
        )

        self._render_top_nav()
        self._render_side_indicators()
        self._render_amount()
        self._render_address()
        self._render_tokens()
        self._render_scroll_indicators()

    def _render_top_nav(self):
        # Title and page number
        title_font = Fonts.get_font(GUIConstants.get_body_font_name(), GUIConstants.BODY_FONT_MIN_SIZE)

        # Change badge or Output title
        if self.is_change:
            title_text = _("CHANGE")
            title_color = GUIConstants.SUCCESS_COLOR
        else:
            title_text = self.title
            title_color = GUIConstants.BODY_FONT_COLOR

        self.renderer.draw.text(
            (self.side_button_width + 4, 4),
            title_text,
            font=title_font,
            fill=title_color,
            anchor="lt"
        )

        # Page indicator
        page_text = f"{self.page_num}/{self.total_pages}"
        self.renderer.draw.text(
            (self.canvas_width - self.side_button_width - 4, 4),
            page_text,
            font=title_font,
            fill=GUIConstants.LABEL_FONT_COLOR,
            anchor="rt"
        )

    def _render_side_indicators(self):
        mid_y = self.canvas_height // 2

        # Left chevron
        if self.has_left:
            self.renderer.draw.polygon(
                [(12, mid_y), (4, mid_y - 8), (4, mid_y + 8)],
                fill=GUIConstants.ACCENT_COLOR
            )

        # Right chevron
        if self.has_right:
            right_x = self.canvas_width - 4
            self.renderer.draw.polygon(
                [(right_x - 8, mid_y), (right_x, mid_y - 8), (right_x, mid_y + 8)],
                fill=GUIConstants.ACCENT_COLOR
            )

    def _render_amount(self):
        # Big ADA amount
        ada = self.amount / 1_000_000
        ada_formatted = f"{ada:,.6f}".rstrip('0').rstrip('.')
        amount_text = f"{ada_formatted} ADA"

        amount_font = Fonts.get_font(GUIConstants.get_body_font_name(), GUIConstants.get_top_nav_title_font_size() + 4)

        self.renderer.draw.text(
            (self.canvas_width // 2, self.top_nav_height + 8),
            amount_text,
            font=amount_font,
            fill=GUIConstants.ACCENT_TEXT_COLOR,
            anchor="mt"
        )

    def _render_address(self):
        # Formatted address with colored first/last 8 characters
        addr = self.address
        if len(addr) > 20:
            # Split into first 8, middle (truncated), last 8
            first = addr[:8]
            last = addr[-8:]

            # For Cardano addresses, show prefix + first chars ... last chars
            addr_y = self.top_nav_height + 42

            font = Fonts.get_font(GUIConstants.FIXED_WIDTH_FONT_NAME, 14)
            accent_font = Fonts.get_font(GUIConstants.FIXED_WIDTH_EMPHASIS_FONT_NAME, 14)

            # Get char width
            bbox = font.getbbox("A")
            char_width = bbox[2] - bbox[0]

            # Line 1: first 8 chars (accented) + middle chars
            line1_start_x = self.content_x + 8

            # First 8 chars in accent color
            self.renderer.draw.text(
                (line1_start_x, addr_y),
                first,
                font=accent_font,
                fill=GUIConstants.ACCENT_TEXT_COLOR,
                anchor="lt"
            )

            # Middle part (truncated) in muted color
            middle_x = line1_start_x + char_width * 8
            middle_chars = min(12, len(addr) - 16)
            middle_text = addr[8:8+middle_chars]
            self.renderer.draw.text(
                (middle_x, addr_y),
                middle_text,
                font=font,
                fill=GUIConstants.LABEL_FONT_COLOR,
                anchor="lt"
            )

            # Line 2: ... more middle ... last 8 chars (accented)
            addr_y2 = addr_y + 18

            # Ellipsis
            self.renderer.draw.text(
                (line1_start_x, addr_y2),
                "...",
                font=font,
                fill=GUIConstants.LABEL_FONT_COLOR,
                anchor="lt"
            )

            # More middle chars
            mid2_x = line1_start_x + char_width * 3
            mid2_text = addr[-16:-8] if len(addr) > 24 else ""
            self.renderer.draw.text(
                (mid2_x, addr_y2),
                mid2_text,
                font=font,
                fill=GUIConstants.LABEL_FONT_COLOR,
                anchor="lt"
            )

            # Last 8 chars in accent
            last_x = mid2_x + char_width * len(mid2_text)
            self.renderer.draw.text(
                (last_x, addr_y2),
                last,
                font=accent_font,
                fill=GUIConstants.ACCENT_TEXT_COLOR,
                anchor="lt"
            )

    def _render_tokens(self):
        if not self.token_list:
            return

        # Tokens header
        header_y = self.scroll_area_y - 18
        header_font = Fonts.get_font(GUIConstants.get_body_font_name(), GUIConstants.BODY_FONT_MIN_SIZE)
        self.renderer.draw.text(
            (self.content_x + 8, header_y),
            _("Tokens ({})").format(len(self.token_list)),
            font=header_font,
            fill=GUIConstants.LABEL_FONT_COLOR,
            anchor="lt"
        )

        # Draw separator line
        self.renderer.draw.line(
            (self.content_x, self.scroll_area_y - 2, self.canvas_width - self.side_button_width, self.scroll_area_y - 2),
            fill="#333333",
            width=1
        )

        # Render visible tokens
        token_font = Fonts.get_font(GUIConstants.get_body_font_name(), GUIConstants.BODY_FONT_MIN_SIZE)
        y = self.scroll_area_y - self.scroll_offset

        for token_name, token_amount in self.token_list:
            if y >= self.scroll_area_y - self.token_line_height and y < self.scroll_area_y + self.scroll_area_height:
                # Clip rendering to scroll area
                if y >= self.scroll_area_y:
                    # Token name
                    display_name = token_name[:16] + "..." if len(token_name) > 16 else token_name
                    self.renderer.draw.text(
                        (self.content_x + 8, y),
                        display_name,
                        font=token_font,
                        fill=GUIConstants.BODY_FONT_COLOR,
                        anchor="lt"
                    )

                    # Token amount (right aligned)
                    amount_text = f"{token_amount:,}"
                    self.renderer.draw.text(
                        (self.canvas_width - self.side_button_width - 8, y),
                        amount_text,
                        font=token_font,
                        fill=GUIConstants.ACCENT_TEXT_COLOR,
                        anchor="rt"
                    )
            y += self.token_line_height

    def _render_scroll_indicators(self):
        if self.max_scroll <= 0:
            return

        # Bottom scroll indicators
        bottom_y = self.canvas_height - 14
        center_x = self.canvas_width // 2
        indicator_font = Fonts.get_font(GUIConstants.get_body_font_name(), 16)

        # Up indicator (when not at top)
        if self.scroll_offset > 0:
            self.renderer.draw.text(
                (center_x - 15, bottom_y),
                "^",
                font=indicator_font,
                fill=GUIConstants.ACCENT_COLOR,
                anchor="mt"
            )

        # Down indicator (when not at bottom)
        if self.scroll_offset < self.max_scroll:
            self.renderer.draw.text(
                (center_x + 15, bottom_y),
                "v",
                font=indicator_font,
                fill=GUIConstants.ACCENT_COLOR,
                anchor="mt"
            )

    def _run(self):
        while True:
            self._render()
            self.renderer.show_image()

            user_input = self.hw_inputs.wait_for(HardwareButtonsConstants.ALL_KEYS)

            if user_input == HardwareButtonsConstants.KEY_LEFT:
                if self.has_left:
                    return RET_CODE__LEFT_BUTTON
            elif user_input == HardwareButtonsConstants.KEY_RIGHT:
                if self.has_right:
                    return RET_CODE__RIGHT_BUTTON
            elif user_input == HardwareButtonsConstants.KEY_UP:
                self.scroll_offset = max(0, self.scroll_offset - self.token_line_height * 2)
            elif user_input == HardwareButtonsConstants.KEY_DOWN:
                self.scroll_offset = min(self.max_scroll, self.scroll_offset + self.token_line_height * 2)
            elif user_input == HardwareButtonsConstants.KEY_PRESS:
                return 0  # Confirm/select
            elif user_input == HardwareButtonsConstants.KEY1:
                return -1  # Back/cancel
