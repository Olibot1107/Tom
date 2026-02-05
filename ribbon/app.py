import time
import threading
from . import config_state
from .config_state import load_config, save_config
from .weather import WeatherProvider
from .ui_terminal import TerminalUI
from .ui_oled import OLEDDisplay
from .web_config import ConfigWebServer
from .web_reboot import RebootWebServer
from .assets import ensure_default_assets
from .audio import play_boot_sound


class CombinedDisplay:
    """Combined terminal and OLED display"""

    def __init__(self):
        self.weather_provider = WeatherProvider()
        self.terminal_ui = TerminalUI(self.weather_provider)
        self.oled_display = OLEDDisplay(self.weather_provider)
        self.config_server = ConfigWebServer()
        self.reboot_server = RebootWebServer()
        self.running = False
        self.terminal_thread = None
        self.oled_thread = None

    def start_terminal(self):
        try:
            self.terminal_ui.start()
        except Exception as e:
            print(f"❌ Terminal UI error: {e}")

    def start_oled(self):
        self.oled_display.start()

    def start(self):
        self.running = True

        print("🚀 Initializing Raspberry Pi 5 Ribbon Display...")
        time.sleep(1)

        ensure_default_assets()
        play_boot_sound()
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
        self.running = False
        self.weather_provider.stop()
        self.terminal_ui.stop()
        self.oled_display.stop()

        if self.oled_thread and self.oled_thread.is_alive():
            self.oled_thread.join(timeout=1)

        print("👋 All displays stopped!")


def main():
    config_state.CONFIG = load_config()
    save_config(config_state.CONFIG)

    display = CombinedDisplay()
    try:
        display.start()
    except Exception as e:
        print(f"❌ Critical error: {e}")
        display.stop()
        raise


if __name__ == "__main__":
    main()
