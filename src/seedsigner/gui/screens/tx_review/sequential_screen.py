"""
Base sequential screen for Cardano transaction review.
"""

from dataclasses import dataclass
from typing import List

from seedsigner.gui.components import GUIConstants, Fonts
from seedsigner.hardware.buttons import HardwareButtonsConstants

from ..screen import BaseScreen
from .utils import RET_CODE__LEFT_BUTTON, RET_CODE__RIGHT_BUTTON


@dataclass
class CardanoTxSequentialScreen(BaseScreen):
    """
    Base screen for sequential transaction review.
    - Thin side indicators (< >) for left/right navigation
    - Content area in the middle
    - Up/down arrows when content is scrollable
    - Joystick: left/right = prev/next screen, up/down = scroll
    """
    title: str = ""
    page_num: int = 1
    total_pages: int = 1
    has_left: bool = True  # Show left arrow
    has_right: bool = True  # Show right arrow
    content_lines: List[str] = None  # Lines of content to display

    def __post_init__(self):
        super().__post_init__()

        self.side_button_width = 20
        self.content_x = self.side_button_width
        self.content_width = self.canvas_width - 2 * self.side_button_width

        # Top nav area
        self.top_nav_height = 28

        # Calculate content area
        self.content_y = self.top_nav_height + 4
        self.content_height = self.canvas_height - self.content_y - 24  # Leave room for scroll indicators

        # Scroll state
        self.scroll_offset = 0
        self.line_height = 18
        if self.content_lines is None:
            self.content_lines = []
        self.max_scroll = max(0, len(self.content_lines) * self.line_height - self.content_height)

    def _render(self):
        self._render_background()
        self._render_top_nav()
        self._render_side_buttons()
        self._render_content()
        self._render_scroll_indicators()

    def _render_background(self):
        self.renderer.draw.rectangle(
            (0, 0, self.canvas_width, self.canvas_height),
            fill=GUIConstants.BACKGROUND_COLOR
        )

    def _render_top_nav(self):
        # Title centered at top
        title_font = Fonts.get_font(GUIConstants.get_body_font_name(), GUIConstants.get_body_font_size())
        page_text = f"{self.page_num}/{self.total_pages}"

        # Draw title
        self.renderer.draw.text(
            (self.canvas_width // 2, 4),
            self.title,
            font=title_font,
            fill=GUIConstants.BODY_FONT_COLOR,
            anchor="mt"
        )

        # Draw page indicator on right
        self.renderer.draw.text(
            (self.canvas_width - self.side_button_width - 4, 4),
            page_text,
            font=Fonts.get_font(GUIConstants.get_body_font_name(), GUIConstants.BODY_FONT_MIN_SIZE),
            fill=GUIConstants.LABEL_FONT_COLOR,
            anchor="rt"
        )

    def _render_side_buttons(self):
        # Left side indicator
        left_color = GUIConstants.ACCENT_COLOR if self.has_left else "#333333"
        mid_y = self.content_y + self.content_height // 2

        # Left chevron
        if self.has_left:
            self.renderer.draw.polygon(
                [(15, mid_y), (5, mid_y - 10), (5, mid_y + 10)],
                fill=left_color
            )

        # Right side indicator
        right_color = GUIConstants.ACCENT_COLOR if self.has_right else "#333333"

        # Right chevron
        if self.has_right:
            right_x = self.canvas_width - 5
            self.renderer.draw.polygon(
                [(right_x - 10, mid_y), (right_x, mid_y - 10), (right_x, mid_y + 10)],
                fill=right_color
            )

    def _render_content(self):
        if not self.content_lines:
            return

        font = Fonts.get_font(GUIConstants.get_body_font_name(), GUIConstants.BODY_FONT_MIN_SIZE)
        y = self.content_y - self.scroll_offset

        for line in self.content_lines:
            if y >= self.content_y - self.line_height and y < self.content_y + self.content_height:
                # Determine color based on line prefix
                color = GUIConstants.BODY_FONT_COLOR
                if line.startswith("###"):
                    # Header line
                    line = line[3:].strip()
                    color = GUIConstants.ACCENT_COLOR
                    font = Fonts.get_font(GUIConstants.get_body_font_name(), GUIConstants.get_body_font_size())
                elif line.startswith("**"):
                    # Emphasis line
                    line = line[2:].strip()
                    color = GUIConstants.ACCENT_TEXT_COLOR
                else:
                    font = Fonts.get_font(GUIConstants.get_body_font_name(), GUIConstants.BODY_FONT_MIN_SIZE)

                self.renderer.draw.text(
                    (self.content_x + 4, y),
                    line,
                    font=font,
                    fill=color,
                    anchor="lt"
                )
            y += self.line_height

    def _render_scroll_indicators(self):
        # Bottom area - show up/down arrows if scrollable
        bottom_y = self.canvas_height - 20
        center_x = self.canvas_width // 2

        if self.max_scroll > 0:
            arrow_font = Fonts.get_font(GUIConstants.get_body_font_name(), 16)

            # Up arrow if not at top
            if self.scroll_offset > 0:
                self.renderer.draw.text(
                    (center_x - 15, bottom_y),
                    "^",
                    font=arrow_font,
                    fill=GUIConstants.ACCENT_COLOR,
                    anchor="mt"
                )

            # Down arrow if not at bottom
            if self.scroll_offset < self.max_scroll:
                self.renderer.draw.text(
                    (center_x + 15, bottom_y),
                    "v",
                    font=arrow_font,
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
                # Scroll up
                self.scroll_offset = max(0, self.scroll_offset - self.line_height * 2)
            elif user_input == HardwareButtonsConstants.KEY_DOWN:
                # Scroll down
                self.scroll_offset = min(self.max_scroll, self.scroll_offset + self.line_height * 2)
            elif user_input == HardwareButtonsConstants.KEY_PRESS:
                # Center press - could be confirm/select
                return 0
            elif user_input == HardwareButtonsConstants.KEY1:
                # Top button - back
                return -1
            elif user_input == HardwareButtonsConstants.KEY2:
                # Middle button
                return 1
            elif user_input == HardwareButtonsConstants.KEY3:
                # Bottom button
                return 2
