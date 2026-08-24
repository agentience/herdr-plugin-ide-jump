# Publishing ide-jump

**Last Updated: 2026-08-24 08:57**

`agentience.ide-jump` is a Herdr plugin that gets you back to your IDE: one key
raises the editor window for the focused pane's project, another opens a
filterable popup already sitting on that project. It is **built, linked,
published, and confirmed indexed in the marketplace** — Troy's `prefix+alt+c`
and `ctrl+shift+w` both route through it live on this machine. What remains is
two things gated on Troy's go-ahead (the install-path test, and landing the
picker screenshot) plus checking whether anyone has replied in the Discord
channel it was announced in.

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
honest answer is that language is not the bottleneck — a Rust port that still
shells to `osascript` would be exactly as slow. What would actually be fast is
calling `AXUIElement` directly, a native API bypassing the IPC round trip
entirely.

**The floor moved after this decision was first written, and it weakens the
case for going native.** `f314b9b` cut process discovery from three System
Events filters to `ps`; `1eb7954` (same session, 2026-08-21 16:29) then found
the same per-dereference trap one level down inside `ENUM_WINDOWS`/`RAISE` and
replaced a `repeat with w in windows` loop with a single bulk query. That took
the one remaining `osascript` round trip from ~700ms to **~217ms** (the whole
popup list render is 298ms). `AXUIElement` would still very likely beat that —
plausibly tens of ms rather than 217ms — but the win on the table is now a few
hundred milliseconds, not most of a second. It is a smaller prize for the same
cost (see below), which is why *leave it* is a stronger recommendation now
than it was when this was first raised.

The cost is the plugin's best property. It is standard-library Python with no
`[[build]]` step, so `herdr plugin install` is a clone and nothing else — no
toolchain, no per-arch release binaries, nothing to go stale. Going native means
either shipping build artifacts per architecture or requiring `cargo` on the
user's machine, and it makes the X11 port a cross-compilation problem rather
than one new module.

Options, in the order I would try them:

1. **Leave it.** 298ms for the popup list, 938ms for `jump`, is no longer the
   complaint that prompted this. Costs nothing, and keeps install trivial.
   *Recommendation.*
2. **PyObjC for the AX calls, if present, falling back to osascript.** Gets the
   speed with no build step and no hard dependency, but PyObjC is not in the
   standard library, so the fast path only exists on machines that happen to
   have it.
3. **A Rust helper binary shipped per-arch via GitHub releases.** Fastest and
   the tidiest fit with Herdr, but it is the option that ends clone-and-go
   install, and it should wait until someone other than Troy is running this.

Not urgent either way — this is a "if 217ms ever annoys you" decision, not a
blocker, and a weaker one than it was: the prize shrank from ~650ms recovered
to well under that.

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

**Whether this handoff document should stay public in the repo — settled
2026-08-21.** It is tracked and committed, so it is public at
https://github.com/agentience/herdr-plugin-ide-jump alongside the code. Flagged
to Troy twice, since it carries local paths and Herdr config detail; both times
he said "commit and push." Treat as accepted — do not re-raise it.

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
- [x] **Confirm the marketplace actually picked it up.** Verified 2026-08-24
      08:57 at https://herdr.dev/plugins: `ide-jump` is in the index,
      `firstSeenAt: 2026-08-22T11:31:22Z`, current index build `generatedAt:
      2026-08-23T00:31:20Z` tracks `headCommit 5cd969f` (current HEAD, not a
      stale clone). Manifest parsed completely — id, name, version,
      `minHerdrVersion`, platforms, description all present. Catalogue is now
      762 plugins; the listing has 1 star.
- [ ] **Decide whether to keep the local link or switch to the installed copy.**
      Installing over a locally linked plugin is **refused** — it needs
      `herdr plugin unlink agentience.ide-jump` first. Keeping the link is the
      better development posture; switch only to test the install path end to
      end, and re-link afterwards.
- [ ] **Test the install path once from a clean state**, ideally after
      unlinking: `herdr plugin install agentience/herdr-plugin-ide-jump`. There
      are no `[[build]]` commands, so install is a clone plus registration —
      but it has never been exercised.
      **Doubly unblocked now** — the keypress check passed 2026-08-21 16:35
      *and* the repo is confirmed in the marketplace index. Still worth doing
      deliberately: unlinking swaps the live plugin out from under Troy's
      working keybindings, so re-link immediately afterwards
      (`herdr plugin link <this dir>`) and confirm with `herdr plugin list`.
      Troy has not yet said to go ahead. **Next actionable step for a fresh
      session, pending Troy's word.**
- [ ] **(in progress)** **Crop and land `jump-popup.jpg` in the README.** Troy
      took a screenshot 2026-08-24 08:56, untracked, sitting at the repo root
      (1000x839 JPEG). Viewed: it shows the popup pane titled "Jump to IDE
      window", body "Switch to Visual Studio Code window", a `6/6` count, six
      repo rows with **`herdr-plugin-ide-jump` correctly preselected**, and the
      hint line `type to filter · ↑↓ move · enter switch · esc cancel` — real
      evidence the preselect works. It is not usable as-is: it is a crop of a
      full screen, so fragments of other terminal panes bleed in along both the
      left and right edges, and roughly the bottom two-thirds is empty black
      below the six rows. Needs a tighter crop to just the popup, then commit
      it and add a README reference. Not yet committed — Troy has not asked for
      that either.
- [ ] **Check the `sanvio` Discord channel (id `1523531109101600851`) for
      replies.** The plugin was announced there 2026-08-21 16:39 via
      `discord-notify`, HTTP 200, ending "feedback and bug reports welcome."
      Nobody has looked since. It is the only channel where anyone other than
      Troy has been told this plugin exists, so a reply there — especially a
      bug report from a first outside user — is the single most valuable thing
      that could be waiting. Do not assume silence; check.
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
  left is one `ENUM_WINDOWS` round trip — ~0.7s then, **~217ms** after
  `1eb7954` fixed the loop below — and that is the floor for
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

**Confirmed indexed — 2026-08-24, see Work items above and Verification
state below.** This section now only needs to record the durable lesson for
whatever gets published next.

**There is no marketplace CLI command.** `herdr plugin --help` lists only
install/uninstall/link/unlink/enable/disable/list/config-dir/action/log/pane.
The marketplace is the web page **https://herdr.dev/plugins** (`/marketplace`
serves the same thing), which embeds its whole catalogue as a JSON blob in the
HTML — greppable without a browser (`grep -o '"generatedAt":"[^"]*"'` etc).

**The published index can lag for many hours, and the "refreshes every 30
minutes" figure from the Herdr docs is not something to plan around.** Two
observations of this repo's own listing showed the *same* `generatedAt:
2026-08-21T18:01:29Z` build 28 minutes apart. This repo was created 2026-08-21
23:05 UTC and did not appear as `firstSeenAt` until 2026-08-22T11:31:22Z —
over 12 hours later. Absence from a fresh listing is not evidence of a broken
manifest; check `generatedAt` against the repo's creation time before
concluding anything.

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

- **Interactive picker input — verified 2026-08-21 16:35 by Troy**, against
  `1eb7954`: arrows, filtering, Enter and Esc inside a Herdr popup all take
  real keystrokes. This was the longest-standing unknown in the project. The
  `jump-popup.jpg` screenshot (repo root, untracked) is a second record of it,
  showing the preselected row.
- **Listed in the Herdr marketplace — verified 2026-08-24 08:57.**
  `firstSeenAt: 2026-08-22T11:31:22Z`; the index build tracks `headCommit
  5cd969f`, and the manifest parsed in full.

**NOT verified — do not assume:**
- **`herdr plugin install` from GitHub.** Never run. Nothing blocks it now —
  see the work item, which wants Troy's go-ahead rather than a fix.
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

`ide-jump-install-test`

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
- 2026-08-21 16:39 — Announced the plugin in the `sanvio` Discord channel
  (id `1523531109101600851`) via the `discord-notify` skill: what it is, the
  install line, the repo link, and the three gotchas a new user hits
  (macOS-only, `bundle_path` for anything reporting as `Electron`, and the
  `window.title` requirement). Sent HTTP 200.
  **Fixed a blocker on the way:** `~/.claude/agentic-config.json` was invalid
  JSON — a missing comma between the `sanvio` and `railmetrix` channel entries —
  which made `discord-notify` exit 2 from *every* project, not just this one.
  Backed up to `~/.claude/agentic-config.json.bak.<timestamp>` before editing.
  The bot token lives in `~/.claude/agentic-config.local.json` and was untouched.
  Note for next time: the skill's named-channel flag is `--channel-name`;
  `--channel` takes a raw id, so passing a name there posts nowhere useful.

- 2026-08-24 08:57 — Refreshed for handoff. **The marketplace question closed
  itself:** the plugin has been indexed since `firstSeenAt 2026-08-22T11:31:22Z`
  and the live build tracks `headCommit 5cd969f`, so the index is following
  current HEAD and the manifest parses in full — no action was ever needed, only
  patience. Cut `## Marketplace indexing` down to the durable lesson (published
  index lags many hours; the docs' "every 30 minutes" is not plannable) and
  dropped the how-to-tell-if-it-is-broken apparatus. Corrected the AX/Rust
  decision, which still quoted a ~700ms floor: `1eb7954` cut that to ~217ms, so
  the win from going native is now a few hundred ms rather than most of a second
  — recommendation to leave it is unchanged but now rests on a smaller number.
  Fixed the same stale figure in Traps. Logged the untracked `jump-popup.jpg`
  Troy captured at 08:56 as the concrete form of the screenshot item, with what
  it shows and why it needs cropping first. Added an explicit work item to check
  the `sanvio` Discord channel for replies — announced there 2026-08-21, never
  looked at since, and the only place anyone outside this machine has been told
  the plugin exists. Window slug moved from `ide-jump-publish` to
  `ide-jump-install-test`, since publishing is finished and the install-path
  test is what remains.
