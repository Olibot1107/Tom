import os
import shutil
import subprocess
from config_state import get_config


def play_boot_sound():
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
