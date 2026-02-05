import os
import time
from datetime import datetime
from .config_state import get_config
from .system_info import get_system_info


class TerminalUI:
    """Terminal UI for Raspberry Pi 5 Ribbon Display"""

    def __init__(self, weather_provider):
        self.width = 80
        self.height = 24
        self.start_time = time.time()
        self.weather_provider = weather_provider

    def _update_terminal_size(self):
        try:
            size = os.get_terminal_size()
            self.width = size.columns
            self.height = size.lines
        except OSError:
            pass

    def clear_screen(self):
        os.system("cls" if os.name == "nt" else "clear")

    def reset_cursor(self):
        print("\033[H", end="")

    def center_text(self, text, width=None):
        if width is None:
            width = self.width
        return text.center(width)

    def draw_header(self):
        colors = get_config()["terminal"]["colors"]
        header_text = "RASPBERRY PI 5 RIBBON DISPLAY"
        line = f"{colors[3]}" + "═" * self.width
        print(line)
        print(f"{colors[6]}\033[1m{self.center_text(header_text)}\033[0m")
        print(line)

    def draw_time_date(self):
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
        uptime_seconds = int(time.time() - self.start_time)
        hours, remainder = divmod(uptime_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def draw_all(self):
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
        print("\033[?1049h\033[?25l")
        try:
            while True:
                self.draw_all()
                time.sleep(get_config()["terminal"].get("refresh_s", 1.0))
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        print("\033[?25h\033[?1049l")
        self.clear_screen()
        print("👋 Terminal display stopped!")
