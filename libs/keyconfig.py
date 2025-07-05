import contextlib
import os
import json
from pygame import key
from .speech import speak


class Keyconfig:
    def __init__(self, file="keyconfig.json"):
        self.file = file
        self.keys = {}
        self.load()

    def load(self):
        with contextlib.suppress(FileNotFoundError):
            path = self.file if os.path.exists(self.file) else "default_keyconfig.json"
            # we try to load the default keyconfig if not found, and we ignore if that one is not found as well.
            with open(path, "rb") as f:
                keys = json.loads(f.read())
                for k, v in keys.items():
                    try:
                        self.keys[v.strip()] = key.key_code(k.strip())
                        # we reverse it because in the game we care about keys from functions, not functions from keys. we also strip the strings just in case of leading or traling spaces
                    except ValueError:
                        # an invalid key is given.
                        speak(f"Invalid key string for {v}: {k}. Using default.")

    def save(self):
        # we reverse self.keys inside a local variable to be compatible with the file format.
        keys = {key.name(v): k for k, v in self.keys.items()}
        with open(self.file, "wb") as f:
            data = json.dumps(keys, indent=4).encode("utf-8", "ignore")
            f.write(data)

    def get(self, func, default):
        """returns the key constant asociated with {func}. if that key is not set, return {default}."""
        return self.keys.get(func, default)

    def set(self, k, func, autosave=True):
        """takes a key constant as {k} and a function string as {func} and sets that in the keyconfig. if autosave = True (default), saves the current key configuration to the file automaticly after setting."""
        self.keys[func] = k
        if autosave:
            self.save()
