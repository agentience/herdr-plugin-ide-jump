# Publishing ide-jump

**Last Updated: 2026-08-21 16:35**

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

- Published at **https://github.com/agentience/herdr-plugin-ide-jump** (public,
  default branch `main`, topic `herdr-plugin`), 2026-08-21 16:05. Seven commits;
  `origin/main` is current. The branch was always `main` locally — an earlier
  draft of this document said `master`, which was wrong.
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

**Whether to drop osascript for the accessibility API directly.** Raised
2026-08-21 when Troy asked why the plugin is Python when Herdr is Rust. The
honest answer is that language is not the bottleneck — after `f314b9b` the
remaining ~0.7s is a single `osascript` round trip to System Events, and a Rust
port that still shells to `osascript` would be exactly as slow. What would
actually be fast is calling `AXUIElement` directly, which is a native API:
plausibly ~50ms rather than ~700ms.

The cost is the plugin's best property. It is standard-library Python with no
`[[build]]` step, so `herdr plugin install` is a clone and nothing else — no
toolchain, no per-arch release binaries, nothing to go stale. Going native means
either shipping build artifacts per architecture or requiring `cargo` on the
user's machine, and it makes the X11 port a cross-compilation problem rather
than one new module.

Options, in the order I would try them:

1. **Leave it.** 0.85s is no longer the complaint that prompted this. Costs
   nothing, and keeps install trivial. *Recommendation.*
2. **PyObjC for the AX calls, if present, falling back to osascript.** Gets the
   speed with no build step and no hard dependency, but PyObjC is not in the
   standard library, so the fast path only exists on machines that happen to
   have it.
3. **A Rust helper binary shipped per-arch via GitHub releases.** Fastest and
   the tidiest fit with Herdr, but it is the option that ends clone-and-go
   install, and it should wait until someone other than Troy is running this.

Not urgent either way — this is a "if the 0.7s ever annoys you" decision, not a
blocker.

## Decisions resolved

**Which GitHub account owns the repo — settled 2026-08-21: the `agentience`
org**, not `tmolander` as this document previously recommended. Troy chose it
directly; it also matches the plugin id `agentience.ide-jump`, so the install
shorthand and the id now read as one name. `tmolander` is a member of the org
and `gh` is authed as that account, which is how the repo was created. The
`herdr-spreader` fork stays under `tmolander` — that is a fork of someone
else's project and does not belong in the org.

The id remains `agentience.ide-jump` and must not change: it is what user
keybindings reference and what `herdr plugin config-dir` keys on.

Nothing else is open.

## Work items

> **Keep this current.** Tick items as you complete them, add ones you discover,
> and update **Last Updated** each time you edit this file. The next session
> after you reads this file, not your transcript.

- [x] **Press `ctrl+shift+w` and `prefix+alt+c` once each.** Done by Troy
      2026-08-21 16:35, against `1eb7954`. The picker works interactively —
      raw-mode keyboard handling inside a Herdr popup takes real keystrokes,
      which had never been proven. Reported as "not instantaneous, but snappy
      enough" after the two perf fixes took the list render from 2080ms to
      298ms. **This was the last item gating everything else.**
- [x] **Create the GitHub repo and push.** Done 2026-08-21 16:05 —
      `agentience/herdr-plugin-ide-jump`, public, `origin/main` tracking.
- [x] **Add the GitHub topic `herdr-plugin`.** Applied and verified via
      `gh api repos/agentience/herdr-plugin-ide-jump --jq .topics`. That topic is
      the entire marketplace mechanism.
- [ ] **Confirm the marketplace actually picked it up.** Everything on our side
      is already proven, so this is pure waiting — see *Marketplace indexing*
      below for how to check and what "not there yet" means.
- [ ] **Decide whether to keep the local link or switch to the installed copy.**
      Installing over a locally linked plugin is **refused** — it needs
      `herdr plugin unlink agentience.ide-jump` first. Keeping the link is the
      better development posture; switch only to test the install path end to
      end, and re-link afterwards.
- [ ] **Test the install path once from a clean state**, ideally after
      unlinking: `herdr plugin install agentience/herdr-plugin-ide-jump`. There
      are no `[[build]]` commands, so install is a clone plus registration —
      but it has never been exercised.
      **No longer blocked** — the keypress check passed 2026-08-21 16:35. Still
      worth doing deliberately rather than casually: unlinking swaps the live
      plugin out from under Troy's working keybindings, so re-link immediately
      afterwards (`herdr plugin link <this dir>`) and confirm with
      `herdr plugin list`. Troy has not yet said to go ahead.
- [ ] Optional: **README screenshot or a short cast of the picker.** The
      marketplace card is a repo card; nothing sells a picker like seeing it.
      Now that the repo is public this is the highest-value optional item.
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
- **A System Events `whose background only is false` filter costs ~0.5s, and
  the cost is the enumeration, not the property you read.** Asking it for
  `unix id`, `name` and `POSIX path` in one script is three filters and ~1.5s,
  which is how `list` came to take 2s while spending 0.12s in Python. Process
  discovery is `ps` now (`f314b9b`) and must stay that way; if you need another
  per-process fact, get it from `ps`, never by adding a fourth filter. What is
  left is one `ENUM_WINDOWS` round trip at ~0.7s, and that is the floor for
  osascript. **The same trap lives one level down**, and did: `ENUM_WINDOWS`
  and `RAISE` both built their title lists with `repeat with w in windows`,
  and since the process reference is itself a `first ... whose unix id is`
  filter, each iteration re-resolved it — 689ms against 217ms for
  `name of every window of <proc>`, identical output (`1eb7954`). **Any new
  AppleScript here uses a bulk plural query. Never a repeat loop.**
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

## Marketplace indexing

**There is no marketplace CLI command.** `herdr plugin --help` lists only
install/uninstall/link/unlink/enable/disable/list/config-dir/action/log/pane.
The marketplace is the web page **https://herdr.dev/plugins** (`/marketplace`
serves the same thing), which embeds its whole catalogue as a JSON blob in the
HTML — so it is greppable without a browser:

```bash
curl -sS -L https://herdr.dev/plugins | grep -o '"generatedAt":"[^"]*"' | head -1
curl -sS -L https://herdr.dev/plugins | grep -c 'herdr-plugin-ide-jump'
```

**Read `generatedAt` before concluding anything.** It is a UTC timestamp on the
index build, and the published index can be *hours* stale — at 2026-08-21
23:07 UTC the live page still reported `generatedAt: 2026-08-21T18:01:29Z`,
**5h06m old** — and at 23:35 UTC it reported *the same build*, unchanged, against the "refreshes every 30 minutes" this document
previously claimed. That claim came from the Herdr docs, not from observation;
do not plan around it. Absence from an index whose `generatedAt` predates the
repo's creation (2026-08-21 23:05 UTC) means nothing at all.

**Everything on our side is already verified, so there is nothing to debug
until a fresh index skips us:**

- The repo matches the index's own upstream query exactly —
  `gh api -X GET search/repositories -f q='topic:herdr-plugin is:public repo:agentience/herdr-plugin-ide-jump'`
  returns `total_count: 1` (checked 2026-08-21 16:10).
- `herdr-plugin.toml` parses under `tomllib` with all of `id`, `name`,
  `version`, `min_herdr_version`, `platforms`, `actions`, `panes`.

That matters because the index publishes its own reject buckets alongside the
catalogue — `missingManifestCount: 20`, `invalidManifestCount: 1`,
`duplicateManifestCount: 5`, `blacklistedCount: 2` in the 18:01 build. If a
build newer than the repo lands and `ide-jump` is still missing, check whether
those counts moved rather than guessing; the catalogue had 742 plugins across
730 repositories, so this is a busy index and being crowded out is not a
failure mode, but a manifest reject is.

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
- **Speed, measured on the real Herdr invocation path** (`herdr plugin log
  list` reports `started_unix_ms`/`finished_unix_ms`, so this is the action's
  own wall time, not the CLI's — `herdr plugin action invoke` returns in ~0ms
  because actions run detached, and timing *that* measures nothing):
  `jump` **2985ms → 1726ms** and the window list the popup renders
  **2080ms → 785ms**, old vs new at `f314b9b`, verified 2026-08-21 16:27.
  Both figures are medians of 3, interleaved against a warmed System Events so
  neither side pays a cold-start cost. After `1eb7954` the list the popup
  renders is **298ms** — 2080ms → 298ms overall — and `jump` is ~938ms.
- `herdr server reload-config` → `status: applied`, no diagnostics, after the
  keybindings were repointed.

**NOT verified — do not assume:**
- ~~Interactive picker input~~ — **verified 2026-08-21 16:35 by Troy** against
  `1eb7954`: the popup takes real keystrokes and the picker works. This was the
  longest-standing unknown in the project.
- **`herdr plugin install` from GitHub.** Never run. The remote now exists, so
  this is unblocked once the keypress check passes.
- **That the marketplace actually indexed it.** Absent from the index as of
  2026-08-21 16:10 PDT, but that snapshot predates the repo — see below.
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

- 2026-08-21 16:06 — Published. Created `agentience/herdr-plugin-ide-jump`
  (public) under the `agentience` org rather than `tmolander`, per Troy;
  pushed `main`; applied the `herdr-plugin` topic and verified it via the API.
  Added `.agentics/` and `logs/` to `.gitignore` first so local tooling output
  cannot be committed by anyone working on the clone. Left the local
  `herdr plugin link` in place — the interactive picker is still unproven, and
  unlinking would confound that test. Marketplace index not yet refreshed.
- 2026-08-21 16:08 — Verified the publication end to end short of the index
  itself: the repo satisfies the marketplace's own GitHub search query, and the
  manifest parses. Corrected this document's "index refreshes every 30 minutes"
  claim — the live index was 5h06m stale when checked — and added a
  *Marketplace indexing* section so the next session does not misread a slow
  build as a broken manifest. Nothing in the plugin changed.
- 2026-08-21 16:12 — Rewrote the README's Install section, which still carried
  the `<owner>/<repo>` placeholder from before the repo existed. Now names the
  published coordinates and fills in what the placeholder version omitted: no
  build step, the `-y` and `--ref` flags, a `herdr plugin list` check that the
  registered id matches what keybindings name, and that installing over a
  linked plugin is refused. Promoted the macOS Accessibility permission out of
  Troubleshooting into a stated requirement — without it both gestures fail
  silently and look exactly like unbound keys. Pushed as `8f46782`.
- 2026-08-21 16:15 — Troy observed that `prefix+alt+c` looks redundant now that
  the picker auto-selects the active project's window. Checked the code rather
  than the README's prose: largely true, but not entirely. `cmd_jump` falls back
  to `open_missing()` → `open_command` when nothing matches, so it is the only
  gesture that handles *the editor is not open yet*; `cmd_picker` has nothing to
  preselect there, opens on an unrelated first row that Enter will raise, and
  exits 1 when no editor windows exist. The asymmetry was already deliberate —
  `find_index` returns -1 rather than 0 precisely so the two callers can differ,
  and says so in its docstring — but it was written down nowhere a user would
  look. So: kept `jump`, dropped the README's backwards claim that it is "the
  point of the plugin" and pick "the fallback", stated the real divergence, and
  reordered the keybinding block to lead with `pick`. Pushed as `61a0c78`.
- 2026-08-21 16:23 — Troy reported the popup rendering slower than an earlier
  iteration. Profiled: ~2s wall, 0.12s of it Python, the rest blocked on
  osascript. Cause was the pid rewrite (`1bae3e4`) fixing the hang by asking
  System Events for three properties in one script — three ~0.5s process
  enumerations. Replaced discovery with `ps` (`f314b9b`): **2.0s → 0.85s** for
  VS Code, 0.37s for Kiro, output byte-identical in both configurations, Kiro's
  bundle_path disambiguation re-verified against the same rival `Electron`
  processes. Also answered "why not Rust": the bottleneck is osascript IPC, so a
  Rust port at the same call boundary would be exactly as slow — see
  *Decisions needed* for the version of that question that is actually live.
- 2026-08-21 16:28 — Re-measured the perf fix on the real Herdr path after a
  first attempt produced a false negative: `git stash` had nothing to stash
  because the tree was already clean at `f314b9b`, so both arms of that A/B ran
  the *new* code and showed no difference. Redone by copying the pre-change file
  into place: `jump` 2985ms → 1726ms, `list` 2080ms → 785ms. Also corrected four
  **Last Updated**/progress-log timestamps in this document and one in the
  README that had been written from estimate rather than from `date`; they now
  come from `git log` and the clock. The times were 10-25 minutes fast.
- 2026-08-21 16:30 — Troy clarified the complaint was the popup *rendering its list*, not
  the window switch. That path is `list_windows()`. Found the SPEED trap
  repeating one level down inside `ENUM_WINDOWS`/`RAISE` — `repeat with w in
  windows` over a filtered process reference — and replaced both with
  `name of every window`: 689ms → 217ms on that call, identical output.
  Popup list render is now **298ms**, from 2080ms before either fix
  (`f314b9b` + `1eb7954`). `jump` end to end via Herdr is ~938ms, from 2985ms.
  Raise re-verified (`match=0` is a hit; no-match is `-1`).
- 2026-08-21 16:35 — **Troy pressed the keys; the picker works.** Arrows,
  filtering, Enter and Esc inside a Herdr popup all take real input — the one
  thing that could not be automated and the last item gating the rest. Verdict
  on speed after the two fixes: "not instantaneous, but snappy enough". The
  install-path test is now unblocked, pending Troy's go-ahead since it means
  briefly unlinking his live plugin. Marketplace index re-checked and still
  reporting the same 18:01Z build it reported 28 minutes earlier, so it has not
  rebuilt at all yet; absence still means nothing.
