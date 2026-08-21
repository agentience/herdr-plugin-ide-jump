#!/usr/bin/env python3
"""Entrypoint for every command the manifest declares.

  jump          raise this project's window, no UI          ([[actions]] jump)
  open-picker   ask Herdr to open the picker popup          ([[actions]] pick)
  picker        the picker itself, inside the popup pane    ([[panes]] picker)
  why           print how the project resolved, and exit    (debugging)
  list          print window titles, one per line           (debugging)

`pick` and `picker` are two entrypoints for one gesture because an action
command runs detached with no terminal attached, so it cannot host an
interactive list. The action's whole job is to ask Herdr for a popup pane and
hand it the invocation context, which the popup would otherwise have to
re-derive from a process that is no longer the focused one.
"""
import datetime
import json
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from windowswitch import config, context, picker  # noqa: E402
from windowswitch.backends import BackendUnavailable, get_backend  # noqa: E402

PLUGIN_ID = "trellios.window-switch"


def log_dir():
    """Where the log goes, most-preferred first.

    HERDR_PLUGIN_STATE_DIR is the documented home for plugin runtime state, but
    Herdr 0.8.2 does not set it (measured -- neither the variable nor the
    directory exists), so the config dir is the working fallback and a plain
    XDG-ish path is the last resort. The log is not optional colour: when a
    keybinding "does nothing", one line here separates "never invoked" from
    "invoked and matched nothing", which is the difference between a wiring bug
    and a naming bug.
    """
    for key in ("HERDR_PLUGIN_STATE_DIR", "HERDR_PLUGIN_CONFIG_DIR"):
        d = os.environ.get(key)
        if d:
            return d
    return os.path.expanduser("~/.local/state/herdr-window-switch")


def log(msg):
    try:
        d = log_dir()
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "window-switch.log"), "a") as fh:
            fh.write("{} {}\n".format(
                datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), msg))
    except Exception:
        pass


def open_missing(app, root):
    """No open window matches -- let the configured command create one."""
    if not app.open_command or not root:
        return False
    cmd = [a.replace("{path}", root) for a in app.open_command]
    if not shutil.which(cmd[0]):
        log("open_command {!r} not on PATH".format(cmd[0]))
        return False
    subprocess.run(cmd, capture_output=True)
    # The CLI picks the right window but does not always bring the app forward
    # when the frontmost app is the terminal.
    subprocess.run(["open", "-a", app.app_name], capture_output=True)
    return True


def cmd_jump(app, backend):
    name, root, why = context.resolve_project()
    items = backend.list_windows()
    idx = picker.find_index(items, name)
    log("jump project={!r} via {} match={} {!r}".format(
        name, why, idx, items[idx] if idx >= 0 else None))
    if idx >= 0:
        backend.raise_window(items[idx], idx + 1)
        return 0
    # Nothing open for this project. Ask the configured command to open it
    # rather than raising some unrelated window, which would look like a hit.
    if open_missing(app, root):
        return 0
    log("jump: no window for {!r} and nothing opened it".format(name))
    return 0


def cmd_open_picker():
    """Hand the popup the context this process has and it would not."""
    name, root, why = context.resolve_project()
    # No --workspace: Herdr rejects it for popup and overlay panes, which always
    # target the active pane ("overlay and popup plugin panes target the active
    # pane", invalid_params). The popup lands where the user is, which is what
    # a keybinding wants anyway.
    args = [context.herdr_bin(), "plugin", "pane", "open",
            "--plugin", PLUGIN_ID, "--entrypoint", "picker"]
    if name:
        args += ["--env", "WINDOW_SWITCH_PROJECT=" + name]
    if root:
        args += ["--env", "WINDOW_SWITCH_ROOT=" + root]
    args += ["--env", "WINDOW_SWITCH_WHY=" + why]
    # Forwarded so the popup half can be exercised without holding the keyboard.
    if os.environ.get("WINDOW_SWITCH_SELFTEST"):
        args += ["--env", "WINDOW_SWITCH_SELFTEST=1"]
    r = subprocess.run(args, capture_output=True, text=True)
    log("open-picker project={!r} via {} rc={} {}".format(
        name, why, r.returncode, (r.stderr or r.stdout).strip()[:200]))
    return r.returncode


def cmd_picker(app, backend):
    items = backend.list_windows()
    if not items:
        sys.stderr.write("No {} windows found.\n".format(app.app_name))
        return 1
    name = os.environ.get("WINDOW_SWITCH_PROJECT") or ""
    why = os.environ.get("WINDOW_SWITCH_WHY") or ""
    if not name:
        name, _root, why = context.resolve_project()
    idx = picker.preselect_index(items, name)
    log("picker project={!r} via {} preselect={} {!r}".format(
        name, why, idx, items[idx]))
    if os.environ.get("WINDOW_SWITCH_SELFTEST"):
        # Prove the popup launched and handed us a real terminal, then get out.
        # The interactive path holds all keyboard input until Esc, which is not
        # something to trigger from a script running under someone's session.
        try:
            with open("/dev/tty", "w") as fh:
                fh.write("selftest ok\n")
            log("selftest: /dev/tty writable, {} windows".format(len(items)))
        except Exception as exc:
            log("selftest: /dev/tty FAILED {!r}".format(exc))
        return 0
    chosen = picker.pick(items, idx,
                         title="Switch to {} window".format(app.app_name))
    if chosen is None:
        return 0
    backend.raise_window(chosen[1], chosen[0])
    return 0


def cmd_why(app, backend):
    name, root, why = context.resolve_project()
    items = backend.list_windows()
    idx = picker.preselect_index(items, name)
    print("app       : {} (process {})".format(app.app_name, app.process_name))
    print("config    : {}".format(config.config_path() or "(no HERDR_PLUGIN_CONFIG_DIR)"))
    print("project   : {}".format(name or "(none)"))
    print("root      : {}".format(root or "(none)"))
    print("resolved  : {}".format(why))
    print("preselect : {} -> {}".format(idx, items[idx] if items else "(no windows)"))
    print("context   : {}".format(json.dumps(context.invocation_context())))
    return 0


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "picker"
    if cmd == "open-picker":
        return cmd_open_picker()
    app = config.load()
    try:
        backend = get_backend(app)
    except BackendUnavailable as exc:
        sys.stderr.write(str(exc) + "\n")
        return 1
    if cmd == "jump":
        return cmd_jump(app, backend)
    if cmd == "list":
        print("\n".join(backend.list_windows()))
        return 0
    if cmd == "why":
        return cmd_why(app, backend)
    if cmd == "picker":
        return cmd_picker(app, backend)
    sys.stderr.write("unknown command: {}\n".format(cmd))
    return 2


if __name__ == "__main__":
    sys.exit(main())
