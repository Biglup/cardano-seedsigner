import logging
import os
import pathlib
import random
import time

from dataclasses import dataclass

from PIL import Image

from seedsigner.gui.components import Fonts, GUIConstants, load_image
from seedsigner.gui.screens.screen import BaseScreen
from seedsigner.views.view import View

logger = logging.getLogger(__name__)



# TODO: This early code is now outdated vis-a-vis Screen vs View distinctions
class LogoScreen(BaseScreen):
    def __init__(self):
        super().__init__()
        self.logo = load_image("logo_black_240.png")

    def _run(self):
        pass


@dataclass
class OpeningSplashView(View):
    def run(self):
        self.run_screen(OpeningSplashScreen)



class OpeningSplashScreen(LogoScreen):
    LOGO_VISIBLE_HEIGHT = 70

    def __init__(self):
        super().__init__()
        cometa_path = os.path.join(
            pathlib.Path(__file__).parent.resolve(), "..", "resources", "img", "cometa_py.png"
        )
        self.cometa_logo = Image.open(cometa_path).convert("RGBA")

    def _get_cometa_version(self) -> str:
        """Get cometa library version, with graceful fallback."""
        try:
            from cometa.cardano import get_lib_version
            return get_lib_version()
        except ImportError:
            return ""
        except Exception as e:
            logger.warning(f"Could not get cometa version: {e}")
            return ""

    def _render(self):
        from seedsigner.controller import Controller
        controller = Controller.get_instance()

        self.clear_screen()

        center_x = self.canvas_width // 2

        logo_offset_y = -20
        logo_offset_x = (self.canvas_width - self.logo.width) // 2

        background = Image.new("RGBA", size=self.logo.size, color=GUIConstants.BACKGROUND_COLOR)
        if not self.renderer.is_screenshot_generator:
            for i in range(250, -1, -25):
                self.logo.putalpha(255 - i)
                self.renderer.canvas.paste(
                    Image.alpha_composite(background, self.logo),
                    (logo_offset_x, logo_offset_y)
                )
                self.renderer.show_image()
        else:
            self.renderer.canvas.paste(self.logo, (logo_offset_x, logo_offset_y))

        version_font = Fonts.get_font(GUIConstants.get_body_font_name(), GUIConstants.get_top_nav_title_font_size())
        version_text = f"v{controller.VERSION}"
        version_y = (self.canvas_height // 2) + (self.LOGO_VISIBLE_HEIGHT // 2) + logo_offset_y + GUIConstants.COMPONENT_PADDING
        self.renderer.draw.text(
            xy=(center_x, version_y), text=version_text,
            font=version_font, fill=GUIConstants.ACCENT_TEXT_COLOR, anchor="mt",
        )

        cometa_version = self._get_cometa_version()
        small_font = Fonts.get_font(GUIConstants.get_body_font_name(), 15)

        powered_label = "Powered by"
        cometa_name = "Cometa.py"
        cometa_ver_label = f" {cometa_version}" if cometa_version else ""
        name_text = f"{cometa_name}{cometa_ver_label}"

        label_bbox = small_font.getbbox(powered_label)
        label_h = label_bbox[3] - label_bbox[1]
        name_bbox = small_font.getbbox(name_text)
        name_w = name_bbox[2] - name_bbox[0]
        name_h = name_bbox[3] - name_bbox[1]

        line_gap = 3
        text_block_h = label_h + line_gap + name_h
        scale = text_block_h / self.cometa_logo.height
        scaled_logo_w = max(1, int(self.cometa_logo.width * scale))
        scaled_logo_h = max(1, int(self.cometa_logo.height * scale))
        scaled_cometa = self.cometa_logo.resize((scaled_logo_w, scaled_logo_h), Image.LANCZOS)

        # Text is centered on screen; logo sits to the left of the wider text line
        gap = 6
        label_w = label_bbox[2] - label_bbox[0]
        wider_text_w = max(name_w, label_w)
        # Left edge of the wider text line when centered
        text_left_edge = (self.canvas_width - wider_text_w) // 2
        logo_x = text_left_edge - gap - scaled_logo_w
        block_y = self.canvas_height - scaled_logo_h - GUIConstants.COMPONENT_PADDING

        from PIL import ImageDraw
        temp = Image.new("RGBA", self.renderer.canvas.size, (0, 0, 0, 0))
        temp.paste(scaled_cometa, (logo_x, block_y))
        composited = Image.alpha_composite(
            self.renderer.canvas.convert("RGBA"), temp
        ).convert("RGB")
        # Paste in-place to preserve canvas object identity (important for
        # components that cache a reference to renderer.canvas).
        self.renderer.canvas.paste(composited)
        self.renderer.draw = ImageDraw.Draw(self.renderer.canvas)

        text_top = block_y + (scaled_logo_h - text_block_h) // 2
        self.renderer.draw.text(
            xy=(center_x, text_top), text=powered_label,
            font=small_font, fill=GUIConstants.PRIMARY_COLOR, anchor="mt",
        )
        # Draw "Cometa.py" in white and version in accent blue
        line2_y = text_top + label_h + line_gap
        name_only_bbox = small_font.getbbox(cometa_name)
        name_only_w = name_only_bbox[2] - name_only_bbox[0]
        # Center the full name_text, then split drawing at the boundary
        line2_left = center_x - name_w // 2
        self.renderer.draw.text(
            xy=(line2_left, line2_y), text=cometa_name,
            font=small_font, fill=GUIConstants.PRIMARY_COLOR, anchor="lt",
        )
        if cometa_ver_label:
            self.renderer.draw.text(
                xy=(line2_left + name_only_w, line2_y), text=cometa_ver_label,
                font=small_font, fill=GUIConstants.ACCENT_TEXT_COLOR, anchor="lt",
            )

        if not self.renderer.is_screenshot_generator:
            self.renderer.show_image()
            time.sleep(2)



class ScreensaverScreen(LogoScreen):
    def __init__(self, buttons):
        super().__init__()

        self.buttons = buttons

        # Paste the logo in a bigger image that is the canvas + the logo dims (half the
        # logo will render off the canvas at each edge).
        self.image = Image.new("RGB", (self.renderer.canvas_width + self.logo.width, self.renderer.canvas_height + self.logo.height), (0,0,0))

        # Place the logo centered on the larger image
        logo_x = int((self.image.width - self.logo.width) / 2)
        logo_y = int((self.image.height - self.logo.height) / 2)
        self.image.paste(self.logo, (logo_x, logo_y))

        self.min_coords = (0, 0)
        self.max_coords = (self.renderer.canvas_width, self.renderer.canvas_height)

        # Update our first rendering position so we're centered
        self.cur_x = int(self.logo.width / 2)
        self.cur_y = int(self.logo.height / 2)

        self.increment_x = self.rand_increment()
        self.increment_y = self.rand_increment()

        self._is_running = False
        self.last_screen = None


    @property
    def is_running(self):
        return self._is_running
    

    def rand_increment(self):
        max_increment = 10.0
        min_increment = 1.0
        increment = random.uniform(min_increment, max_increment)
        if random.uniform(-1.0, 1.0) < 0.0:
            return -1.0 * increment
        return increment


    def start(self):
        if self.is_running:
            return

        self._is_running = True

        # Store the current screen in order to restore it later
        self.last_screen = self.renderer.canvas.copy()

        screensaver_start = int(time.time() * 1000)

        # Screensaver must block any attempts to use the Renderer in another thread so it
        # never gives up the lock until it returns.
        with self.renderer.lock:
            try:
                while self._is_running:
                    if self.buttons.has_any_input() or self.buttons.override_ind:
                        break

                    # Must crop the image to the exact display size
                    crop = self.image.crop((
                        self.cur_x, self.cur_y,
                        self.cur_x + self.renderer.canvas_width, self.cur_y + self.renderer.canvas_height))
                    self.renderer.disp.show_image(crop, 0, 0)

                    self.cur_x += self.increment_x
                    self.cur_y += self.increment_y

                    # At each edge bump, calculate a new random rate of change for that axis
                    if self.cur_x < self.min_coords[0]:
                        self.cur_x = self.min_coords[0]
                        self.increment_x = self.rand_increment()
                        if self.increment_x < 0.0:
                            self.increment_x *= -1.0
                    elif self.cur_x > self.max_coords[0]:
                        self.cur_x = self.max_coords[0]
                        self.increment_x = self.rand_increment()
                        if self.increment_x > 0.0:
                            self.increment_x *= -1.0

                    if self.cur_y < self.min_coords[1]:
                        self.cur_y = self.min_coords[1]
                        self.increment_y = self.rand_increment()
                        if self.increment_y < 0.0:
                            self.increment_y *= -1.0
                    elif self.cur_y > self.max_coords[1]:
                        self.cur_y = self.max_coords[1]
                        self.increment_y = self.rand_increment()
                        if self.increment_y > 0.0:
                            self.increment_y *= -1.0

            except KeyboardInterrupt as e:
                # Exit triggered; close gracefully
                logger.info("Shutting down Screensaver")

                # Have to let the interrupt bubble up to exit the main app
                raise e

            finally:
                self._is_running = False

                # Restore the original screen
                self.renderer.show_image(self.last_screen)



    def stop(self):
        self._is_running = False


