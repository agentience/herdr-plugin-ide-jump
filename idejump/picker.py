"""Keyboard-only filterable list, in the feel of fzf.

Written against /dev/tty directly rather than stdin/stdout so it works inside a
Herdr popup pane, and depends on nothing outside the standard library -- no fzf,
sk, peco or gum, none of which are guaranteed present on the machine the plugin
is installed on.
"""
import select
import termios
import tty

MAX_ROWS = 15


def matches(query, item):
    """Case-insensitive subsequence match, the way fzf feels."""
    if not query:
        return True
    it = iter(item.lower())
    return all(ch in it for ch in query.lower())


def find_index(items, project):
    """Index of the window belonging to `project`, or -1 if none does.

    A title is the folder name plus a mutable status suffix, e.g.
    "trade-advisor — Modified". Match the whole title first, then the head
    before a separator, so "articles" never matches "articles-archive".

    Returns -1 rather than 0 for "no match" because the two callers need
    different things from that case: the picker opens on the first row anyway,
    while `jump` must NOT raise an arbitrary window when it found nothing.
    """
    if not project:
        return -1
    for i, name in enumerate(items):
        if name == project:
            return i
    for sep in ("\u2014", "\u2013", " - "):
        for i, name in enumerate(items):
            if name.split(sep)[0].strip() == project:
                return i
    return -1


def preselect_index(items, project):
    """Row the picker should open on: the project's window, else the first."""
    return max(0, find_index(items, project))


def pick(items, initial=0, title="Switch window"):
    """Run the picker. Returns (1-based index, title) or None if cancelled."""
    tty_in = open("/dev/tty", "rb", buffering=0)
    tty_out = open("/dev/tty", "w")
    fd = tty_in.fileno()
    old = termios.tcgetattr(fd)
    query, sel = "", initial

    def render(view):
        tty_out.write("\x1b[H\x1b[2J")
        tty_out.write("  {}\x1b[0m\r\n".format(title))
        tty_out.write("  \x1b[2m{}/{}\x1b[0m  \x1b[1m{}\x1b[0m\x1b[7m \x1b[0m\r\n\r\n"
                      .format(len(view), len(items), query))
        for i, (_, name) in enumerate(view[:MAX_ROWS]):
            if i == sel:
                tty_out.write("  \x1b[7m > {} \x1b[0m\r\n".format(name))
            else:
                tty_out.write("    \x1b[2m>\x1b[0m {}\r\n".format(name))
        if not view:
            tty_out.write("    \x1b[2mno match\x1b[0m\r\n")
        tty_out.write("\r\n  \x1b[2mtype to filter · ↑↓ move · "
                      "enter switch · esc cancel\x1b[0m")
        tty_out.flush()

    try:
        tty.setraw(fd)
        while True:
            view = [(i, n) for i, n in enumerate(items, 1) if matches(query, n)]
            sel = max(0, min(sel, len(view) - 1))
            render(view)
            ch = tty_in.read(1)
            if not ch:
                return None
            b = ch[0]
            if b in (13, 10):                                    # enter
                return view[sel] if view else None
            if b == 3:                                           # ctrl-c
                return None
            if b in (127, 8):                                    # backspace
                query, sel = query[:-1], 0
            elif b == 21:                                        # ctrl-u
                query, sel = "", initial
            elif b == 14:                                        # ctrl-n
                sel += 1
            elif b == 16:                                        # ctrl-p
                sel -= 1
            elif b == 27:                                        # esc, or an arrow prefix
                if select.select([fd], [], [], 0.05)[0]:
                    rest = tty_in.read(2)
                    if rest[-1:] == b"A":
                        sel -= 1
                    elif rest[-1:] == b"B":
                        sel += 1
                else:
                    return None
            elif 32 <= b < 127:
                query, sel = query + chr(b), 0
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
        tty_out.write("\x1b[H\x1b[2J")
        tty_out.flush()
        tty_in.close()
        tty_out.close()
