import threading
import subprocess
from flask import Flask
from config_state import get_config


class RebootWebServer:
    def __init__(self):
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
        cfg = get_config()
        port = cfg["web"].get("reboot_port", 500)
        threading.Thread(
            target=self.app.run,
            kwargs={"host": "0.0.0.0", "port": port, "debug": False, "use_reloader": False},
            daemon=True,
        ).start()
