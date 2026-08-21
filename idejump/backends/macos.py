"""macOS backend: enumerate and raise windows through System Events.

Deliberately NOT the `code` CLI. A window title is not a folder path -- it
carries mutable suffixes like " -- Modified" or " -- 1 problem in this file" --
so the CLI can only be pointed at a directory, and cannot be asked to raise the
window that is already showing one. The accessibility API can, and it works for
any application rather than only for editors that ship a CLI.

Two things this has to get right, both learned the hard way:

PROCESS IDENTITY. The accessibility process name is not the app name. VS Code
reports as "Code", but a VS-Code-derived editor that did not rename its
executable reports as "Electron" -- Kiro does, and so does every unrelated
Electron app and every `npm install electron` dev tree on the machine. Measured
on one laptop: two processes named "Electron", the first with no windows at all.
Resolving by name alone silently enumerates the wrong one and the plugin looks
broken rather than misconfigured. So `bundle_path` wins when configured, and
when resolving by name we pick the candidate with the most windows -- a tiebreak
that would have been enough on its own here.

WINDOW IDENTITY. Matching is by title, never by index: window z-order was
observed changing between two listings minutes apart, so an index captured
during enumeration is stale by the time the raise runs. The index is passed only
as a last-resort fallback for when the title changed underneath us.
"""
import subprocess

# Shared prologue: bind `proc` to the target process, or return "" / exit.
_FIND = '''
  set proc to missing value
  set bestCount to -1
  repeat with p in (every process whose background only is false)
    set isHit to false
    if bundlePath is not "" then
      try
        if (POSIX path of (file of p)) is bundlePath then set isHit to true
      end try
    else
      if (name of p) is procName then set isHit to true
    end if
    if isHit then
      set n to 0
      try
        set n to count windows of p
      end try
      if n > bestCount then
        set proc to p
        set bestCount to n
      end if
    end if
  end repeat
'''

ENUM = '''
on run argv
  set procName to item 1 of argv
  set bundlePath to item 2 of argv
  tell application "System Events"
''' + _FIND + '''
    if proc is missing value then return ""
    set out to ""
    repeat with w in windows of proc
      set out to out & (name of w) & linefeed
    end repeat
    return out
  end tell
end run
'''

RAISE = '''
on run argv
  set procName to item 1 of argv
  set bundlePath to item 2 of argv
  set target to item 3 of argv
  set idx to (item 4 of argv) as integer
  tell application "System Events"
''' + _FIND + '''
    if proc is missing value then return
    set names to {}
    repeat with w in windows of proc
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
    perform action "AXRaise" of window hit of proc
    -- frontmost on the process itself, rather than `tell application <name> to
    -- activate`, so this needs no correct app name and works for an editor
    -- whose bundle name and process name disagree.
    set frontmost of proc to true
  end tell
end run
'''


class MacOSBackend:
    name = "macos"

    def __init__(self, app):
        self.app = app

    def _args(self):
        return [self.app.process_name, self.app.bundle_path or ""]

    def list_windows(self):
        r = subprocess.run(
            ["osascript", "-e", ENUM] + self._args(),
            capture_output=True, text=True,
        )
        if r.returncode != 0:
            return []
        return [ln for ln in (l.rstrip() for l in r.stdout.splitlines()) if ln]

    def raise_window(self, title, index=0):
        subprocess.run(
            ["osascript", "-e", RAISE] + self._args() + [title, str(index)],
            capture_output=True, text=True,
        )
