# IDE Jump — a Herdr plugin

**Last Updated: 2026-08-21 15:32**

Get back to your IDE. From a [Herdr](https://herdr.dev) pane, one key raises
the editor window for *that pane's project* — no leaving the keyboard, no
hunting through a Mission Control grid of ten identical editor windows.

Two gestures:

- **Jump** raises the window belonging to the focused pane's project. No UI.
  This is the point of the plugin; the picker below is the fallback.
- **Pick** opens a popup list of every open window, already positioned on the
  focused pane's project, so the key plus Enter is the same direct jump and
  typing a few letters goes somewhere else.

macOS only today. The window-manager surface is deliberately two operations
wide — enumerate windows, raise one — so a port is one new module; see
`idejump/backends/__init__.py` for what X11 and Wayland would each need.

## Install

```bash
herdr plugin install <owner>/<repo>
```

or, to develop against a local checkout:

```bash
herdr plugin link /path/to/herdr-plugin-ide-jump
```

Requires Herdr 0.7.4 or newer (the release that added popup plugin panes) and
`python3`. Verified against Herdr 0.8.2.

## Keybindings

Herdr does not bind plugin actions for you. Add these to
`~/.config/herdr/config.toml`:

```toml
[[keys.command]]
key = "prefix+alt+c"
type = "plugin_action"
command = "agentience.ide-jump.jump"
description = "jump to this project's editor window"

[[keys.command]]
key = "ctrl+shift+w"
type = "plugin_action"
command = "agentience.ide-jump.pick"
description = "pick an editor window"
```

Then `herdr server reload-config`.

## Configuration

Optional. Write `config.json` into the directory
`herdr plugin config-dir agentience.ide-jump` prints:

```json
{
  "app_name": "Visual Studio Code",
  "process_name": "Code",
  "open_command": ["code", "{path}"]
}
```

- `app_name` — what the OS calls the application, used to bring it forward.
- `process_name` — what the accessibility API calls its process; often shorter
  than the app name (`Code`, `Cursor`).
- `open_command` — run by **jump** when no open window matches the project,
  with `{path}` replaced by the project root. Set to `null` to do nothing
  instead of opening a new window.

Nothing in the mechanism is VS-Code-specific; the defaults just happen to be.

## How it decides which project you meant

In order, stopping at the first that answers:

1. `workspace_label` from the invocation context. A Herdr workspace label is
   already the repo name and an editor window title is already the folder name,
   so this needs no path handling at all.
2. The workspace label looked up by `workspace_id`.
3. `foreground_cwd` of the focused pane, via `herdr pane current`, resolved to
   its git root — so a pane sitting in `packages/backend` and one in
   `apps/web` both land on the one window.
4. `focused_pane_cwd` / `workspace_cwd` from the invocation context.

To see which of those answered, run `python3 ide_jump.py why` from the
plugin directory: it prints the resolved project, the signal that produced it,
the preselected window, and the raw invocation context.

**The current working directory is deliberately not a signal.** Herdr runs
plugin commands with the *plugin* directory as their cwd, so a cwd-based guess
resolves to this plugin's own folder name — plausible-looking and always wrong.

## Troubleshooting

Every invocation writes one line to `ide-jump.log` under
`HERDR_PLUGIN_STATE_DIR` (in practice
`~/.local/state/herdr/plugins/agentience.ide-jump/`), falling back to the
plugin config directory and then `~/.local/state/herdr-ide-jump/`.

When a key "does nothing", that line separates the two causes that look
identical from the outside: no line at all means the command was never invoked
(a keybinding or reload problem), while a line reading `match=-1` means it ran
and found no window for that project (a naming problem — compare the resolved
project against `python3 ide_jump.py list`).

## License

MIT.
