"""Windows backend: enumerate and raise windows through user32.

Same contract as the macOS backend -- `pid()`, `list_windows()`,
`raise_window()` -- and the same reasoning behind it: match by TITLE, never by
index, because z-order changes between the listing and the raise.

Everything here is ctypes against user32/kernel32, so the plugin stays "Python
against the standard library" on this platform too. No pywin32, no psutil.

Three things this has to get right, all of them different from macOS:

PROCESS IDENTITY. There is no accessibility process name on Windows; the
identity is the executable's basename. VS Code is "Code.exe", so a config
written for macOS says `process_name = "Code"` and must still match -- the
comparison is case-insensitive and tolerates a missing ".exe". `bundle_path`
keeps working as the unambiguous override, compared as a full image path, which
is the answer for the Electron collision the macOS backend describes: two
editors both running as "Code.exe" from different install roots.

Unlike macOS there is no single pid per application. Electron apps run a broker
plus one renderer per window and any of them may own top-level windows, so this
backend does NOT pick one pid and enumerate it. It enumerates every top-level
window on the desktop and keeps those whose owning pid is any matching process.
`pid()` still exists and still returns a representative pid, because the shared
entrypoint logs it, but nothing here narrows by it.

WINDOW FILTERING. EnumWindows returns a great deal that is not a window a user
could switch to: zero-size message sinks, invisible Electron scratch windows,
cloaked UWP shells, and tool windows owned by a real window. Every one of them
would show up in the picker as a blank or duplicate row. The filter is
visible + unowned + non-empty title + not cloaked, and the cloak test is what
removes the ghost entries that IsWindowVisible alone still reports as visible.

FOREGROUND. SetForegroundWindow is refused for a process that does not already
own the foreground -- it flashes the taskbar button instead of raising, which
looks exactly like the plugin silently doing nothing. The documented way
through is to attach our input queue to the foreground window's thread for the
duration of the call, which makes the OS treat the request as coming from the
active app. AttachThreadInput is therefore not optional defensive garnish here;
without it this backend appears broken on precisely the gesture it exists for.
"""
import ctypes
import ctypes.wintypes as w
import os

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

# Set by the caller so a failure says so somewhere, mirroring the macOS backend.
report = None


def _note(msg):
    if report:
        report(msg)


WNDENUMPROC = ctypes.WINFUNCTYPE(w.BOOL, w.HWND, w.LPARAM)

user32.EnumWindows.argtypes = [WNDENUMPROC, w.LPARAM]
user32.EnumWindows.restype = w.BOOL
user32.GetWindowTextLengthW.argtypes = [w.HWND]
user32.GetWindowTextW.argtypes = [w.HWND, w.LPWSTR, ctypes.c_int]
user32.IsWindowVisible.argtypes = [w.HWND]
user32.GetWindow.argtypes = [w.HWND, w.UINT]
user32.GetWindow.restype = w.HWND
user32.GetWindowThreadProcessId.argtypes = [w.HWND, ctypes.POINTER(w.DWORD)]
user32.GetWindowThreadProcessId.restype = w.DWORD
user32.SetForegroundWindow.argtypes = [w.HWND]
user32.ShowWindow.argtypes = [w.HWND, ctypes.c_int]
user32.IsIconic.argtypes = [w.HWND]
user32.BringWindowToTop.argtypes = [w.HWND]
user32.GetForegroundWindow.restype = w.HWND
user32.AttachThreadInput.argtypes = [w.DWORD, w.DWORD, w.BOOL]

kernel32.OpenProcess.argtypes = [w.DWORD, w.BOOL, w.DWORD]
kernel32.OpenProcess.restype = w.HANDLE
kernel32.CloseHandle.argtypes = [w.HANDLE]
kernel32.QueryFullProcessImageNameW.argtypes = [
    w.HANDLE, w.DWORD, w.LPWSTR, ctypes.POINTER(w.DWORD)]
kernel32.QueryFullProcessImageNameW.restype = w.BOOL
kernel32.GetCurrentThreadId.restype = w.DWORD

GW_OWNER = 4
SW_RESTORE = 9
# PROCESS_QUERY_LIMITED_INFORMATION, not PROCESS_QUERY_INFORMATION: the limited
# right is enough to read the image path and is granted for processes at the
# same integrity level, where the full right is not.
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
DWMWA_CLOAKED = 14


def _cloaked(hwnd):
    """True for a window the shell is hiding (other virtual desktop, UWP shell).

    These pass IsWindowVisible and would otherwise reach the picker as rows the
    user cannot switch to. dwmapi may be missing on a stripped system, in which
    case the honest answer is "not cloaked" rather than an exception.
    """
    try:
        dwmapi = ctypes.WinDLL("dwmapi")
    except OSError:
        return False
    val = ctypes.c_int(0)
    hr = dwmapi.DwmGetWindowAttribute(
        w.HWND(hwnd), w.DWORD(DWMWA_CLOAKED),
        ctypes.byref(val), ctypes.sizeof(val))
    return hr == 0 and val.value != 0


def _image_path(pid):
    """Full executable path for `pid`, or "" if it cannot be read."""
    h = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not h:
        return ""
    try:
        size = w.DWORD(32768)
        buf = ctypes.create_unicode_buffer(size.value)
        if not kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)):
            return ""
        return buf.value
    finally:
        kernel32.CloseHandle(h)


def _window_title(hwnd):
    n = user32.GetWindowTextLengthW(hwnd)
    if n <= 0:
        return ""
    buf = ctypes.create_unicode_buffer(n + 1)
    user32.GetWindowTextW(hwnd, buf, n + 1)
    return buf.value


def _toplevel_windows():
    """(hwnd, pid, title) for every window a user could plausibly switch to."""
    found = []

    def cb(hwnd, _lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        # An owned window is a dialog or tool window belonging to a real one.
        if user32.GetWindow(hwnd, GW_OWNER):
            return True
        title = _window_title(hwnd)
        if not title:
            return True
        if _cloaked(hwnd):
            return True
        pid = w.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        found.append((hwnd, pid.value, title))
        return True

    if not user32.EnumWindows(WNDENUMPROC(cb), 0):
        err = ctypes.get_last_error()
        # EnumWindows returns FALSE when a callback stops the walk; ours never
        # does, so a real failure is the only way here.
        if err:
            _note("EnumWindows failed err={}".format(err))
    return found


def _force_foreground(hwnd):
    """Raise `hwnd`, working around the foreground lock. See FOREGROUND above."""
    if user32.IsIconic(hwnd):
        user32.ShowWindow(hwnd, SW_RESTORE)
    fg = user32.GetForegroundWindow()
    if fg == hwnd:
        return True
    target_thread = user32.GetWindowThreadProcessId(hwnd, None)
    fg_thread = user32.GetWindowThreadProcessId(fg, None) if fg else 0
    ours = kernel32.GetCurrentThreadId()
    attached = []
    for other in {fg_thread, target_thread}:
        if other and other != ours and user32.AttachThreadInput(ours, other, True):
            attached.append(other)
    try:
        user32.BringWindowToTop(hwnd)
        ok = bool(user32.SetForegroundWindow(hwnd))
    finally:
        for other in attached:
            user32.AttachThreadInput(ours, other, False)
    if not ok:
        _note("SetForegroundWindow refused for hwnd={}".format(hwnd))
    return ok


class WindowsBackend:
    name = "windows"

    def __init__(self, app):
        self.app = app
        self._pid = None

    def _wanted_exe(self):
        """The executable basename to match, lowercased and with .exe."""
        name = (self.app.process_name or "").strip().lower()
        if name and not name.endswith(".exe"):
            name += ".exe"
        return name

    def _is_target(self, pid):
        path = _image_path(pid)
        if not path:
            return False
        want_path = (self.app.bundle_path or "").strip()
        if want_path:
            return os.path.normcase(os.path.normpath(path)) == \
                os.path.normcase(os.path.normpath(want_path))
        return os.path.basename(path).lower() == self._wanted_exe()

    def _target_windows(self):
        """(hwnd, pid, title) for the configured application only.

        The pid->image-path lookup is cached per call: an Electron editor puts
        every window on a different renderer pid, but a handful of pids back a
        few dozen windows, and OpenProcess is the expensive part.
        """
        seen = {}
        out = []
        for hwnd, pid, title in _toplevel_windows():
            if pid not in seen:
                seen[pid] = self._is_target(pid)
            if seen[pid]:
                out.append((hwnd, pid, title))
        return out

    def pid(self):
        """A representative pid for the target app, or 0.

        Unlike macOS this is not how windows are found -- see PROCESS IDENTITY.
        It exists because the shared entrypoint treats 0 as "app not running".
        """
        if self._pid is not None:
            return self._pid
        hits = self._target_windows()
        self._pid = hits[0][1] if hits else 0
        return self._pid

    def list_windows(self):
        return [title for _hwnd, _pid, title in self._target_windows()]

    def raise_window(self, title, index=0):
        wins = self._target_windows()
        if not wins:
            _note("raise: no {} windows".format(self.app.process_name))
            return
        for hwnd, _pid, name in wins:
            if name == title:
                _force_foreground(hwnd)
                return
        # Title changed under us. `index` is 1-based, matching the macOS
        # backend's contract and the picker's return value.
        if 1 <= index <= len(wins):
            _note("raise: title {!r} gone, falling back to index {}".format(
                title, index))
            _force_foreground(wins[index - 1][0])
            return
        _note("raise: no window matched {!r} and index {} is out of range".format(
            title, index))
