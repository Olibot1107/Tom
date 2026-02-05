import os
import json
import copy
import threading
from small import DisplayType

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
            "\033[91m",
            "\033[92m",
            "\033[93m",
            "\033[94m",
            "\033[95m",
            "\033[96m",
            "\033[97m",
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
        "units": "imperial",
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
