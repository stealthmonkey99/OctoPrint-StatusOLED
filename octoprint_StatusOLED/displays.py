from abc import ABC, abstractmethod
import logging

try:
    from board import SCL, SDA
    import busio
    import adafruit_ssd1306
    I2C_AVAILABLE = True
except ImportError:
    I2C_AVAILABLE = False

import os
import io
import base64
from PIL import Image, ImageDraw, ImageFont
from threading import Thread
import time

PIOLED_WIDTH = 128
PIOLED_HEIGHT = 64

ANIMATION_DELAY = 0.05   # 20fps
ANIMATION_SPEED_XSLOW = 1
ANIMATION_SPEED_XFAST = 18

FONT_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), "static/ttf")

class DisplayImage():
    def __init__(
        self,
        font_name, font_size,
        sec_font_name = None, sec_font_size = None,
        animation_loops = None, animation_speed = None,
        progbar_enabled = None, progbar_outline = None, progbar_size = None,
        printer = None
    ):
        self._logger = logging.getLogger(__name__+"."+self.__class__.__name__)

        # Create blank image and drawing object
        self._monoImage = Image.new("1", (PIOLED_WIDTH, PIOLED_HEIGHT))
        self._alphaImage = None
        self._draw = ImageDraw.Draw(self._monoImage)
        self._font = None
        self._secondary_font = None
        self._texts = []
        self._progress = 0.0
        self._progress_bar_enabled = True
        self._progress_bar_outline = 0
        self._progress_bar_height = 6
        self._printer = printer
        self._animation_running = False
        self._animation_thread = None
        self._animation_x = 0
        self._animation_y = 0
        self._animation_w = 0
        self._animation_loops = 0
        self._animation_signal = None
        self._animation_settings_loops = 0
        self._animation_settings_speed = 0

        self.set_settings(font_name, font_size, sec_font_name, sec_font_size, animation_loops, animation_speed, progbar_enabled, progbar_outline, progbar_size)

    def debug(self, enabled):
        self._logger.setLevel(level=logging.DEBUG if enabled else logging.NOTSET)

    def set_settings(
        self,
        font_name, font_size,
        sec_font_name = None, sec_font_size = None,
        animation_loops = 0, animation_speed = ANIMATION_SPEED_XSLOW,
        progbar_enabled = True, progbar_outline = True, progbar_size = 6
    ):
        if font_name is not None and font_name != "default" and font_size is not None:
            self._font = ImageFont.truetype(os.path.join(FONT_DIR, font_name), int(font_size))
        else:
            self._font = ImageFont.load_default()

        if sec_font_name is not None and sec_font_name != "default" and sec_font_size is not None:
            self._secondary_font = ImageFont.truetype(os.path.join(FONT_DIR, sec_font_name), int(sec_font_size))
        else:
            self._secondary_font = ImageFont.load_default()

        self._animation_settings_loops = animation_loops
        self._animation_settings_speed = animation_speed

        self._progress_bar_enabled = bool(progbar_enabled)
        self._progress_bar_outline = 0 if bool(progbar_outline) else 1
        self._progress_bar_height = int(progbar_size)

        # Update the image in case any settings have changed
        if len(self._texts) > 0:
            self.show_text()
        if self._progress > 0:
            self.show_progress()

    def show_text(self, text = None, signal_animation = None):
        # add text to head of array
        if text is not None:
            self._texts[0:0] = text.split("\n")

        # clear the drawing to start
        self._draw.rectangle((0, 0, PIOLED_WIDTH, PIOLED_HEIGHT), outline=0, fill=0)

        # draw as many lines of text as will fit
        index = 0
        ox, oy = (0, 0)
        while index < len(self._texts) and oy < PIOLED_HEIGHT - 2:
            line_font = self._font if index == 0 else self._secondary_font
            if hasattr(line_font, "getbbox"):
                bbox = self._draw.textbbox((ox, oy), self._texts[index], font=line_font, anchor="lt")
            else:
                w, h = self._draw.textsize(self._texts[index], font=line_font)
                bbox = (ox, oy, ox + w, oy + h)
            bbx, bby, bbw, bbh = bbox
            self._draw.text((ox, oy), self._texts[index], font=line_font, fill=1, anchor="lt")
            if index == 0 and signal_animation is not None:
                if bbw > PIOLED_WIDTH:
                    if self._animation_settings_loops > 0:
                        self._logger.warn("Text '%s' is %dpx wide, will need to animate on a new thread..." % (self._texts[index], bbw))
                        self._start_animation(bbx, bby, bbw - bbx, bbh - bby, signal_animation)
                    else:
                        self._logger.warn("Text '%s' is %dpx wide and will be truncated (animation disabled)" % (self._texts[index], bbw))
                else:
                    self._stop_animation()
            oy = bbh + 1
            index += 1

    def _start_animation(self, x, y, width, height, signal):
        # reset the animation parameters
        self._animation_x = x
        self._animation_y = y
        self._animation_w = width
        self._animation_h = height
        self._animation_loops = self._animation_settings_loops
        self._animation_signal = signal

        # if we're not already animating, start a new thread to begin doing so now
        if self._animation_thread is not None and self._animation_thread.is_alive():
            return

        self._animation_running = True
        self._animation_thread = Thread(target=self._animation_worker)
        self._animation_thread.start()
        self._logger.debug("forked a new animation thread (id: {0})".format(self._animation_thread.ident))

    def _stop_animation(self):
        self._animation_running = False

    def _animation_worker(self):
        self._logger.debug("animation loops remaining: %d" % self._animation_loops)
        while self._animation_running:
            time.sleep(ANIMATION_DELAY)
            if not self._animation_running:
                break

            # do the next animation step:
            self._animation_x -= self._animation_settings_speed
            if self._animation_x < (0 - self._animation_w):
                self._animation_loops -= 1
                self._animation_x = PIOLED_WIDTH
                self._logger.debug("animation loops remaining: %d" % self._animation_loops)
            if self._animation_loops <= 0 and self._animation_x <= 0:
                self._logger.debug("animation stopping.")
                self._animation_x = 0
                self._stop_animation()
            self._draw.rectangle((0, self._animation_y, PIOLED_WIDTH, self._animation_h), outline=0, fill=0)
            self._draw.text((self._animation_x, self._animation_y), self._texts[0], font=self._font, fill=1, anchor="lt")
            if self._animation_signal is not None:
                self._animation_signal()

        self._logger.debug("exiting animation thread (id: {0})".format(self._animation_thread.ident))

    def show_progress(self, progress = None):
        if progress is None:
            if self._printer is not None and self._printer.is_ready():
                return
            progress = self._progress
        progress = min(100.0, max(0.0, progress))
        self._progress = progress
        progheight = min(PIOLED_HEIGHT, max(4, self._progress_bar_height))

        if not self._progress_bar_enabled:
            return

        self._draw.rectangle((-1, PIOLED_HEIGHT - 2 - progheight, PIOLED_WIDTH + 1, PIOLED_HEIGHT + 1), outline=0, fill=1)
        self._draw.rectangle((0, PIOLED_HEIGHT - 1 - progheight, PIOLED_WIDTH-1, PIOLED_HEIGHT-1), outline=1, fill=0)
        self._draw.rectangle((1, PIOLED_HEIGHT - progheight, int(1 + ((PIOLED_WIDTH - 3) * progress / 100)), PIOLED_HEIGHT - 2), outline=self._progress_bar_outline, fill=1)

    def get_mono_image(self):
        return self._monoImage

    def get_alpha_image(self):
        if self._alphaImage is None:
            self._alphaImage = Image.new("RGBA", (PIOLED_WIDTH, PIOLED_HEIGHT))

        # Convert the 1-bit image to a black-and-alpha image
        pixels = []
        for pixel in self._monoImage.getdata():
            pixels.append((0, 0, 0, 255) if pixel == 0 else (255, 255, 255, 0))
        self._alphaImage.putdata(pixels)

        return self._alphaImage

    def get_alpha_buffer(self):
        buffer = io.BytesIO()
        self.get_alpha_image().save(buffer, "PNG")
        buffer.seek(0)
        return buffer

class Display(ABC):
    def __init__(self):
        pass

    @abstractmethod
    def is_enabled():
        pass

    @abstractmethod
    def clear():
        pass

    @abstractmethod
    def update():
        pass

class HardwareDisplay(Display):
    def __init__(self, img, enabled, rotated_180):
        self._logger = logging.getLogger(__name__+"."+self.__class__.__name__)

        self._i2c = None
        self._disp = None
        self._dispImg = img

        self.set_settings(enabled, rotated_180)
        self.clear()

    def debug(self, enabled):
        self._logger.setLevel(level=logging.DEBUG if enabled else logging.NOTSET)

    def Available():
        return I2C_AVAILABLE

    def set_settings(self, enabled, rotated_180):
        if enabled is not None:
            self._enabled = bool(enabled)
        if rotated_180 is not None:
            self._rotated_180 = bool(rotated_180)

        self._logger.info("HardwareDisplay set to enabled {self._enabled} rotated_180 {self._rotated_180}".format(**locals()))
        self.initDisplay()

    def is_enabled(self):
        return HardwareDisplay.Available() and self._enabled

    def initDisplay(self):
        if not self.is_enabled():
            self.clear()
            return

        # Create the I2C interface.
        if self._i2c is None:
            self._i2c = busio.I2C(SCL, SDA)

        # Create the SSD1306 OLED class.
        if self._disp is None:
            self._disp = adafruit_ssd1306.SSD1306_I2C(PIOLED_WIDTH, PIOLED_HEIGHT, self._i2c)

        self._disp.rotation = 2 if self._rotated_180 else 0
        self.update()

    def clear(self):
        if self._disp is None:
            return

        # Clear display.
        self._disp.fill(0)
        self._disp.show()

    def update(self):
        if not self.is_enabled() or self._disp is None:
            return

        self._disp.image(self._dispImg.get_mono_image())
        self._disp.show()

class SoftwareDisplay(Display):
    def __init__(self, img, pushDisplayFunc, enabled):
        self._logger = logging.getLogger(__name__+"."+self.__class__.__name__)

        self._dispImg = img
        self._pushDisplayFunc = pushDisplayFunc
        self._cleared = Image.new("1", (PIOLED_WIDTH, PIOLED_HEIGHT), 0)

        self.set_settings(enabled)
        self.clear()

    def debug(self, enabled):
        self._logger.setLevel(level=logging.DEBUG if enabled else logging.NOTSET)

    def set_settings(self, enabled):
        if enabled is not None:
            self._enabled = bool(enabled)

        self._logger.info("SoftwareDisplay set to enabled {self._enabled}".format(**locals()))
        self.update()

    def is_enabled(self):
        return self._enabled

    def clear(self):
        buffer = io.BytesIO()
        self._cleared.save(buffer, "PNG")
        img_base64 = bytes("data:image/png;base64,", encoding='utf-8') + base64.b64encode(buffer.getvalue())
        self._pushDisplayFunc(img_base64)

    def update(self):
        if not self.is_enabled():
            return

        img_base64 = bytes("data:image/png;base64,", encoding='utf-8') + base64.b64encode(self._dispImg.get_alpha_buffer().getvalue())
        self._pushDisplayFunc(img_base64)
