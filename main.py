#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Raspberry Pi 5 Ribbon Display - Tim
Combined terminal UI, OLED display, and simple web config
"""

import time
import sys
import os
import threading
import json
import copy
import subprocess
import shutil
import math
import wave
import struct
from datetime import datetime
from urllib.request import urlopen
from urllib.parse import urlencode
from PIL import Image, ImageDraw
from flask import Flask, request
from small import Color, create_ssd1306

# ====================
# Paths + Config
# ====================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
ASSETS_DIR = os.path.join(BASE_DIR, "config")
BACKGROUND_PATH = os.path.join(ASSETS_DIR, "background.png")
BOOT_SOUND_PATH = os.path.join(ASSETS_DIR, "boot.wav")
DEFAULT_AVIF_PATH = os.path.join(BASE_DIR, "defalt.avif")

DEFAULT_CONFIG = {
    "terminal": {
        "font_size": 24,
        "colors": [
            "\033[91m",  # Red
            "\033[92m",  # Green
            "\033[93m",  # Yellow
            "\033[94m",  # Blue
            "\033[95m",  # Magenta
            "\033[96m",  # Cyan
            "\033[97m",  # White
        ],
        "refresh_s": 1.0,
        "clear_screen": True,
    },
    "oled": {
        "interface": "i2c",
        "port": 1,
        "address": 0x3C,
        "width": 128,
        "height": 64,
        "rotate": 0,
        "refresh_s": 1.0,
        "font_sizes": {
            "time": 28,
            "date": 12,
            "weather": 12,
        },
    },
    "weather": {
        "enabled": True,
        "latitude": 37.7749,
        "longitude": -122.4194,
        "units": "imperial",  # imperial or metric
        "refresh_s": 300,
    },
    "background": {
        "enabled": True,
        "path": BACKGROUND_PATH,
    },
    "audio": {
        "enabled": True,
        "path": BOOT_SOUND_PATH,
    },
    "web": {
        "config_port": 5000,
        "reboot_port": 500,
    },
}

CONFIG_LOCK = threading.Lock()
CONFIG = {}


def _deep_update(target, updates):
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _deep_update(target[key], value)
        else:
            target[key] = value


def load_config():
    config = copy.deepcopy(DEFAULT_CONFIG)
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                saved = json.load(f)
            _deep_update(config, saved)
        except Exception as e:
            print(f"⚠️  Failed to load config.json, using defaults: {e}")
    return config


def save_config(config):
    os.makedirs(ASSETS_DIR, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


def get_config():
    with CONFIG_LOCK:
        return copy.deepcopy(CONFIG)


def update_config(patch):
    with CONFIG_LOCK:
        _deep_update(CONFIG, patch)
        save_config(CONFIG)


def ensure_default_assets():
    os.makedirs(ASSETS_DIR, exist_ok=True)

    if not os.path.exists(BACKGROUND_PATH) and os.path.exists(DEFAULT_AVIF_PATH):
        try:
            img = Image.open(DEFAULT_AVIF_PATH)
            img.save(BACKGROUND_PATH, format="PNG")
            print("✅ Converted defalt.avif to background.png")
        except Exception as e:
            print(f"⚠️  Failed to convert defalt.avif: {e}")

    if not os.path.exists(BOOT_SOUND_PATH):
        try:
            _write_default_beep(BOOT_SOUND_PATH)
            print("✅ Wrote default boot beep")
        except Exception as e:
            print(f"⚠️  Failed to write default boot beep: {e}")


def _write_default_beep(path):
    sample_rate = 44100
    duration_s = 0.18
    frequency = 880.0
    amplitude = 0.4
    frames = int(sample_rate * duration_s)
    with wave.open(path, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        for i in range(frames):
            t = i / sample_rate
            sample = amplitude * math.sin(2 * math.pi * frequency * t)
            wf.writeframes(struct.pack("<h", int(sample * 32767)))


# ====================
# System Information
# ====================

def get_system_info():
    """Get system information"""
    try:
        temp_file = "/sys/class/thermal/thermal_zone0/temp"
        if os.path.exists(temp_file):
            with open(temp_file, 'r') as f:
                temp = int(f.read()) / 1000.0
            cpu_temp = f"{temp:.1f}°C"
        else:
            cpu_temp = "N/A"

        mem_info = os.popen('free -m').read().split()
        if len(mem_info) > 10:
            mem_used = int(mem_info[8])
            mem_total = int(mem_info[7])
            mem_percent = (mem_used / mem_total) * 100
            memory = f"{mem_used}/{mem_total} MB ({mem_percent:.0f}%)"
        else:
            memory = "N/A"

        return cpu_temp, memory

    except Exception as e:
        return f"Error: {e}", "N/A"


# ====================
# Weather
# ====================

WEATHER_CODES = {
    0: "Clear",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Rime fog",
    51: "Light drizzle",
    53: "Drizzle",
    55: "Heavy drizzle",
    56: "Freezing drizzle",
    57: "Freezing drizzle",
    61: "Light rain",
    63: "Rain",
    65: "Heavy rain",
    66: "Freezing rain",
    67: "Freezing rain",
    71: "Light snow",
    73: "Snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Rain showers",
    81: "Rain showers",
    82: "Violent showers",
    85: "Snow showers",
    86: "Snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm hail",
    99: "Thunderstorm hail",
}


class WeatherProvider:
    def __init__(self, config_getter):
        self.config_getter = config_getter
        self._lock = threading.Lock()
        self._summary = "Weather: --"
        self._last_update = 0
        self._stop = threading.Event()
        self._thread = None

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1)

    def _set_summary(self, text):
        with self._lock:
            self._summary = text

    def get_summary(self):
        with self._lock:
            return self._summary

    def _run(self):
        while not self._stop.is_set():
            cfg = self.config_getter()
            weather_cfg = cfg["weather"]

            if not weather_cfg.get("enabled", True):
                self._set_summary("Weather: off")
                time.sleep(5)
                continue

            now = time.time()
            if now - self._last_update >= weather_cfg.get("refresh_s", 300):
                summary = self._fetch_weather(weather_cfg)
                self._set_summary(summary)
                self._last_update = now

            time.sleep(5)

    def _fetch_weather(self, weather_cfg):
        try:
            lat = weather_cfg.get("latitude")
            lon = weather_cfg.get("longitude")
            units = weather_cfg.get("units", "imperial")

            temp_unit = "fahrenheit" if units == "imperial" else "celsius"
            params = {
                "latitude": lat,
                "longitude": lon,
                "current_weather": "true",
                "temperature_unit": temp_unit,
                "timezone": "auto",
            }
            url = f"https://api.open-meteo.com/v1/forecast?{urlencode(params)}"

            with urlopen(url, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            temp = None
            code = None

            if "current_weather" in data:
                temp = data["current_weather"].get("temperature")
                code = data["current_weather"].get("weathercode")
            elif "current" in data:
                temp = data["current"].get("temperature_2m")
                code = data["current"].get("weather_code")

            if temp is None:
                return "Weather: --"

            unit_symbol = "°F" if units == "imperial" else "°C"
            desc = WEATHER_CODES.get(code, "Weather")
            return f"{temp:.0f}{unit_symbol} {desc}"
        except Exception:
            return "Weather: --"


# ====================
# Terminal UI Class
# ====================
class TerminalUI:
    """Terminal UI for Raspberry Pi 5 Ribbon Display"""

    def __init__(self, config_getter, weather_provider):
        self.width = 80
        self.height = 24
        self.start_time = time.time()
        self.config_getter = config_getter
        self.weather_provider = weather_provider

    def _update_terminal_size(self):
        try:
            size = os.get_terminal_size()
            self.width = size.columns
            self.height = size.lines
        except OSError:
            pass

    def clear_screen(self):
        """Clear the terminal screen"""
        os.system("cls" if os.name == "nt" else "clear")

    def reset_cursor(self):
        print("\033[H", end="")

    def center_text(self, text, width=None):
        """Center text horizontally"""
        if width is None:
            width = self.width
        return text.center(width)

    def draw_header(self):
        """Draw the main header"""
        colors = get_config()["terminal"]["colors"]
        header_text = "RASPBERRY PI 5 RIBBON DISPLAY"
        line = f"{colors[3]}" + "═" * self.width
        print(line)
        print(f"{colors[6]}\033[1m{self.center_text(header_text)}\033[0m")
        print(line)

    def draw_time_date(self):
        """Draw big time and date display"""
        colors = get_config()["terminal"]["colors"]

        now = datetime.now()
        time_str = now.strftime("%H:%M:%S")
        date_str = now.strftime("%A, %B %d, %Y")

        print(f"\n{colors[2]}\033[1m{self.center_text(time_str, 40)}\033[0m")
        print(f"{colors[4]}{self.center_text(date_str)}")

    def draw_weather(self):
        colors = get_config()["terminal"]["colors"]
        weather = self.weather_provider.get_summary()
        print(f"{colors[5]}\033[1m{self.center_text(weather)}\033[0m")

    def draw_system_info(self):
        """Draw system information"""
        colors = get_config()["terminal"]["colors"]
        cpu_temp, memory = get_system_info()

        info_text = (
            f"{colors[1]}CPU: {cpu_temp} | "
            f"{colors[5]}RAM: {memory} | "
            f"{colors[3]}UP: {self.get_uptime()}"
        )

        print(f"\n{colors[6]}" + "─" * self.width)
        print(f"{colors[6]}{self.center_text(info_text)}")
        print(f"{colors[6]}" + "─" * self.width)

    def get_uptime(self):
        """Get system uptime"""
        uptime_seconds = int(time.time() - self.start_time)
        hours, remainder = divmod(uptime_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def draw_all(self):
        """Draw complete display"""
        cfg = get_config()
        self._update_terminal_size()
        if cfg["terminal"].get("clear_screen", True):
            self.clear_screen()
        else:
            self.reset_cursor()
        self.draw_header()
        self.draw_time_date()
        self.draw_weather()
        self.draw_system_info()

    def start(self):
        """Start the terminal display"""
        print("\033[?1049h\033[?25l")  # Alt screen + hide cursor

        try:
            while True:
                self.draw_all()
                time.sleep(get_config()["terminal"].get("refresh_s", 1.0))

        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        """Stop the terminal display"""
        print("\033[?25h\033[?1049l")  # Show cursor + leave alt screen
        self.clear_screen()
        print("👋 Terminal display stopped!")


# ====================
# OLED Display Class
# ====================
class OLEDDisplay:
    """OLED Display for Raspberry Pi 5 Ribbon Display"""

    def __init__(self, config_getter, weather_provider):
        self.config_getter = config_getter
        self.weather_provider = weather_provider
        self._bg_cache = None
        self._bg_path = None
        self._bg_mtime = None

        try:
            cfg = self.config_getter()
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
        """Clear the OLED display"""
        if self.is_active:
            self.display.clear()

    def show(self):
        """Update the OLED display"""
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
        cfg = self.config_getter()
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
        """Draw time and date on OLED"""
        if not self.is_active:
            return

        cfg = self.config_getter()
        font_sizes = cfg["oled"]["font_sizes"]

        now = datetime.now()
        time_str = now.strftime("%H:%M:%S")
        date_str = now.strftime("%b %d, %Y")

        self._draw_centered_text(time_str, 2, font_sizes["time"])
        self._draw_centered_text(date_str, 34, font_sizes["date"])

    def draw_weather(self):
        if not self.is_active:
            return

        cfg = self.config_getter()
        font_sizes = cfg["oled"]["font_sizes"]
        weather = self.weather_provider.get_summary()
        self._draw_centered_text(weather, 48, font_sizes["weather"])

    def get_uptime(self):
        """Get system uptime"""
        uptime_seconds = int(time.time() - self.start_time)
        hours, remainder = divmod(uptime_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def draw_all(self):
        """Draw complete OLED display"""
        if not self.is_active:
            return

        self.clear()
        self._apply_background()
        self.draw_time_date()
        self.draw_weather()
        self.show()

    def start(self):
        """Start the OLED display"""
        if not self.is_active:
            return

        try:
            while True:
                self.draw_all()
                time.sleep(self.config_getter()["oled"].get("refresh_s", 1.0))

        except Exception as e:
            print(f"❌ OLED display error: {e}")
            self.is_active = False

    def stop(self):
        """Stop the OLED display"""
        if self.is_active:
            self.display.cleanup()


# ====================
# Web Config + Reboot
# ====================

class ConfigWebServer:
    def __init__(self, config_getter, config_updater):
        self.config_getter = config_getter
        self.config_updater = config_updater
        self.app = Flask(__name__)
        self._setup_routes()

    def _setup_routes(self):
        @self.app.get("/")
        def index():
            cfg = self.config_getter()
            weather = cfg["weather"]
            bg = cfg["background"]
            audio = cfg.get("audio", {})

            return f"""
            <html>
                <head><title>Display Config</title></head>
                <body style="font-family: sans-serif; max-width: 600px; margin: 24px auto;">
                    <h2>Display Config</h2>
                    <form action="/save" method="post" enctype="multipart/form-data">
                        <h3>Weather</h3>
                        <label>Latitude: <input name="lat" value="{weather['latitude']}" /></label><br/>
                        <label>Longitude: <input name="lon" value="{weather['longitude']}" /></label><br/>
                        <label>Units:
                            <select name="units">
                                <option value="imperial" {'selected' if weather['units']=='imperial' else ''}>Imperial (°F)</option>
                                <option value="metric" {'selected' if weather['units']=='metric' else ''}>Metric (°C)</option>
                            </select>
                        </label><br/>
                        <label>Enable Weather: <input type="checkbox" name="weather_enabled" {'checked' if weather.get('enabled', True) else ''}/></label>

                        <h3>Background Image (OLED)</h3>
                        <label>Enable Background: <input type="checkbox" name="bg_enabled" {'checked' if bg.get('enabled', False) else ''}/></label><br/>
                        <input type="file" name="background" accept="image/*" /><br/>
                        <small>Current: {bg.get('path')}</small><br/><br/>

                        <h3>Boot Sound</h3>
                        <label>Enable Boot Sound: <input type="checkbox" name="audio_enabled" {'checked' if audio.get('enabled', True) else ''}/></label><br/>
                        <input type="file" name="boot_sound" accept="audio/*" /><br/>
                        <small>Current: {audio.get('path')}</small><br/><br/>

                        <button type="submit">Save</button>
                    </form>
                </body>
            </html>
            """

        @self.app.post("/save")
        def save():
            os.makedirs(ASSETS_DIR, exist_ok=True)

            weather_enabled = True if request.form.get("weather_enabled") else False
            bg_enabled = True if request.form.get("bg_enabled") else False
            audio_enabled = True if request.form.get("audio_enabled") else False

            try:
                lat = float(request.form.get("lat", "0"))
                lon = float(request.form.get("lon", "0"))
            except ValueError:
                lat, lon = 0.0, 0.0

            units = request.form.get("units", "imperial")

            file = request.files.get("background")
            if file and file.filename:
                file.save(BACKGROUND_PATH)

            audio_file = request.files.get("boot_sound")
            if audio_file and audio_file.filename:
                audio_file.save(BOOT_SOUND_PATH)

            self.config_updater({
                "weather": {
                    "enabled": weather_enabled,
                    "latitude": lat,
                    "longitude": lon,
                    "units": units,
                },
                "background": {
                    "enabled": bg_enabled,
                    "path": BACKGROUND_PATH,
                },
                "audio": {
                    "enabled": audio_enabled,
                    "path": BOOT_SOUND_PATH,
                },
            })

            return "<p>Saved. <a href='/'>Back</a></p>"

    def start(self):
        cfg = self.config_getter()
        port = cfg["web"].get("config_port", 5000)
        threading.Thread(
            target=self.app.run,
            kwargs={"host": "0.0.0.0", "port": port, "debug": False, "use_reloader": False},
            daemon=True,
        ).start()


class RebootWebServer:
    def __init__(self, config_getter):
        self.config_getter = config_getter
        self.app = Flask("reboot")
        self._setup_routes()

    def _setup_routes(self):
        @self.app.get("/")
        def index():
            return (
                "<html><body style='font-family: sans-serif; max-width: 480px; margin: 24px auto;'>"
                "<h2>Reboot Device</h2>"
                "<form action='/reboot' method='post'>"
                "<button type='submit'>Reboot Now</button>"
                "</form>"
                "</body></html>"
            )

        @self.app.post("/reboot")
        def reboot():
            threading.Thread(target=self._do_reboot, daemon=True).start()
            return "<p>Reboot command sent.</p>"

    def _do_reboot(self):
        try:
            subprocess.Popen(["sudo", "/sbin/reboot"])
        except Exception as e:
            print(f"❌ Reboot failed: {e}")

    def start(self):
        cfg = self.config_getter()
        port = cfg["web"].get("reboot_port", 500)
        threading.Thread(
            target=self.app.run,
            kwargs={"host": "0.0.0.0", "port": port, "debug": False, "use_reloader": False},
            daemon=True,
        ).start()


# ====================
# Combined Display
# ====================
class CombinedDisplay:
    """Combined terminal and OLED display"""

    def __init__(self):
        self.weather_provider = WeatherProvider(get_config)
        self.terminal_ui = TerminalUI(get_config, self.weather_provider)
        self.oled_display = OLEDDisplay(get_config, self.weather_provider)
        self.config_server = ConfigWebServer(get_config, update_config)
        self.reboot_server = RebootWebServer(get_config)
        self.running = False
        self.terminal_thread = None
        self.oled_thread = None

    def start_terminal(self):
        """Start terminal UI in thread"""
        try:
            self.terminal_ui.start()
        except Exception as e:
            print(f"❌ Terminal UI error: {e}")

    def start_oled(self):
        """Start OLED display in thread"""
        self.oled_display.start()

    def start(self):
        """Start both displays"""
        self.running = True

        print("🚀 Initializing Raspberry Pi 5 Ribbon Display...")
        time.sleep(1)

        ensure_default_assets()
        self._play_boot_sound()
        self.weather_provider.start()
        self.config_server.start()
        self.reboot_server.start()

        self.terminal_thread = threading.Thread(
            target=self.start_terminal,
            daemon=True
        )
        self.terminal_thread.start()

        if self.oled_display.is_active:
            self.oled_thread = threading.Thread(
                target=self.start_oled,
                daemon=True
            )
            self.oled_thread.start()

        try:
            while self.running:
                time.sleep(1)

        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        """Stop all displays"""
        self.running = False
        self.weather_provider.stop()
        self.terminal_ui.stop()
        self.oled_display.stop()

        if self.oled_thread and self.oled_thread.is_alive():
            self.oled_thread.join(timeout=1)

        print("👋 All displays stopped!")

    def _play_boot_sound(self):
        cfg = get_config()
        audio_cfg = cfg.get("audio", {})
        if not audio_cfg.get("enabled", False):
            return

        path = audio_cfg.get("path")
        if not path or not os.path.exists(path):
            return

        players = ["aplay", "paplay"]
        for player in players:
            if shutil.which(player):
                try:
                    subprocess.Popen([player, path])
                    return
                except Exception:
                    continue


# ====================
# Main Application
# ====================

def main():
    """Application entry point"""
    global CONFIG
    CONFIG = load_config()
    save_config(CONFIG)

    display = CombinedDisplay()

    try:
        display.start()
    except Exception as e:
        print(f"❌ Critical error: {e}")
        display.stop()
        sys.exit(1)


if __name__ == "__main__":
    main()
