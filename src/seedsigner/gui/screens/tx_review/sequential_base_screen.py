"""
Base sequential screen for Cardano transaction review.

Provides the shared frame (top nav, side chevrons, scroll indicators,
input loop) so subclasses only implement _render_content().
"""

from dataclasses import dataclass

from seedsigner.gui.components import GUIConstants, Fonts
from seedsigner.hardware.buttons import HardwareButtonsConstants

from ..screen import BaseScreen
from .utils import RET_CODE__LEFT_BUTTON, RET_CODE__RIGHT_BUTTON


@dataclass
class CardanoSequentialBaseScreen(BaseScreen):
    """
    Base screen for all sequential transaction review screens.

    Handles:
    - Background clearing
    - Top nav bar (title + page counter)
    - Side chevrons (left/right navigation indicators)
    - Scroll indicators (up/down arrows)
    - Input loop (left/right nav, up/down scroll, button presses)

    Subclasses must implement:
    - _render_content(): draw section-specific content
    - _calculate_scroll(): set self.max_scroll (called from __post_init__)
    """
    title: str = ""
    page_num: int = 1
    total_pages: int = 1
    has_left: bool = True
    has_right: bool = True

    def __post_init__(self):
        super().__post_init__()

        self.side_button_width = 20
        self.content_x = self.side_button_width
        self.content_width = self.canvas_width - 2 * self.side_button_width

        self.top_nav_height = GUIConstants.TOP_NAV_HEIGHT

        self.bottom_bar_height = 24
        self.content_y = self.top_nav_height + 2
        self.content_height = self.canvas_height - self.content_y - self.bottom_bar_height

        self.scroll_offset = 0
        self.scroll_unit = 36  # pixels per scroll step
        self.max_scroll = 0

        self._active_chevron = None  # "left" or "right" when pressed
        self._active_scroll = None  # "up" or "down" when pressed

        self._calculate_scroll()

    def _calculate_scroll(self):
        """Override to set self.max_scroll (and optionally self.scroll_unit)."""
        pass

    def _render(self):
        self._render_background()
        self._render_content()
        self._render_top_nav()
        self._render_side_buttons()
        self._render_scroll_indicators()

    def _render_background(self):
        self.renderer.draw.rectangle(
            (0, 0, self.canvas_width, self.canvas_height),
            fill=GUIConstants.BACKGROUND_COLOR,
        )

    def _render_top_nav(self):
        # Clear top nav area to prevent content bleed-through
        self.renderer.draw.rectangle(
            (0, 0, self.canvas_width, self.top_nav_height),
            fill=GUIConstants.BACKGROUND_COLOR,
        )

        # Progress bar — full width
        bar_height = 4
        bar_y = 0
        bar_x = 0
        bar_width = self.canvas_width

        self.renderer.draw.rectangle(
            (bar_x, bar_y, bar_x + bar_width, bar_y + bar_height),
            fill="#333333",
        )

        progress = self.page_num / self.total_pages if self.total_pages > 0 else 1
        fill_width = int(bar_width * progress)
        if fill_width > 0:
            self.renderer.draw.rectangle(
                (bar_x, bar_y, bar_x + fill_width, bar_y + bar_height),
                fill=GUIConstants.ACCENT_COLOR,
            )

        # Title centered in top nav area (below progress bar)
        title_center_y = bar_y + bar_height + (self.top_nav_height - bar_height) // 2
        title_font = Fonts.get_font(
            GUIConstants.get_top_nav_title_font_name(),
            GUIConstants.get_top_nav_title_font_size(),
        )
        self.renderer.draw.text(
            (self.canvas_width // 2, title_center_y),
            self.title,
            font=title_font,
            fill="#ffffff",
            anchor="mm",
        )

    def _render_side_buttons(self):
        mid_y = self.content_y + self.content_height // 2
        if self.has_left:
            left_color = "#ffffff" if self._active_chevron == "left" else GUIConstants.ACCENT_COLOR
            self.renderer.draw.polygon(
                [(5, mid_y), (15, mid_y - 10), (15, mid_y + 10)],
                fill=left_color,
            )

        if self.has_right:
            right_x = self.canvas_width - 5
            right_color = "#ffffff" if self._active_chevron == "right" else GUIConstants.ACCENT_COLOR
            self.renderer.draw.polygon(
                [(right_x, mid_y), (right_x - 10, mid_y - 10), (right_x - 10, mid_y + 10)],
                fill=right_color,
            )

    def _render_content(self):
        """Override in subclasses to draw section-specific content."""
        raise NotImplementedError

    def _render_scroll_indicators(self):
        # Always clear the bottom bar to prevent content overflow
        bar_top = self.canvas_height - self.bottom_bar_height
        self.renderer.draw.rectangle(
            (0, bar_top, self.canvas_width, self.canvas_height),
            fill=GUIConstants.BACKGROUND_COLOR,
        )

        if self.max_scroll <= 0:
            return

        # Match side chevron size: 10px wide, 20px tall (base=20)
        mid_y = self.canvas_height - self.bottom_bar_height // 2

        if self.scroll_offset > 0:
            # Up chevron at 1/3 screen width — triangle pointing up
            cx = self.canvas_width // 3
            up_color = "#ffffff" if self._active_scroll == "up" else GUIConstants.ACCENT_COLOR
            self.renderer.draw.polygon(
                [(cx, mid_y - 5), (cx - 10, mid_y + 5), (cx + 10, mid_y + 5)],
                fill=up_color,
            )

        if self.scroll_offset < self.max_scroll:
            # Down chevron at 2/3 screen width — triangle pointing down
            cx = 2 * self.canvas_width // 3
            down_color = "#ffffff" if self._active_scroll == "down" else GUIConstants.ACCENT_COLOR
            self.renderer.draw.polygon(
                [(cx, mid_y + 5), (cx - 10, mid_y - 5), (cx + 10, mid_y - 5)],
                fill=down_color,
            )

    def _run(self):
        while True:
            self._render()
            self.renderer.show_image()

            user_input = self.hw_inputs.wait_for(HardwareButtonsConstants.ALL_KEYS)

            if user_input == HardwareButtonsConstants.KEY_LEFT:
                if self.has_left:
                    self._active_chevron = "left"
                    self._render()
                    self.renderer.show_image()
                    return RET_CODE__LEFT_BUTTON
            elif user_input == HardwareButtonsConstants.KEY_RIGHT:
                if self.has_right:
                    self._active_chevron = "right"
                    self._render()
                    self.renderer.show_image()
                    return RET_CODE__RIGHT_BUTTON
            elif user_input == HardwareButtonsConstants.KEY_UP:
                self.scroll_offset = max(0, self.scroll_offset - self.scroll_unit)
                self._active_scroll = "up"
                self._render()
                self.renderer.show_image()
                self._active_scroll = None
            elif user_input == HardwareButtonsConstants.KEY_DOWN:
                self.scroll_offset = min(
                    self.max_scroll, self.scroll_offset + self.scroll_unit
                )
                self._active_scroll = "down"
                self._render()
                self.renderer.show_image()
                self._active_scroll = None
            elif user_input == HardwareButtonsConstants.KEY1:
                return -1  # Back
