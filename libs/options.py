import json
import os
import sys

from cryptography.fernet import Fernet
import appdirs

from . import consts

config_dirs = appdirs.AppDirs("final_hour")
# defaults.
prefs = {
    "beacons": True,
    "buffer_timing": 2,
    "host": consts.DEFAULT_HOST,
    "port": consts.DEFAULT_PORT,
    "stream_ambience": True,
}
fernet = Fernet(consts.SETTINGS_KEY)


def initialize():
    if not os.path.exists(config_dirs.user_config_dir):
        os.makedirs(config_dirs.user_config_dir)


def load():
    try:
        with open(f"{config_dirs.user_config_dir}/settings.json", "rb") as f:
            global prefs
            loaded_prefs = json.loads(fernet.decrypt(f.read()).decode())
            for key, value in loaded_prefs.items():
                prefs[key] = value
    except FileNotFoundError:
        # settings file not found, create one with the default settings.
        save()


def save():
    with open(f"{config_dirs.user_config_dir}/settings.json", "wb") as f:
        f.write(fernet.encrypt(json.dumps(prefs).encode()))


def get(key, default=None):
    if key == "host" and "local" in sys.argv:
        return "127.0.0.1"
    return prefs.get(key, default)


def set(key, value, autosave=True):
    prefs[key] = value
    if autosave:
        save()
