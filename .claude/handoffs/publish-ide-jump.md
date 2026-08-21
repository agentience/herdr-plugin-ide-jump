# Publishing ide-jump

**Last Updated: 2026-08-21 16:02**

`agentience.ide-jump` is a Herdr plugin that gets you back to your IDE: one key
raises the editor window for the focused pane's project, another opens a
filterable popup already sitting on that project. It is **built, linked, and
running live on this machine** — Troy's `prefix+alt+c` and `ctrl+shift+w` both
route through it. What remains is publication and two manual checks.

It was built inside the IFTI repo's session on 2026-08-21 and handed over here
because the work is no longer about IFTI. The originating document is
`~/Development/IFTI/ifti_dev2/.claude/handoffs/herdr-terminal-adoption.md`,
which covers the wider Herdr adoption (relaunch hook, Cmd+click, herdr-spreader
PRs) and is **not** needed to finish this — everything load-bearing was copied
down. Read it only for the Herdr-adoption context around it.

## State

- Four commits on `master`, **no remote**. `git log --oneline` in this repo.
- Registered with `herdr plugin link`, so edits to this working tree take effect
  on the next invocation — no reinstall while iterating.
- `herdr plugin list` shows it as
  `local:/Users/troymolander/Development/Agentience/herdr-plugin-ide-jump`.
- Troy's keybindings in `~/.config/herdr/config.toml` are `type =
  "plugin_action"` pointing at `agentience.ide-jump.jump` and `.pick`. Backups
  of that file are at `~/.config/herdr/config.toml.bak.*`; the two scripts the
  plugin replaced (`~/.claude/scripts/herdr-code-window.sh` and
  `vscode-window-switch.py`) are untouched on disk, so a revert is one `cp`.

## Decisions needed

**Which GitHub account owns the repo.** `herdr plugin install` takes GitHub
shorthand only (`owner/repo[/subdir]`), so publication needs a public repo.
Recommendation: **`tmolander/herdr-plugin-ide-jump`** — that account already
carries the herdr-spreader fork whose PRs #17/#18 are open upstream, so the
plugin lands as a second thread in the same community rather than under a new
identity. Troy has ruled out any `trellios` naming; the id is `agentience.ide-jump`
and should not change again, because the id is what user keybindings reference
and what `herdr plugin config-dir` keys on.

Nothing else is open.

## Work items

> **Keep this current.** Tick items as you complete them, add ones you discover,
> and update **Last Updated** each time you edit this file. The next session
> after you reads this file, not your transcript.

- [ ] **Press `ctrl+shift+w` and `prefix+alt+c` once each.** The only check that
      could not be automated. A selftest proved the popup launches and hands the
      picker a working `/dev/tty`
      (`herdr plugin pane open --plugin agentience.ide-jump --entrypoint picker
      --env IDE_JUMP_SELFTEST=1`), but **raw-mode keyboard handling inside a
      Herdr popup has never taken a real keystroke** — arrows, filtering, Enter,
      Esc are all unproven. Expected: `ctrl+shift+w` opens the list with the
      current repo highlighted, Enter jumps, Esc closes; `prefix+alt+c` jumps
      with no UI.
      If a key does nothing, read the log **before** suspecting the wiring —
      see Troubleshooting below.
- [ ] **Create the GitHub repo and push.** Public. Then
      `git remote add origin …` and `git push -u origin master`.
- [ ] **Add the GitHub topic `herdr-plugin`.** That is the entire marketplace
      mechanism: it indexes public repos carrying that topic whose
      `herdr-plugin.toml` parses, at the root or in a subdirectory of the
      default branch. Index refreshes every 30 minutes.
- [ ] **Decide whether to keep the local link or switch to the installed copy.**
      Installing over a locally linked plugin is **refused** — it needs
      `herdr plugin unlink agentience.ide-jump` first. Keeping the link is the
      better development posture; switch only to test the install path end to
      end, and re-link afterwards.
- [ ] **Test the install path once from a clean state**, ideally after
      unlinking: `herdr plugin install tmolander/herdr-plugin-ide-jump`. There
      are no `[[build]]` commands, so install is a clone plus registration —
      but it has never been exercised.
- [ ] Optional: **README screenshot or a short cast of the picker.** The
      marketplace card is a repo card; nothing sells a picker like seeing it.
- [ ] Optional: **v0.2 — the reverse jump.** A key inside the editor that raises
      the Herdr pane for that repo. The plugin was named `ide-jump` rather than
      `back-to-ide` specifically so this lands inside it rather than needing a
      second plugin. Herdr side is `herdr pane focus`/`workspace` over
      `HERDR_BIN_PATH`; the editor side is a VS Code task or keybinding, which
      is the unresearched half.
- [ ] Optional: **X11 backend.** `windowswitch`-era notes live in
      `idejump/backends/__init__.py`: `wmctrl -l` to enumerate, `wmctrl -i -a`
      to raise. Wayland is deliberately out — no standard raise API, and the
      manifest declares `platforms = ["macos"]` rather than overpromising.

## How it is put together

Read `README.md` first; it is written for a user, not a maintainer. The parts
that are not obvious from the code:

- **`pick` and `picker` are two entrypoints for one gesture.** Action commands
  run detached with no terminal, so an action cannot host an interactive list.
  `pick` exists only to call `herdr plugin pane open` for the `picker` pane,
  forwarding the resolved project through `--env`.
- **Project resolution is a name, not a path.** A Herdr workspace label already
  *is* the repo name and an editor window title already *is* the folder name, so
  matching those needs no path handling. `workspace_label` arrives directly in
  `HERDR_PLUGIN_CONTEXT_JSON`.
- **The picker depends on nothing outside the standard library** — no fzf, sk,
  peco or gum, none of which are on this machine and none of which can be
  assumed on anyone else's.

## Traps (every one of these failed silently — read before editing)

- **A plugin command's cwd is the PLUGIN directory, not the pane's.** Any
  "guess the project from `os.getcwd()`" fallback resolves to this plugin's own
  folder name: plausible-looking and always wrong. The pre-plugin script used
  that fallback correctly, because a popup keybinding inherits the pane's cwd.
  It was removed on the way in. Do not reintroduce it.
- **An AppleScript reference held from `every process whose …` re-runs that
  filter on EVERY dereference.** `set proc to p` in a loop, then
  `repeat with w in windows of proc`, costs one full process enumeration per
  window: **10–14s for ten windows**, against **0.2s** addressing the same
  process by pid. It does not error — the action simply **hung**,
  `herdr plugin log list` reported it `running` forever, and the plugin log
  stayed empty, so both instruments that normally localise a fault said nothing.
  `repeat with p in (…)` for discovery is the same trap one level up: use bulk
  plural queries (`unix id of (every process whose …)`), one round trip each.
  **Rule: get pids out in a bulk pass, then address everything by pid.**
- **A VS-Code-derived editor reports to the accessibility API as `Electron`.**
  Kiro's `CFBundleExecutable` is `Electron`; only `CFBundleName` says `Kiro`.
  VS Code's is `Code` for both, which is why VS Code hid this. The name is also
  not unique — this machine had **two** `Electron` processes (Kiro, and a stray
  `node_modules/electron` under `code-window-manager`) and the stray one sorted
  first with zero windows. Select by `bundle_path`.
- **Title matching needs the editor to put the folder name in the window
  title.** VS Code and its derivatives title by active *file* by default. Troy's
  VS Code works only because it sets `"window.title": "${rootName}"`; Kiro at
  defaults titled its window `chrome.ts`. This is a user-settings requirement,
  documented in the README, not something the plugin can fix.
- **`herdr plugin pane open --workspace <id>` is rejected for popup and overlay
  panes** (`invalid_params`, "overlay and popup plugin panes target the active
  pane"). Pass context through `--env` instead. `--placement` on that command
  does not accept `popup` either — only `overlay|split|tab|zoomed`. Declare
  `placement = "popup"` in the manifest and open with no `--placement`.
- **`HERDR_PLUGIN_STATE_DIR` is `~/.local/state/herdr/plugins/<id>/`, NOT under
  `~/.config/herdr/`** where the config dir lives. Twenty minutes went into "the
  plugin isn't logging" that was entirely searching the wrong root.
  `herdr plugin config-dir <id>` prints the config dir; there is no equivalent
  for state, so read the env var.
- **A plugin action that exits 0 with empty stdout/stderr in
  `herdr plugin log list` tells you nothing about whether its work happened.**
  `succeeded` means the command exited 0. Anything you want to know has to be
  written to the plugin's own log.

## Troubleshooting

Every invocation writes one line to
`~/.local/state/herdr/plugins/agentience.ide-jump/ide-jump.log`. When a key
"does nothing", that line separates causes that are identical from outside:

| Log says | Cause |
|---|---|
| nothing at all | never invoked — keybinding or `reload-config`, not the plugin |
| `match=-1` | ran, found no window for that project — a naming problem; compare against `python3 ide_jump.py list` and check `window.title` |
| `osascript timed out` / `osascript failed` | the accessibility call did not return — check Accessibility permission for the terminal running Herdr |

`python3 ide_jump.py why` prints the resolved project, which signal produced it,
the preselected window, and the raw invocation context. `python3 ide_jump.py
list` prints window titles.

## Verification state

**Verified live against the running Herdr server, 2026-08-21:**
- `herdr plugin link`, action listing, and `plugin config-dir`.
- `jump` through `herdr plugin action invoke`, repeatedly: resolves via
  `plugin context workspace_label`, matches, raises. Follows the *focused* pane,
  confirmed by it resolving `formworks` when focus had moved there.
- `pick` → `plugin pane open` → the popup pane launching and running the picker
  with a working `/dev/tty` (via `IDE_JUMP_SELFTEST=1`).
- Window enumeration for **VS Code** (10 windows) and **Kiro**, the latter both
  by `bundle_path` and by ambiguous process name, where the window-count
  tiebreak picks Kiro over the empty stray `Electron`.
- A full `list` completes in ~2s after the pid rewrite, against a timeout before.
- `herdr server reload-config` → `status: applied`, no diagnostics, after the
  keybindings were repointed.

**NOT verified — do not assume:**
- **Interactive picker input.** Arrows, filtering, Enter and Esc inside a Herdr
  popup have never taken a real keystroke. First work item.
- **`herdr plugin install` from GitHub.** Never run; there is no remote yet.
- **Anything on a non-macOS platform.** There is no other backend.
- **Kiro's `raise`.** Enumeration was verified against Kiro; raising a Kiro
  window was not.

## Don't touch

- **The two scripts the plugin replaced**, `~/.claude/scripts/herdr-code-window.sh`
  and `~/.claude/scripts/vscode-window-switch.py`. They are the revert path
  until the keypress check passes. They are also the historical record of the
  cwd-based resolution that had to be dropped.
- **`min_herdr_version = "0.7.4"`** without a reason. That is the release whose
  changelog adds popup plugin panes. It has only ever been run on 0.8.2.

## Window slug

`ide-jump-publish`

## Progress log

- 2026-08-21 16:02 — Document created, splitting this work out of the IFTI
  Herdr-adoption handoff now that it has its own repo. Nothing changed in the
  plugin in this entry; state as described above. Everything the next session
  needs was copied down, so the IFTI document is context, not a dependency.
