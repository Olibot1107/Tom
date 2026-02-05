import os
import threading
from flask import Flask, request
from config_state import get_config, update_config, ASSETS_DIR, BACKGROUND_PATH, BOOT_SOUND_PATH


class ConfigWebServer:
    def __init__(self):
        self.app = Flask(__name__)
        self._setup_routes()

    def _setup_routes(self):
        @self.app.get("/")
        def index():
            cfg = get_config()
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
                    <h3>System</h3>
                    <form id="rebootForm" method="post">
                        <button type="submit">Reboot Now</button>
                    </form>
                    <script>
                        const rebootForm = document.getElementById('rebootForm');
                        rebootForm.action = window.location.protocol + '//' + window.location.hostname + ':500/reboot';
                    </script>
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

            update_config({
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
        cfg = get_config()
        port = cfg["web"].get("config_port", 5000)
        threading.Thread(
            target=self.app.run,
            kwargs={"host": "0.0.0.0", "port": port, "debug": False, "use_reloader": False},
            daemon=True,
        ).start()
