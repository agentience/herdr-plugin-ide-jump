# Changelog

**Last Updated: 2026-08-24 09:38**

## [Unreleased]

- Windows backend, via `user32` through `ctypes` — no pywin32, no psutil, still
  standard library only. `EnumWindows` to enumerate, `SetForegroundWindow` to
  raise. Unlike macOS there is no single pid per application: an Electron editor
  runs a broker plus one renderer per window, so windows are collected across
  every process whose image matches, rather than under one pid.
- Raising attaches to the foreground window's input queue for the duration of
  the call. `SetForegroundWindow` is refused for a process that does not already
  own the foreground and flashes the taskbar button instead, which is
  indistinguishable from the plugin doing nothing.
- `picker` no longer imports `termios` at module scope. That import alone made
  the module unusable on Windows and took `jump` down with it, which needs only
  `find_index` — pure logic that never wanted a tty. Terminal handling now sits
  behind two small classes, `/dev/tty` and `CONIN$`/`CONOUT$`, and the key
  handling is written once against the events they emit.
- Match by project PATH before project name, for setups where a folder name is
  ambiguous — git worktrees laid out as `<repo>/<branch>` name every worktree
  after its branch, so `master` is every project at once. Requires a title that
  carries the path; contributes nothing when it does not, so name matching is
  unchanged for everyone else.
- Match the project name against any separated segment of the title, not only
  the head. VS Code's Windows default title puts the root name in the MIDDLE
  (`${activeEditorShort} - ${rootName} - ${appName}`), where neither existing
  test could see it. Ranked last and still compared per whole segment, so
  `articles` does not match `articles-archive`.
- `pick` opens the project when nothing matches, instead of listing other
  projects' windows with an unrelated first row for Enter to raise. The gesture
  asks for this project's editor, and every row on offer was the wrong project.
  This ends the split the README used to draw between the two gestures — both
  now handle cold start, and `pick` falls back to the list only when opening is
  not possible and there are other windows to show.
- Fix cold start never firing on a labelled Herdr workspace. `resolve_project`
  answers with the workspace label and no root, and an empty root silently means
  "do not open" — so `open_command` was unreachable on the ordinary case. Root
  resolution is now separate from project resolution.
- Fix every cwd signal vanishing on Windows. `pane current` reports no
  `foreground_cwd` there, and indexing the absent key raised into a bare
  `except` that returned `""`; it now falls back to `cwd`.
- Fix `UnicodeDecodeError` reading Herdr's output. `text=True` decodes with the
  locale codec, cp1252 on most Windows installs, while Herdr emits UTF-8 — and
  the failure lands in subprocess's reader thread, so it printed a traceback and
  still looked like an empty result. Same fix for the log file and the picker's
  console, which render window titles, `↑↓` and `·`.

## [0.1.0] - 2026-08-21

- First release. `jump` action, `pick` action, and a popup `picker` pane.
- macOS backend via System Events / `AXRaise`; configurable application, so any
  editor with ordinary windows works, not only VS Code. Verified against VS Code
  and Kiro.
- Target process resolves by `bundle_path` when configured, and breaks
  process-name ties by window count otherwise — a VS-Code-derived editor can
  report as plain `Electron` and collide with unrelated Electron processes.
- All System Events access is addressed by pid and by bulk plural query, never
  through a reference held from `every process whose …`; the latter re-runs the
  filter on each dereference and made a single jump take 14 seconds.
