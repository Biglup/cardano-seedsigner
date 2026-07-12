"""
Base sequential screen for Cardano transaction review.

Provides the shared frame (top nav, side chevrons, scroll indicators,
input loop) so subclasses only implement _render_content().
"""

import time
from dataclasses import dataclass

from seedsigner.gui.components import GUIConstants, Fonts
from seedsigner.hardware.buttons import HardwareButtonsConstants
from seedsigner.models.threads import BaseThread

from ..screen import BaseScreen, RET_CODE__BACK_BUTTON
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
        """Set up layout geometry, scroll state, and the blink thread.

        scroll_unit is the pixel distance per scroll step. The screen
        registers itself on the renderer when running under the screenshot
        generator so scrolled states can be captured, and starts a blink
        thread for the down chevron when the content overflows, hinting at
        more content below.
        """
        super().__post_init__()

        self.side_button_width = 20
        self.content_x = self.side_button_width
        self.content_width = self.canvas_width - 2 * self.side_button_width

        self.top_nav_height = GUIConstants.TOP_NAV_HEIGHT

        self.bottom_bar_height = 24
        self.content_y = self.top_nav_height + 2
        self.content_height = self.canvas_height - self.content_y - self.bottom_bar_height

        self.scroll_offset = 0
        self.scroll_unit = 36
        self.max_scroll = 0

        self._active_chevron = None
        self._active_scroll = None
        self._blink_state = False
        self._reached_bottom = False

        self._calculate_scroll()

        if self.renderer.is_screenshot_generator:
            self.renderer._scrollable_screen = self

        if self.max_scroll > 0:
            self.threads.append(self._BlinkThread(self))

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
        """Draw the top nav: a full-width progress bar with the title centered below it.

        The nav area is cleared first to prevent content bleed-through.
        """
        self.renderer.draw.rectangle(
            (0, 0, self.canvas_width, self.top_nav_height),
            fill=GUIConstants.BACKGROUND_COLOR,
        )

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
        """Draw the bottom bar: scroll percentage centered between the up
        chevron (at 1/4 screen width) and the down chevron (at 3/4).

        The bar is always cleared first to prevent content overflow. A
        chevron greys out at its scroll limit, and the down chevron blinks
        between accent shades until the user first reaches the bottom.
        """
        bar_top = self.canvas_height - self.bottom_bar_height
        self.renderer.draw.rectangle(
            (0, bar_top, self.canvas_width, self.canvas_height),
            fill=GUIConstants.BACKGROUND_COLOR,
        )

        if self.max_scroll <= 0:
            return

        mid_y = self.canvas_height - self.bottom_bar_height // 2

        pct = int(self.scroll_offset / self.max_scroll * 100) if self.max_scroll > 0 else 0
        pct_font = Fonts.get_font(
            GUIConstants.get_body_font_name(), GUIConstants.BODY_FONT_MIN_SIZE
        )
        self.renderer.draw.text(
            (self.canvas_width // 2, mid_y),
            f"{pct}%",
            font=pct_font,
            fill=GUIConstants.LABEL_FONT_COLOR,
            anchor="mm",
        )

        disabled_color = "#333333"

        cx = self.canvas_width // 4
        if self._active_scroll == "up":
            up_color = "#ffffff"
        elif self.scroll_offset > 0:
            up_color = GUIConstants.ACCENT_COLOR
        else:
            up_color = disabled_color
        self.renderer.draw.polygon(
            [(cx, mid_y - 5), (cx - 10, mid_y + 5), (cx + 10, mid_y + 5)],
            fill=up_color,
        )

        cx = 3 * self.canvas_width // 4
        if self._active_scroll == "down":
            down_color = "#ffffff"
        elif self.scroll_offset >= self.max_scroll:
            down_color = disabled_color
        elif not self._reached_bottom:
            down_color = GUIConstants.ACCENT_TEXT_COLOR if self._blink_state else GUIConstants.ACCENT_COLOR
        else:
            down_color = GUIConstants.ACCENT_COLOR
        self.renderer.draw.polygon(
            [(cx, mid_y + 5), (cx - 10, mid_y - 5), (cx + 10, mid_y - 5)],
            fill=down_color,
        )

    class _BlinkThread(BaseThread):
        """Blinks the down chevron to hint at scrollable content below."""
        def __init__(self, screen):
            super().__init__()
            self.screen = screen

        def run(self):
            while self.keep_running:
                time.sleep(0.4)
                if not self.keep_running:
                    break
                s = self.screen
                if s._reached_bottom or s.max_scroll <= 0 or s._active_scroll is not None:
                    continue
                s._blink_state = not s._blink_state
                with s.renderer.lock:
                    s._render_scroll_indicators()
                    s.renderer.show_image()

    def _run(self):
        """Input loop.

        Returns RET_CODE__LEFT_BUTTON or RET_CODE__RIGHT_BUTTON for chevron
        navigation, and RET_CODE__BACK_BUTTON when KEY1 (Back) is pressed.
        Up/down scroll the content and briefly highlight the pressed scroll
        chevron.
        """
        while True:
            with self.renderer.lock:
                self._render()
                self.renderer.show_image()

            user_input = self.hw_inputs.wait_for(HardwareButtonsConstants.ALL_KEYS)

            if user_input == HardwareButtonsConstants.KEY_LEFT:
                if self.has_left:
                    self._active_chevron = "left"
                    with self.renderer.lock:
                        self._render()
                        self.renderer.show_image()
                    return RET_CODE__LEFT_BUTTON
            elif user_input == HardwareButtonsConstants.KEY_RIGHT:
                if self.has_right:
                    self._active_chevron = "right"
                    with self.renderer.lock:
                        self._render()
                        self.renderer.show_image()
                    return RET_CODE__RIGHT_BUTTON
            elif user_input == HardwareButtonsConstants.KEY_UP:
                self.scroll_offset = max(0, self.scroll_offset - self.scroll_unit)
                self._active_scroll = "up"
                with self.renderer.lock:
                    self._render()
                    self.renderer.show_image()
                time.sleep(0.15)
                self._active_scroll = None
            elif user_input == HardwareButtonsConstants.KEY_DOWN:
                self.scroll_offset = min(
                    self.max_scroll, self.scroll_offset + self.scroll_unit
                )
                self._reached_bottom = True
                self._active_scroll = "down"
                with self.renderer.lock:
                    self._render()
                    self.renderer.show_image()
                time.sleep(0.15)
                self._active_scroll = None
            elif user_input == HardwareButtonsConstants.KEY1:
                return RET_CODE__BACK_BUTTON
