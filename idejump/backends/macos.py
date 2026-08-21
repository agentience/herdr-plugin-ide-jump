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

WINDOW IDENTITY. Matching is by title, never by index: window z-order was
observed changing between two listings minutes apart, so an index captured
during enumeration is stale by the time the raise runs. The index is passed only
as a last-resort fallback for when the title changed underneath us.
"""
import subprocess

# Bulk plural queries only. `unix id of (every process whose ...)` is one round
# trip; `repeat with p in (every process whose ...)` followed by `unix id of p`
# re-runs the filter on every dereference and takes tens of seconds. Same trap
# as SPEED above, one level up. Three filters at ~0.5s each in one osascript
# process beats one loop that looks tidier.
LIST_PROCS = '''
tell application "System Events"
  set AppleScript's text item delimiters to linefeed
  set idsText to (unix id of (every process whose background only is false)) as text
  set namesText to (name of (every process whose background only is false)) as text
  set pathsText to ""
  try
    set pathsText to (POSIX path of (file of (every process whose background only is false))) as text
  end try
  return idsText & linefeed & "\t--\t" & linefeed & namesText & linefeed & "\t--\t" & linefeed & pathsText
end tell
'''

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


class MacOSBackend:
    name = "macos"

    def __init__(self, app):
        self.app = app
        self._pid = None

    def _candidates(self):
        """(pid, name, bundle_path) for every process that could be the target."""
        out = _osascript(LIST_PROCS)
        blocks = out.split("\t--\t")
        if len(blocks) < 3:
            return []
        ids, names, paths = [b.strip().splitlines() for b in blocks[:3]]
        rows = []
        for i, raw in enumerate(ids):
            if not raw.strip().isdigit():
                continue
            rows.append((
                int(raw.strip()),
                names[i].strip() if i < len(names) else "",
                paths[i].strip() if i < len(paths) else "",
            ))
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
