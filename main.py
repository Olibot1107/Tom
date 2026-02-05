# main.py
import time, sys

colors = ["\033[91m", "\033[92m", "\033[93m", "\033[94m", "\033[95m"]
text = "🔥 Welcome to Pi 5 Ribbon Display! 🔥"

while True:
    for color in colors:
        sys.stdout.write(f"{color}{text}\r")
        sys.stdout.flush()
        time.sleep(0.3)
