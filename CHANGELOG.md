# Changelog

**Last Updated: 2026-08-21 15:32**

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
