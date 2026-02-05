import json
import os
import queue
import threading
import time
import zipfile
from urllib.request import urlopen

from .config_state import get_config

_LAST_HEARD_LOCK = threading.Lock()
_LAST_HEARD = ""


def set_last_heard(text):
    with _LAST_HEARD_LOCK:
        global _LAST_HEARD
        _LAST_HEARD = text


def get_last_heard():
    with _LAST_HEARD_LOCK:
        return _LAST_HEARD


class SpeechListener:
    def __init__(self, on_command, on_text=None):
        self.on_command = on_command
        self.on_text = on_text
        self._thread = None
        self._stop = threading.Event()

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1)

    def _run(self):
        cfg = get_config().get("speech", {})
        if not cfg.get("enabled", False):
            return

        model_path = cfg.get("model_path", "")
        model_url = cfg.get("model_url", "")
        if not model_path or not os.path.exists(model_path):
            if model_url:
                self._download_model(model_url, model_path)
            if not model_path or not os.path.exists(model_path):
                print("⚠️  Speech model not found. Set speech.model_path to a Vosk model folder.")
                return

        try:
            from vosk import Model, KaldiRecognizer
            import sounddevice as sd
        except Exception as e:
            print(f"⚠️  Speech dependencies missing: {e}")
            return

        q = queue.Queue()

        def callback(indata, frames, time_info, status):
            if status:
                return
            q.put(bytes(indata))

        try:
            model = Model(model_path)
            recognizer = KaldiRecognizer(model, 16000)

            with sd.RawInputStream(
                samplerate=16000,
                blocksize=8000,
                dtype='int16',
                channels=1,
                callback=callback,
            ):
                while not self._stop.is_set():
                    try:
                        data = q.get(timeout=0.2)
                    except queue.Empty:
                        continue

                    if recognizer.AcceptWaveform(data):
                        result = json.loads(recognizer.Result())
                        text = (result.get("text") or "").strip().lower()
                        if text:
                            set_last_heard(text)
                            if self.on_text:
                                self.on_text(text)
                            self._handle_text(text, cfg)
        except Exception as e:
            print(f"⚠️  Speech listener error: {e}")

    def _handle_text(self, text, cfg):
        wake = (cfg.get("wake_word") or "tom").lower()
        if text.startswith(wake + " "):
            command = text[len(wake):].strip()
            if command:
                self.on_command(command)
            return
        if text == wake:
            return

    def _download_model(self, url, model_path):
        try:
            if not model_path:
                return
            target_dir = model_path
            os.makedirs(os.path.dirname(target_dir), exist_ok=True)
            zip_path = f"{target_dir}.zip"
            print(f"⬇️  Downloading speech model from {url} ...")
            with urlopen(url, timeout=30) as resp, open(zip_path, "wb") as f:
                while True:
                    chunk = resp.read(1024 * 1024)
                    if not chunk:
                        break
                    f.write(chunk)
            print("📦 Extracting speech model...")
            with zipfile.ZipFile(zip_path, "r") as zf:
                names = zf.namelist()
                top_dir = None
                if names:
                    top_dir = names[0].split("/")[0]
                zf.extractall(os.path.dirname(target_dir))
            if top_dir:
                extracted = os.path.join(os.path.dirname(target_dir), top_dir)
                if os.path.isdir(extracted) and not os.path.exists(target_dir):
                    os.rename(extracted, target_dir)
            os.remove(zip_path)
            print("✅ Speech model ready.")
        except Exception as e:
            print(f"⚠️  Failed to download speech model: {e}")
