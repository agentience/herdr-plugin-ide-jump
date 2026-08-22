"""Window-manager backends.

Two operations are all this plugin needs from a desktop: enumerate an
application's windows, and raise one of them. Everything platform-specific
lives behind that pair, so adding a platform means adding one module here and
one line in `get_backend` -- not restructuring the plugin.

Ported platforms:
  macos   System Events / accessibility API (implemented)
  windows user32 EnumWindows / SetForegroundWindow (implemented)

Wanted:
  x11     `wmctrl -l` to enumerate, `wmctrl -i -a <id>` to raise. Mechanically
          the easiest of the three; `xdotool search --name` works too.
  wayland No standard window-raise protocol -- it is compositor-specific by
          design. Sway/i3 can do it through `swaymsg`, but GNOME needs a shell
          extension and KDE needs KWin scripting. This is why the manifest
          declares `platforms = ["macos"]` rather than claiming more.
"""
import sys


class BackendUnavailable(RuntimeError):
    pass


def get_backend(app, report=None):
    """Return the backend for this platform, or raise BackendUnavailable.

    `report` is a diagnostic logging callable. It is set on the platform module
    rather than handed to the constructor because the module-level helpers need
    it too, and setting it here is what lets the caller wire up logging without
    a platform-specific import of its own.
    """
    if sys.platform == "darwin":
        from . import macos
        macos.report = report
        return macos.MacOSBackend(app)
    if sys.platform == "win32":
        from . import windows
        windows.report = report
        return windows.WindowsBackend(app)
    raise BackendUnavailable(
        "no window backend for platform {!r} -- see idejump/backends/"
        "__init__.py for what a port needs to implement".format(sys.platform)
    )
