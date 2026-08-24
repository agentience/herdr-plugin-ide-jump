# Publishing ide-jump

**Last Updated: 2026-08-24 09:32**

`agentience.ide-jump` is a Herdr plugin that gets you back to your IDE: one key
raises the editor window for the focused pane's project, another opens a
filterable popup already sitting on that project. It is **built, linked,
published, and confirmed indexed in the marketplace** — Troy's `prefix+alt+c`
and `ctrl+shift+w` both route through it live on this machine. **Every required
item is now closed** — including the install path, exercised end to end from
GitHub on 2026-08-24 and then reverted to the local link. **The live question is
now PR #1**, a Windows backend from the first outside contributor: verified
green on macOS 2026-08-24, but it carries one deliberate behaviour change to
`pick` that is Troy's call. See *Decisions needed*.

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
- **`ff5193b` is HEAD and is pushed** (2026-08-24 09:15) — adds
  `docs/jump-popup.png` and the README reference. The only thing left in the
  working tree is the untracked source `jump-popup.jpg` at the repo root, kept
  deliberately as the uncropped original; delete it or leave it, but the README
  points at the PNG.

## Decisions needed

**PR #1 changes what `pick` does when nothing matches — accept or ask for it to
be dropped.** Today `pick` shows the list with an unrelated first row
preselected; the PR makes it run `open_command` and open the project instead,
falling back to the list only when opening fails. The README currently states
the opposite in as many words ("neither is a fallback for the other"), and that
wording was written deliberately on 2026-08-21 after checking the code.

The contributor argues the current behaviour is the real failure — the gesture
means "get me to *this* project's editor" and every row on offer is the wrong
project — and **offered to drop it**, noting it is self-contained in
`cmd_picker`. Verified on macOS 2026-08-24: the open fires, the window count
goes 6 → 7, and every fallback branch behaves (open fails → list, exactly as
before; empty root → never opens, guarded in `open_missing`).

- **Accept it.** *Recommendation.* It makes `pick` a superset of `jump`, which
  is where the two gestures were already converging — the 2026-08-21 note kept
  `jump` only because it was the sole cold-start path, and this removes that
  asymmetry. Requires a README edit, since the README would then be wrong.
- **Ask for it to be dropped.** Keeps the documented split and shrinks the PR to
  the Windows port plus the shared fixes. Costs a round trip with the
  contributor.

Whichever way it goes, **the README must be updated in the same commit** — it
currently documents the old behaviour explicitly, and this is the one place the
PR makes the docs wrong.

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
- [x] **Decide whether to keep the local link or switch to the installed copy.**
      Settled 2026-08-24 09:17: **keep the local link.** The install path is now
      proven, so there is nothing left that the installed copy tests, and the
      link is the better development posture. Working tree is linked again and
      verified.
- [x] **Test the install path once from a clean state.** Done 2026-08-24
      09:15–09:17, whole cycle, machine returned to its starting state. What
      happened:
      `herdr plugin unlink agentience.ide-jump` → `{"removed":true}`;
      `herdr plugin install agentience/herdr-plugin-ide-jump -y` → **exit 0**,
      resolved `commit ff5193b`, printed a preview listing 2 actions, 1 pane and
      **0 build commands**, and registered as
      `[github:agentience/herdr-plugin-ide-jump@ff5193ba…]` with the id
      `agentience.ide-jump` — the id Troy's keybindings name, so they kept
      working untouched. The clone landed at
      `~/.config/herdr/plugins/github/agentience.ide-jump-<hash>/`, complete
      (`idejump/`, `examples/`, `docs/`, manifest), and `python3 ide_jump.py
      list` ran from it. `herdr plugin action invoke …jump` against the
      installed copy: `plugin-log-58`, **exit 0 in 679ms**, plugin log
      `match=0` — resolved via `plugin context workspace_label` and raised the
      right window. Then re-linked and re-verified: `plugin-log-59`, exit 0,
      751ms, `match=0`.
      **Two things learned, both new:**
      1. **`herdr plugin link <dir>` over an *installed* plugin just works** and
         silently replaces the registration — no unlink needed. That is the
         reverse of the documented direction (install over a *linked* plugin is
         refused), so the asymmetry is real: link wins, install does not.
      2. **Uninstall is therefore never reached, and it leaves the clone behind.**
         `herdr plugin uninstall agentience.ide-jump` was rejected with a bare
         `usage:` line, and after re-linking there was no registry entry pointing
         at the clone at all — 456K orphaned on disk. Deleted by hand after
         confirming nothing under `~/.config/herdr` or `~/.local/state/herdr`
         referenced it. **If you run this test again, clean up that directory.**
      **Config survives the round trip** — `herdr plugin config-dir` reported
      `~/.config/herdr/plugins/config/agentience.ide-jump` before, during and
      after, because it keys on the plugin id, not the source.
- [ ] **(in progress)** **PR #1 — Windows backend from `tiagoaquino`.**
      https://github.com/agentience/herdr-plugin-ide-jump/pull/1, opened
      2026-08-22, +813/-94 across 8 files. The first outside contribution.
      **macOS regression-verified 2026-08-24 09:25–09:32; the only thing
      blocking a merge is the `pick` decision above.**
      Checked out as a worktree at `../ide-jump-pr1` on branch `pr-1-windows`,
      **deliberately not in this directory** — this one is what
      `herdr plugin link` points at, so checking the PR out here would put
      untested code under Troy's live keybindings.
      What was verified on this Mac:
      `list` output byte-identical to main; `find_index`/`preselect_index`
      differential-tested across all six real window titles plus three
      negatives — **zero divergence**, so the new path- and segment-matching
      rules are inert on `${rootName}` titles as the author claimed; perf
      **297ms median vs main's 313ms**, interleaved, 5 runs each, so the 298ms
      floor holds; `jump` through Herdr exit 0 in 630ms with `match=0`; the
      popup pane launched under Herdr with a working `/dev/tty` and the right
      preselect; `termios` confirmed **not** imported at module scope while
      the module still imports on darwin; and the PR merges into current `main`
      cleanly with the `docs/jump-popup.png` README line intact.
      Two shared changes are real fixes that apply to macOS, not just Windows:
      **`resolve_root()`** — `why` on main prints `root: (none)` on a labelled
      workspace and the PR prints the actual path, confirming cold start could
      never fire; and **explicit UTF-8** on `_run`, the log file and the picker
      console.
      Not verified, and cannot be from here: **anything Windows.** The author
      tested on Windows 11 / Herdr 0.8.x / VS Code. Taking that on trust is the
      whole of the risk in merging, and it is contained — `windows.py` is only
      reachable under `sys.platform == "win32"`.
      **Next step: settle the `pick` divergence** (see *Decisions needed*),
      then merge. Remember to `git worktree remove ../ide-jump-pr1` and delete
      the local `pr-1-windows` branch afterwards.
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

- **`herdr plugin install` from GitHub — verified 2026-08-24 09:15–09:17.**
  Full unlink → install → invoke → re-link cycle against `ff5193b`. Install
  exit 0, clone complete, action ran from the installed copy (`plugin-log-58`,
  679ms, `match=0`), re-link verified (`plugin-log-59`, 751ms, `match=0`).
  Details and the two gotchas are on the work item.

- **PR #1 against macOS — verified 2026-08-24 09:25–09:32**, in a worktree at
  `../ide-jump-pr1`, never under the live link. Enumeration identical, matching
  differential-tested to zero divergence, no perf regression (297ms vs 313ms),
  `jump` and the popup pane both green through Herdr, merges clean. Detail on
  the work item.

**NOT verified — do not assume:**
- **Anything on a non-macOS platform.** There is no other backend.
- **Kiro's `raise`.** Enumeration was verified against Kiro; raising a Kiro
  window was not.
- **The whole of PR #1's Windows path.** No Windows machine here. Trusting the
  contributor's report is the only risk in merging, and `windows.py` is
  unreachable off `win32`.

## Don't touch

- **The two scripts the plugin replaced**, `~/.claude/scripts/herdr-code-window.sh`
  and `~/.claude/scripts/vscode-window-switch.py`. They are the revert path
  until the keypress check passes. They are also the historical record of the
  cwd-based resolution that had to be dropped.
- **`min_herdr_version = "0.7.4"`** without a reason. That is the release whose
  changelog adds popup plugin panes. It has only ever been run on 0.8.2.

## Open loops with others

**Not this project's work, but discovered while checking Discord and it is
waiting on Troy.** On 2026-08-23 19:36 UTC `patweb99` asked in `sanvio`:
"Hey, mind reviewing my blog post here? Thanks!" with a Substack preview link
(`sanviolabs.substack.com/p/2c67573e-b8d8-4838-af06-af7da4747e68`). Nobody has
answered it. Flagged here only so it is not lost — it has nothing to do with
ide-jump, and this session did not act on it.

No AMQ traffic occurred; there is no `## AMQ coordination` section.

## Window slug

`ide-jump-pr1-windows`

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

- 2026-08-24 09:14 — Read-mode session. **Both non-gated items closed.**
  *Discord*: read the last 25 messages in `sanvio` off the Discord API — the
  announcement drew **no reply and no reaction**, so there is still no outside
  feedback and no first-user bug report. Recorded how to read a channel, since
  the `discord-notify` skill only sends and the next person will hit that too.
  *Screenshot*: Troy had already re-cropped `jump-popup.jpg` at 09:00, after the
  previous entry described it as 1000x839 — it was 517x416 by the time this
  session opened it, but still had terminal bleed on both edges and ~40% empty
  black below the rows. Cropped tight to the popup box, closed the box with a
  redrawn border, and saved `docs/jump-popup.png` (472x242, native resolution —
  a 2x upscale was tried first and looked soft against the JPEG artefacts).
  Referenced it from the README under the opening paragraph. Also surfaced an
  unrelated ask sitting in that Discord channel since 2026-08-23 — patweb99
  wants a blog post reviewed — under a new *Open loops with others* section.
  **Nothing committed**; the install-path test is untouched and still wants
  Troy's word.

- 2026-08-24 09:18 — **Install path tested and the plugin is feature-complete
  for v0.1.** Committed and pushed `ff5193b` (the cropped screenshot plus its
  README reference), then ran the full cycle Troy authorised: unlink → install
  from `agentience/herdr-plugin-ide-jump` → invoke `jump` against the installed
  copy → uninstall → re-link this working tree → invoke again. Both invocations
  exit 0 with `match=0`, 679ms installed and 751ms linked. Machine is back
  exactly where it started: linked to the working tree, same config dir, and the
  orphaned 456K clone the test left in `~/.config/herdr/plugins/github/` removed
  by hand. Two undocumented behaviours found and written onto the work item —
  `plugin link` silently overrides an installed plugin (the reverse of install,
  which refuses), and because of that `uninstall` is never reached, so the clone
  is orphaned rather than cleaned. Slug moved `ide-jump-install-test` →
  `ide-jump-v02-reverse`: only optional work remains, and the reverse jump is the
  next thing anyone would pick up.

- 2026-08-24 09:32 — **Reviewed and macOS-verified PR #1**, the Windows backend
  from `tiagoaquino` — the first outside contribution, and the first evidence
  anyone else is running this. Read the diff rather than trusting it: the
  Windows module is behind the existing seam, but the PR also touches
  `picker.py` (399 lines, terminal handling split into two classes),
  `ide_jump.py` and `context.py`, and the author says outright that the macOS
  path is untested. Checked it out as a worktree at `../ide-jump-pr1` so the
  live link kept pointing at `main`, then ran the regression set: enumeration
  byte-identical, `find_index` differential-tested across every real window
  title plus negatives with **zero divergence**, perf 297ms vs 313ms (no
  regression against the 298ms floor), `jump` and the popup pane both green
  through Herdr, `termios` still deferred, merge clean with the screenshot
  intact. Two of its shared changes are genuine macOS fixes — `resolve_root()`
  (cold start was unreachable on a labelled workspace: `why` proves it, main
  says `root: (none)`) and explicit UTF-8 decoding. **One thing needs Troy:**
  the PR deliberately makes `pick` open the editor on no-match instead of
  listing, which contradicts the README; verified working with all fallbacks
  intact, written up under *Decisions needed* with a recommendation to accept.
  Live plugin re-linked to `main` and re-verified (`plugin-log-61`, 615ms).
