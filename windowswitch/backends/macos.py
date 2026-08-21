"""macOS backend: enumerate and raise windows through System Events.

Deliberately NOT the `code` CLI. A window title is not a folder path -- it
carries mutable suffixes like " -- Modified" or " -- 1 problem in this file" --
so the CLI can only be pointed at a directory, and cannot be asked to raise the
window that is already showing one. The accessibility API can, and it works for
any application rather than only for editors that ship a CLI.

Matching is by title, never by index: window z-order was observed changing
between two listings minutes apart, so an index captured during enumeration is
stale by the time the raise runs. The index is passed only as a last-resort
fallback for the case where the title has changed underneath us.
"""
import subprocess

ENUM = '''
on run argv
  set procName to item 1 of argv
  tell application "System Events"
    if not (exists process procName) then return ""
    tell process procName
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
  set procName to item 1 of argv
  set appName to item 2 of argv
  set target to item 3 of argv
  set idx to (item 4 of argv) as integer
  tell application "System Events" to tell process procName
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
  end tell
  tell application appName to activate
end run
'''


class MacOSBackend:
    name = "macos"

    def __init__(self, app):
        self.app = app

    def list_windows(self):
        r = subprocess.run(
            ["osascript", "-e", ENUM, self.app.process_name],
            capture_output=True, text=True,
        )
        if r.returncode != 0:
            return []
        return [ln for ln in (l.rstrip() for l in r.stdout.splitlines()) if ln]

    def raise_window(self, title, index=0):
        subprocess.run(
            ["osascript", "-e", RAISE,
             self.app.process_name, self.app.app_name, title, str(index)],
            capture_output=True, text=True,
        )
