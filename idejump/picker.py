"""Keyboard-only filterable list, in the feel of fzf.

Written against the CONTROLLING TERMINAL directly rather than stdin/stdout so it
works inside a Herdr popup pane, and depends on nothing outside the standard
library -- no fzf, sk, peco or gum, none of which are guaranteed present on the
machine the plugin is installed on.

"The controlling terminal" is /dev/tty on POSIX and the CONIN$/CONOUT$ pair on
Windows. Those differ in more than their name -- one is a file descriptor put
into raw mode with termios, the other is a console read through msvcrt that was
never in cooked mode to begin with -- so the two live behind the small terminal
classes below and the key-handling loop is written once against the events they
emit.

TRAP: `import termios` at module scope is enough to make this module unusable on
Windows, which takes `jump` down with it -- `find_index` is pure logic that the
non-interactive path needs, and it never wanted a tty at all. The platform
imports are therefore deferred into the terminal classes.
"""
import os
import re
import sys

MAX_ROWS = 15

# Windows drive letters and POSIX roots both, because the title format is the
# user's choice and a config copied between machines should keep working.
_ABS_RE = re.compile(r"^(?:[A-Za-z]:[\\/]|[\\/])")
# The separator VS Code puts between title parts, "${separator}", is " - " by
# default; em and en dashes show up in hand-written formats.
_SEP_RE = re.compile(r"\s+(?:-|\u2014|\u2013)\s+")


def _norm(p):
    """Fold a path for comparison.

    normcase lowercases and turns / into \\ on Windows, which is the whole
    point: git reports "C:/x/y" and Herdr reports "C:\\x\\y" for one directory.
    """
    return os.path.normcase(os.path.normpath(p)).rstrip(os.sep)


def path_in_title(title):
    """The absolute-path segment of a window title, or "".

    Split on the separator and take the part that starts like a path, rather
    than pattern-matching a path out of the whole string. A folder name may
    legally contain spaces and hyphens -- "master - Visual Studio Code" is a
    valid directory name -- so a regex scanning the raw title cannot know where
    the path stops, while the title's own structure can.

    Titles that carry a path are the only ones that can be told apart when two
    projects share a folder name: "master" under two different repos is the
    same string, and no matching can separate them without one.
    """
    for seg in (s.strip() for s in _SEP_RE.split(title)):
        if seg and _ABS_RE.match(seg):
            return seg
    return ""


def title_has_path(title, root):
    """True when `title` names the project rooted at `root`.

    The clean case first -- a title segment that IS the path, which is what the
    recommended window.title produces. Then a containment check for formats
    that wrap the path in something else, or folder names that contain the
    separator and so survive neither split. Containment tests the character
    after the match, so /x/master cannot match /x/master-old.
    """
    if not root:
        return False
    seg = path_in_title(title)
    if seg and _norm(seg) == _norm(root):
        return True
    hay, needle = os.path.normcase(title), _norm(root)
    at = hay.find(needle)
    while at != -1:
        end = at + len(needle)
        if end >= len(hay) or not (hay[end].isalnum() or hay[end] in "_-.~"):
            return True
        at = hay.find(needle, at + 1)
    return False


def short_label(title):
    """Row text for the picker: "repo/worktree" when the title carries a path.

    A full path is what makes the match reliable, and also what makes a title
    unreadable in a 60%-wide popup. The last two components are what actually
    distinguish the user's worktrees ("paas/master" against "gestao/master"),
    so the list shows those and the match still uses the whole path.
    """
    path = path_in_title(title)
    if not path:
        return title
    parts = [p for p in re.split(r"[\\/]", path.rstrip("\\/")) if p]
    return "/".join(parts[-2:]) if len(parts) >= 2 else (parts[0] if parts else title)


def labels_for(items):
    """Row text for every item, kept distinct.

    Two windows on the SAME project collapse to one label, which would leave the
    picker showing two identical rows and no way to tell which is which. Those
    -- and only those -- get the title's leading segment appended, which is the
    active editor under the default title format.
    """
    labels = [short_label(t) for t in items]
    seen = {}
    for lab in labels:
        seen[lab] = seen.get(lab, 0) + 1
    out = []
    for title, lab in zip(items, labels):
        if seen[lab] > 1:
            head = re.split(r"\s+-\s+|\u2014|\u2013", title)[0].strip()
            if head and head != lab:
                lab = "{}  ({})".format(lab, head)
        out.append(lab)
    return out


def matches(query, item):
    """Case-insensitive subsequence match, the way fzf feels."""
    if not query:
        return True
    it = iter(item.lower())
    return all(ch in it for ch in query.lower())


def find_index(items, project, root=None):
    """Index of the window belonging to `project`, or -1 if none does.

    A title is the folder name plus a mutable status suffix, e.g.
    "trade-advisor — Modified". Match the whole title first, then the head
    before a separator, so "articles" never matches "articles-archive".

    Returns -1 rather than 0 for "no match" because the two callers need
    different things from that case: the picker opens on the first row anyway,
    while `jump` must NOT raise an arbitrary window when it found nothing.

    `root` is the project's directory, and it is tried FIRST because it is the
    only signal that survives a folder-name collision. Git worktrees are the
    common way to get one: a checkout laid out as <repo>/<branch> names every
    worktree after its branch, so "master" is the folder name under every repo
    on the machine and matching by name picks whichever window comes first. A
    path match is exact. It requires a title that carries the path -- see
    path_in_title -- and silently contributes nothing when the title does not.
    """
    if root:
        for i, name in enumerate(items):
            if title_has_path(name, root):
                return i
    if not project:
        return -1
    for i, name in enumerate(items):
        if name == project:
            return i
    for sep in ("—", "–", " - "):
        for i, name in enumerate(items):
            if name.split(sep)[0].strip() == project:
                return i
    # Last, the project as any whole segment. VS Code's default title on
    # Windows is "${activeEditorShort} - ${rootName} - ${appName}", which puts
    # the folder name in the MIDDLE -- neither test above can see it, and the
    # plugin would report "no window for this project" with the window right
    # there. Ranked last so a head match still wins, and still compared by
    # equality per segment, so "articles" does not match "articles-archive".
    for sep in ("—", "–", " - "):
        for i, name in enumerate(items):
            if project in [seg.strip() for seg in name.split(sep)]:
                return i
    return -1


def preselect_index(items, project, root=None):
    """Row the picker should open on: the project's window, else the first."""
    return max(0, find_index(items, project, root))


# --- terminals -------------------------------------------------------------
#
# Both classes are context managers that expose `write`, `flush` and
# `read_event`. An event is one of:
#   ("enter", None) ("cancel", None) ("backspace", None) ("clear", None)
#   ("up", None)    ("down", None)   ("char", <str>)     (None, None) on EOF


class _PosixTerm:
    def __init__(self):
        import select
        import termios
        import tty
        self._select, self._termios, self._tty = select, termios, tty

    def __enter__(self):
        self._in = open("/dev/tty", "rb", buffering=0)
        self._out = open("/dev/tty", "w")
        self._fd = self._in.fileno()
        self._old = self._termios.tcgetattr(self._fd)
        self._tty.setraw(self._fd)
        return self

    def __exit__(self, *exc):
        self._termios.tcsetattr(self._fd, self._termios.TCSADRAIN, self._old)
        self._out.write("\x1b[H\x1b[2J")
        self._out.flush()
        self._in.close()
        self._out.close()

    def write(self, s):
        self._out.write(s)

    def flush(self):
        self._out.flush()

    def read_event(self):
        ch = self._in.read(1)
        if not ch:
            return None, None
        b = ch[0]
        if b in (13, 10):
            return "enter", None
        if b == 3:
            return "cancel", None
        if b in (127, 8):
            return "backspace", None
        if b == 21:
            return "clear", None
        if b == 14:
            return "down", None
        if b == 16:
            return "up", None
        if b == 27:
            # Esc, or the prefix of an arrow key. Only a real escape sequence
            # has more bytes already waiting; a lone Esc is the user cancelling.
            if self._select.select([self._fd], [], [], 0.05)[0]:
                rest = self._in.read(2)
                if rest[-1:] == b"A":
                    return "up", None
                if rest[-1:] == b"B":
                    return "down", None
                return "ignore", None
            return "cancel", None
        if 32 <= b < 127:
            return "char", chr(b)
        return "ignore", None


class _WindowsTerm:
    """Console equivalent of the above.

    Reading is msvcrt against CONIN$, which is already unbuffered and unechoed,
    so there is no raw-mode dance to undo on the way out. Writing is CONOUT$
    opened by name for the same reason the POSIX half opens /dev/tty by name:
    stdout may be redirected, the console is what the user is looking at.

    Output needs ENABLE_VIRTUAL_TERMINAL_PROCESSING turned on explicitly. A
    Herdr pane is a ConPTY and normally has it, but a console that does not
    would render every escape in `render` as literal mojibake rather than
    moving the cursor -- so it is set, and the previous mode restored.
    """

    def __init__(self):
        import msvcrt
        self._msvcrt = msvcrt

    def __enter__(self):
        import ctypes
        self._ctypes = ctypes
        # encoding is explicit: the default here is the ANSI codepage (cp1252
        # on a Portuguese install), and this renders "↑↓" and "·" on every
        # frame plus whatever em dashes the window titles carry. Without it the
        # picker does not degrade -- it raises UnicodeEncodeError on first draw.
        self._out = open("CONOUT$", "w", encoding="utf-8")
        self._kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self._handle = self._msvcrt.get_osfhandle(self._out.fileno())
        self._old_mode = ctypes.c_uint32()
        self._restore_mode = False
        if self._kernel32.GetConsoleMode(
                ctypes.c_void_p(self._handle), ctypes.byref(self._old_mode)):
            ENABLE_PROCESSED_OUTPUT = 0x0001
            ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
            new = (self._old_mode.value | ENABLE_PROCESSED_OUTPUT
                   | ENABLE_VIRTUAL_TERMINAL_PROCESSING)
            if new != self._old_mode.value:
                self._restore_mode = bool(self._kernel32.SetConsoleMode(
                    ctypes.c_void_p(self._handle), new))
        return self

    def __exit__(self, *exc):
        if self._restore_mode:
            self._kernel32.SetConsoleMode(
                self._ctypes.c_void_p(self._handle), self._old_mode.value)
        self._out.write("\x1b[H\x1b[2J")
        self._out.flush()
        self._out.close()

    def write(self, s):
        self._out.write(s)

    def flush(self):
        self._out.flush()

    def read_event(self):
        ch = self._msvcrt.getwch()
        # A special key arrives as a two-call sequence led by NUL or 0xE0.
        if ch in ("\x00", "\xe0"):
            code = self._msvcrt.getwch()
            if code == "H":
                return "up", None
            if code == "P":
                return "down", None
            return "ignore", None
        if ch in ("\r", "\n"):
            return "enter", None
        if ch == "\x03":
            return "cancel", None
        if ch in ("\x08", "\x7f"):
            return "backspace", None
        if ch == "\x15":
            return "clear", None
        if ch == "\x0e":
            return "down", None
        if ch == "\x10":
            return "up", None
        if ch == "\x1b":
            # No arrow ever reaches here as an escape sequence -- the console
            # already reported those as 0xE0 pairs above -- so Esc is
            # unambiguously cancel, with none of the POSIX half's timing guess.
            return "cancel", None
        if ch >= " " and ch != "\x7f":
            return "char", ch
        return "ignore", None


def _terminal():
    return _WindowsTerm() if sys.platform == "win32" else _PosixTerm()


def pick(items, initial=0, title="Switch window"):
    """Run the picker. Returns (1-based index, title) or None if cancelled."""
    query, sel = "", initial
    # Rows are (1-based index, real title, display label). The label is what is
    # shown and what the query filters on -- typing "paas" should match the row
    # that reads "paas/master" -- while the title is what gets returned, because
    # raising a window still needs its actual title.
    labels = labels_for(items)

    with _terminal() as term:
        def render(view):
            term.write("\x1b[H\x1b[2J")
            term.write("  {}\x1b[0m\r\n".format(title))
            term.write("  \x1b[2m{}/{}\x1b[0m  \x1b[1m{}\x1b[0m\x1b[7m \x1b[0m\r\n\r\n"
                       .format(len(view), len(items), query))
            for i, (_, _title, lab) in enumerate(view[:MAX_ROWS]):
                if i == sel:
                    term.write("  \x1b[7m > {} \x1b[0m\r\n".format(lab))
                else:
                    term.write("    \x1b[2m>\x1b[0m {}\r\n".format(lab))
            if not view:
                term.write("    \x1b[2mno match\x1b[0m\r\n")
            term.write("\r\n  \x1b[2mtype to filter · ↑↓ move · "
                       "enter switch · esc cancel\x1b[0m")
            term.flush()

        while True:
            view = [(i, n, lab)
                    for i, (n, lab) in enumerate(zip(items, labels), 1)
                    if matches(query, lab)]
            sel = max(0, min(sel, len(view) - 1))
            render(view)
            event, ch = term.read_event()
            if event is None:
                return None
            if event == "enter":
                # (index, title) -- the label was for the eyes only.
                return view[sel][:2] if view else None
            if event == "cancel":
                return None
            if event == "backspace":
                query, sel = query[:-1], 0
            elif event == "clear":
                query, sel = "", initial
            elif event == "down":
                sel += 1
            elif event == "up":
                sel -= 1
            elif event == "char":
                query, sel = query + ch, 0
