"""macOS backend: enumerate and raise windows through System Events.

Deliberately NOT the `code` CLI. A window title is not a folder path -- it
carries mutable suffixes like " -- Modified" or " -- 1 problem in this file" --
so the CLI can only be pointed at a directory, and cannot be asked to raise the
window that is already showing one. The accessibility API can, and it works for
any application rather than only for editors that ship a CLI.

Three things this has to get right, all learned the hard way:

PROCESS IDENTITY. The accessibility process name is not the app name. VS Code
reports as "Code", but a VS-Code-derived editor that did not rename its
executable reports as "Electron" -- Kiro does, and so does every unrelated
Electron app and every `npm install electron` dev tree on the machine. Measured
on one laptop: two processes named "Electron", the first with no windows at all.
Resolving by name alone silently drives the wrong one and the plugin looks
broken rather than misconfigured. So `bundle_path` wins when configured, and
otherwise a name tie is broken by window count.

SPEED. Every process access here is addressed by pid, never by a reference held
from `every process whose ...`. AppleScript re-evaluates the filter on each
dereference of such a reference, so `repeat with w in windows of proc` costs one
full process enumeration per window: measured at 10-14 seconds for ten windows,
against 0.2 seconds for the identical work through
`first application process whose unix id is <pid>`. The plugin action simply
hung. Selection therefore happens in Python between two cheap osascript calls,
rather than inside one clever script.

Finding the pid does not use System Events at all, because a
`whose background only is false` filter costs ~0.5s and the cost is the
enumeration itself, not the property being read -- so asking it for ids, names
and bundle paths meant three filters and ~1.5s before a single window title had
been fetched. `ps` is the same answer for ~0.05s. What remains is one
ENUM_WINDOWS round trip at ~0.7s, which is the real work and the floor for this
approach; getting under it means talking to the accessibility API directly
instead of through osascript.

WINDOW IDENTITY. Matching is by title, never by index: window z-order was
observed changing between two listings minutes apart, so an index captured
during enumeration is stale by the time the raise runs. The index is passed only
as a last-resort fallback for when the title changed underneath us.
"""
import subprocess

# Process discovery is `ps`, not System Events -- see SPEED above. Validated
# against `unix id/name/POSIX path of (every process whose background only is
# false)` on a 26-GUI-process machine: every one present, with byte-identical
# name and bundle path, in 0.048s against 1.33s.
#
# Two shapes have to survive the walk, and a rule that handles one naturally
# breaks the other:
#   * Helpers nest a bundle inside their parent -- ".../Visual Studio Code.app/
#     Contents/Frameworks/Code Helper (Plugin).app/Contents/MacOS/...". They
#     share names with each other in the dozens and own no windows, so letting
#     them through would swamp the ambiguity tiebreak below with processes that
#     can never be the answer. They are excluded by Contents/Frameworks.
#   * A few apps nest a bundle inside their own Contents/MacOS -- Docker is
#     "/Applications/Docker.app/Contents/MacOS/Docker Desktop.app/Contents/
#     MacOS/Docker Desktop". Taking the OUTERMOST .app drops these entirely,
#     which is why the innermost qualifying bundle wins instead.
PS_ARGS = ["ps", "-axwwo", "pid=,comm="]

COUNT_WINDOWS = '''
on run argv
  tell application "System Events"
    tell (first application process whose unix id is (item 1 of argv as integer))
      return count windows
    end tell
  end tell
end run
'''

ENUM_WINDOWS = '''
on run argv
  tell application "System Events"
    tell (first application process whose unix id is (item 1 of argv as integer))
      set out to ""
      repeat with w in windows
        set out to out & (name of w) & linefeed
      end repeat
      return out
    end tell
  end tell
end run
'''

RAISE = '''
on run argv
  set thePid to (item 1 of argv) as integer
  set target to item 2 of argv
  set idx to (item 3 of argv) as integer
  tell application "System Events"
    tell (first application process whose unix id is thePid)
      set names to {}
      repeat with w in windows
        set end of names to name of w
      end repeat
      set hit to 0
      repeat with i from 1 to count of names
        if item i of names is target then
          set hit to i
          exit repeat
        end if
      end repeat
      if hit is 0 then set hit to idx
      if hit is 0 then return
      perform action "AXRaise" of window hit
      -- frontmost on the process itself rather than `tell application <name> to
      -- activate`, so this needs no correct app name and works for an editor
      -- whose bundle name and process name disagree.
      set frontmost to true
    end tell
  end tell
end run
'''


# Set by the caller so a timeout or a script error says so somewhere. Without
# it both look identical to "the app has no windows", which is the wrong
# diagnosis for either.
report = None


def _note(msg):
    if report:
        report(msg)


def _osascript(script, *args, timeout=15):
    try:
        r = subprocess.run(["osascript", "-e", script] + [str(a) for a in args],
                           capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        _note("osascript timed out after {}s".format(timeout))
        return ""
    if r.returncode != 0:
        _note("osascript failed rc={} {!r}".format(
            r.returncode, (r.stderr or "").strip()[:200]))
        return ""
    return r.stdout


def _running_apps():
    """(pid, process_name, bundle_path) for every running application bundle."""
    try:
        r = subprocess.run(PS_ARGS, capture_output=True, text=True, timeout=10)
    except (subprocess.TimeoutExpired, OSError) as exc:
        _note("ps failed {!r}".format(exc))
        return []
    rows = []
    for line in r.stdout.splitlines():
        pid, _, exe = line.strip().partition(" ")
        exe = exe.strip()
        if not pid.isdigit() or "/Contents/Frameworks/" in exe:
            continue
        # Innermost .app whose remainder is exactly /Contents/MacOS/<name>.
        found = None
        at = exe.find(".app/")
        while at != -1:
            bundle, rest = exe[:at + 4], exe[at + 4:]
            leaf = rest.rsplit("/", 1)[-1]
            if rest == "/Contents/MacOS/" + leaf:
                found = (bundle, leaf)
            at = exe.find(".app/", at + 1)
        if not found:
            continue
        bundle, leaf = found
        # System Events calls an executable named "Docker Desktop.app" just
        # "Docker Desktop". Match that, so a process_name copied out of System
        # Events still resolves.
        if leaf.endswith(".app"):
            leaf = leaf[:-4]
        rows.append((int(pid), leaf, bundle))
    return rows


class MacOSBackend:
    name = "macos"

    def __init__(self, app):
        self.app = app
        self._pid = None

    def _candidates(self):
        """(pid, name, bundle_path) for every process that could be the target."""
        rows = _running_apps()
        want_path = (self.app.bundle_path or "").rstrip("/")
        if want_path:
            return [r for r in rows if r[2].rstrip("/") == want_path]
        return [r for r in rows if r[1] == self.app.process_name]

    def pid(self):
        """The target process, chosen once per run."""
        if self._pid is not None:
            return self._pid
        hits = self._candidates()
        if not hits:
            self._pid = 0
        elif len(hits) == 1:
            self._pid = hits[0][0]
        else:
            # Ambiguous name (the "Electron" case). The one actually showing
            # windows is the one the user means.
            def wins(row):
                out = _osascript(COUNT_WINDOWS, row[0]).strip()
                return int(out) if out.isdigit() else 0
            self._pid = max(hits, key=wins)[0]
        return self._pid

    def list_windows(self):
        pid = self.pid()
        if not pid:
            return []
        out = _osascript(ENUM_WINDOWS, pid)
        return [ln for ln in (l.rstrip() for l in out.splitlines()) if ln]

    def raise_window(self, title, index=0):
        pid = self.pid()
        if not pid:
            return
        _osascript(RAISE, pid, title, index)
