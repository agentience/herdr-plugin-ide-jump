# Contributing

**Last Updated: 2026-08-24 09:56**

Contributions are welcome. This file covers only what you cannot work out from
the code — the README has install, configuration and the local development
loop.

## The maintainer can only test macOS

There is one machine behind this project and it runs macOS. Windows was
contributed by someone else; X11 and Wayland do not exist yet. CI checks that
the Windows backend imports and enumerates on a real Windows runner, but it
cannot open an editor or raise a window on any platform — that needs a desktop
with a real editor on it, and no runner has one.

So on anything platform-specific, **your testing is the verification**. In the
pull request, say what you exercised, on what OS and editor, and — just as
usefully — what you could not check. A PR that states plainly which parts are
unverified is far easier to accept than one that is silent about it, because
the alternative is guessing which half to distrust.

## Tests

```bash
python3 -m unittest discover -s tests -v
```

They cover the title-matching rules and the import shape. Both run on every
platform; the Windows-only tests skip elsewhere.

Matching rules are **ranked**, so when you add one, add a case proving it does
not fire where an older rule should win. The suite exists because every
platform port so far has needed a new rule.

## Standard library only

No third-party imports, in the plugin or the tests. CI fails the build on one.

This is what makes `herdr plugin install` a clone and nothing else — no build
step, no toolchain, no per-architecture binaries to go stale. It is the
plugin's best property and it is easy to lose by accident.

Platform modules are fine, but **import them inside the function or class that
needs them, never at module scope**. A top-level `import termios` is correct on
macOS and makes `picker` unimportable on Windows, which takes `jump` down with
it — `jump` needs only `find_index`, which never wanted a terminal. There is a
test asserting exactly this.

## Adding a platform

The window-manager surface is two operations wide: enumerate windows, raise
one. `idejump/backends/__init__.py` describes the contract and what X11 and
Wayland would each need. A port is one new module plus one line in
`get_backend`.

## If you touch the macOS backend

**Use bulk plural queries. Never a repeat loop.** An AppleScript reference held
from `every process whose …` re-runs that filter on every dereference, so
looping over it costs a full process enumeration per iteration: 10–14 seconds
for ten windows, against 0.2 for the same work addressed by pid. It does not
error — the action simply never returns, and the plugin log stays empty, so
nothing tells you where it went. Get pids out in one pass, then address
everything by pid.

The comments in `idejump/backends/macos.py` carry the rest.
