"""User config, read from HERDR_PLUGIN_CONFIG_DIR/config.json.

Nothing in the mechanism is VS-Code-specific -- enumerate windows, raise one --
so the application is configurable and VS Code is only the default. `app_name`
is what the OS calls the application; `process_name` is what the accessibility
API calls its process, which on macOS is often shorter ("Code", "Cursor").

The config directory is created by Herdr, but the file is not: an absent or
malformed file falls back to the defaults rather than failing, because a broken
config should not cost you the keybinding.
"""
import json
import os


class App:
    def __init__(self, app_name, process_name, open_command=None):
        self.app_name = app_name
        self.process_name = process_name
        self.open_command = open_command


DEFAULTS = {
    "app_name": "Visual Studio Code",
    "process_name": "Code",
    # Run when no open window matches the project. `{path}` is substituted with
    # the project root. Set to null to do nothing instead.
    "open_command": ["code", "{path}"],
}


def config_path():
    d = os.environ.get("HERDR_PLUGIN_CONFIG_DIR")
    return os.path.join(d, "config.json") if d else ""


def load():
    data = dict(DEFAULTS)
    path = config_path()
    if path and os.path.isfile(path):
        try:
            with open(path) as fh:
                user = json.load(fh)
            if isinstance(user, dict):
                data.update({k: v for k, v in user.items() if k in DEFAULTS})
        except Exception:
            pass
    return App(data["app_name"], data["process_name"], data["open_command"])
