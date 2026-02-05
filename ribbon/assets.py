import os
import math
import wave
import struct
from PIL import Image
from .config_state import ASSETS_DIR, BACKGROUND_PATH, BOOT_SOUND_PATH, DEFAULT_AVIF_PATH


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
