import os
import time
from datetime import datetime
from PIL import Image, ImageDraw
from .config_state import get_config
from small import Color, create_ssd1306


class OLEDDisplay:
    """OLED Display for Raspberry Pi 5 Ribbon Display"""

    def __init__(self, weather_provider):
        self.weather_provider = weather_provider
        self._bg_cache = None
        self._bg_path = None
        self._bg_mtime = None

        try:
            cfg = get_config()
            self.display = create_ssd1306(
                bus=cfg["oled"]["port"],
                address=cfg["oled"]["address"]
            )
            self.is_active = True
            print("✅ OLED display initialized successfully")
        except Exception as e:
            self.display = None
            self.is_active = False
            print(f"❌ OLED display initialization failed: {e}")
            print("Continuing with terminal UI only...")

        self.start_time = time.time()

    def clear(self):
        if self.is_active:
            self.display.clear()

    def show(self):
        if self.is_active:
            self.display.show()

    def _draw_text_box(self, text, x, y, font_size, padding=2):
        font = self.display._get_font(font_size)
        bbox = self.display.draw.textbbox((x, y), text, font=font)
        rect = (
            bbox[0] - padding,
            bbox[1] - padding,
            bbox[2] + padding,
            bbox[3] + padding,
        )
        self.display.draw.rectangle(rect, fill=Color.BLACK)
        self.display.draw.text((x, y), text, font=font, fill=Color.WHITE)

    def _draw_centered_text(self, text, y, font_size):
        font = self.display._get_font(font_size)
        bbox = self.display.draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        x = max(0, (self.display.width - text_width) // 2)
        self._draw_text_box(text, x, y, font_size)

    def _apply_background(self):
        cfg = get_config()
        bg_cfg = cfg.get("background", {})
        if not bg_cfg.get("enabled", False):
            return

        path = bg_cfg.get("path")
        if not path or not os.path.exists(path):
            return

        try:
            mtime = os.path.getmtime(path)
            if path != self._bg_path or mtime != self._bg_mtime:
                img = Image.open(path)
                img = img.resize((self.display.width, self.display.height), Image.LANCZOS)
                img = img.convert('1', dither=Image.FLOYDSTEINBERG)
                self._bg_cache = img
                self._bg_path = path
                self._bg_mtime = mtime

            if self._bg_cache is not None:
                self.display.buffer.paste(self._bg_cache, (0, 0))
                self.display.draw = ImageDraw.Draw(self.display.buffer)
        except Exception:
            return

    def draw_time_date(self):
        if not self.is_active:
            return

        cfg = get_config()
        font_sizes = cfg["oled"]["font_sizes"]

        now = datetime.now()
        time_str = now.strftime("%H:%M:%S")
        date_str = now.strftime("%b %d, %Y")

        self._draw_centered_text(time_str, 2, font_sizes["time"])
        self._draw_centered_text(date_str, 34, font_sizes["date"])

    def draw_weather(self):
        if not self.is_active:
            return

        cfg = get_config()
        font_sizes = cfg["oled"]["font_sizes"]
        weather = self.weather_provider.get_summary()
        self._draw_centered_text(weather, 48, font_sizes["weather"])

    def draw_all(self):
        if not self.is_active:
            return

        self.clear()
        self._apply_background()
        self.draw_time_date()
        self.draw_weather()
        self.show()

    def start(self):
        if not self.is_active:
            return

        try:
            while True:
                self.draw_all()
                time.sleep(get_config()["oled"].get("refresh_s", 1.0))
        except Exception as e:
            print(f"❌ OLED display error: {e}")
            self.is_active = False

    def stop(self):
        if self.is_active:
            self.display.cleanup()
