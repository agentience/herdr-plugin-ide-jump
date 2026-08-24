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

from idejump import config, context, picker  # noqa: E402
from idejump.backends import BackendUnavailable, get_backend  # noqa: E402

PLUGIN_ID = "agentience.ide-jump"


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
    return os.path.expanduser("~/.local/state/herdr-ide-jump")


def log(msg):
    try:
        d = log_dir()
        os.makedirs(d, exist_ok=True)
        # encoding is explicit: window titles carry em dashes and arrows, and
        # the Windows default here is cp1252, which raises on both.
        with open(os.path.join(d, "ide-jump.log"), "a", encoding="utf-8") as fh:
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
    # shell=True on Windows: the editor CLIs ship as .cmd shims there
    # ("code.cmd"), which CreateProcess cannot execute directly.
    subprocess.run(cmd, capture_output=True,
                   shell=(sys.platform == "win32"))
    # The CLI picks the right window but does not always bring the app forward
    # when the frontmost app is the terminal.
    if sys.platform == "darwin":
        subprocess.run(["open", "-a", app.app_name], capture_output=True)
    return True


def cmd_jump(app, backend):
    name, root, why = context.resolve_project()
    # Resolved up front: the root is a MATCHING signal now, not only the thing
    # that gets opened, and a label-resolved project carries none of its own.
    root = root or context.resolve_root()
    items = backend.list_windows()
    idx = picker.find_index(items, name, root)
    log("jump project={!r} root={!r} via {} match={} {!r}".format(
        name, root, why, idx, items[idx] if idx >= 0 else None))
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
    # Resolved here and forwarded because this process has the real invocation
    # context and the popup does not: inside the popup, `pane current` is the
    # popup itself. See context.resolve_root.
    root = root or context.resolve_root()
    # No --workspace: Herdr rejects it for popup and overlay panes, which always
    # target the active pane ("overlay and popup plugin panes target the active
    # pane", invalid_params). The popup lands where the user is, which is what
    # a keybinding wants anyway.
    args = [context.herdr_bin(), "plugin", "pane", "open",
            "--plugin", PLUGIN_ID, "--entrypoint", "picker"]
    if name:
        args += ["--env", "IDE_JUMP_PROJECT=" + name]
    if root:
        args += ["--env", "IDE_JUMP_ROOT=" + root]
    args += ["--env", "IDE_JUMP_WHY=" + why]
    # Forwarded so the popup half can be exercised without holding the keyboard.
    if os.environ.get("IDE_JUMP_SELFTEST"):
        args += ["--env", "IDE_JUMP_SELFTEST=1"]
    r = subprocess.run(args, capture_output=True, text=True)
    log("open-picker project={!r} via {} rc={} {}".format(
        name, why, r.returncode, (r.stderr or r.stdout).strip()[:200]))
    return r.returncode


def cmd_picker(app, backend):
    items = backend.list_windows()
    name = os.environ.get("IDE_JUMP_PROJECT") or ""
    why = os.environ.get("IDE_JUMP_WHY") or ""
    if not name:
        name, _root, why = context.resolve_project()
    # Env only, never resolved here: inside the popup the cwd signals point at
    # this plugin's own directory, and opening the editor on THAT is a worse
    # outcome than not opening anything. Empty means the popup was launched
    # directly rather than through the `pick` action.
    root = os.environ.get("IDE_JUMP_ROOT") or ""

    idx = picker.find_index(items, name, root)
    if idx < 0:
        # Nothing here belongs to this project -- no editor windows at all, or
        # only other projects' windows. Open instead of listing.
        #
        # DIVERGES FROM UPSTREAM, deliberately. The README keeps `jump` as the
        # only gesture that handles "the editor isn't up yet" and leaves pick to
        # choose among windows, admitting that pick then "opens on an unrelated
        # first row that Enter will happily raise". That row is the problem: the
        # gesture means "get me to this project's editor", and every row on
        # offer is the wrong project. Opening is the answer to the question that
        # was actually asked.
        log("picker: no window for {!r} (via {}, {} other window(s)), "
            "opening {!r}".format(name, why, len(items), root))
        if open_missing(app, root):
            return 0
        if not items:
            # Could not open AND nothing to list. Say which knob is wrong: this
            # is the branch users report as "it said no windows", and the log
            # otherwise cannot separate "editor not running" from "editor
            # running, process filter did not match it".
            log("picker: nothing opened and no {} windows "
                "(process_name={!r} bundle_path={!r} root={!r})".format(
                    app.app_name, app.process_name, app.bundle_path, root))
            sys.stderr.write(
                "No {} windows found, and nothing opened one.\n"
                "If {} IS running, its executable does not match process_name "
                "{!r} -- check {}\n".format(
                    app.app_name, app.app_name, app.process_name,
                    config.config_path() or "the plugin config"))
            return 1
        # Opening failed (no root, or open_command missing / not on PATH) but
        # other windows exist. A list of the wrong projects still beats a
        # keypress that does nothing.
        log("picker: could not open {!r}, falling back to the list".format(name))
        idx = 0

    log("picker project={!r} via {} preselect={} {!r}".format(
        name, why, idx, items[idx]))
    if os.environ.get("IDE_JUMP_SELFTEST"):
        # Prove the popup launched and handed us a real terminal, then get out.
        # The interactive path holds all keyboard input until Esc, which is not
        # something to trigger from a script running under someone's session.
        tty_name = "CONOUT$" if sys.platform == "win32" else "/dev/tty"
        try:
            with open(tty_name, "w") as fh:
                fh.write("selftest ok\n")
            log("selftest: {} writable, {} windows".format(tty_name, len(items)))
        except Exception as exc:
            log("selftest: {} FAILED {!r}".format(tty_name, exc))
        return 0
    chosen = picker.pick(items, idx,
                         title="Switch to {} window".format(app.app_name))
    if chosen is None:
        return 0
    backend.raise_window(chosen[1], chosen[0])
    return 0


def cmd_why(app, backend):
    name, root, why = context.resolve_project()
    root = root or context.resolve_root()
    items = backend.list_windows()
    idx = picker.preselect_index(items, name, root)
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
        backend = get_backend(app, report=log)
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
