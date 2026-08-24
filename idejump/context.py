"""Work out which project the invocation came from.

The answer is a repo NAME, because a Herdr workspace label already is the repo
name and a VS Code window title already is the folder name -- matching those two
needs no path handling in between. Signals are tried most-reliable first, and
each returns its own reason string so `--why` can explain the outcome.

TRAP: os.getcwd() is NOT a signal here. Herdr runs plugin commands with the
PLUGIN directory as their working directory, so a cwd-based guess resolves to
this plugin's own folder name and looks plausible while being always wrong.
That fallback existed in the pre-plugin script, where cwd was inherited from the
pane, and had to be removed on the way in.
"""
import json
import os
import subprocess


def _run(cmd):
    try:
        # encoding is explicit: text=True alone decodes with the locale codec,
        # which is cp1252 on a Windows install in most of the world, while Herdr
        # and git both emit UTF-8. `pane current` carries the pane's terminal
        # title, so any accent or spinner glyph a user has on screen is enough
        # to raise UnicodeDecodeError -- inside subprocess's reader THREAD, so
        # the traceback prints but the except below still sees an empty result.
        # That failure mode is silent and total: every cwd signal becomes "",
        # taking path matching and cold start with it.
        r = subprocess.run(cmd, capture_output=True, timeout=5,
                           encoding="utf-8", errors="replace")
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception:
        return ""


def herdr_bin():
    return os.environ.get("HERDR_BIN_PATH") or "herdr"


def _herdr_json(args):
    out = _run([herdr_bin()] + args)
    if not out:
        return None
    try:
        return json.loads(out)
    except Exception:
        return None


def invocation_context():
    raw = os.environ.get("HERDR_PLUGIN_CONTEXT_JSON")
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _git_root(path):
    if not path or not os.path.isdir(path):
        return ""
    return _run(["git", "-C", path, "rev-parse", "--show-toplevel"])


def _workspace_label(ws_id):
    if not ws_id:
        return ""
    data = _herdr_json(["workspace", "list"])
    if not data:
        return ""
    result = data.get("result", data)
    items = result.get("workspaces", result) if isinstance(result, dict) else result
    if not isinstance(items, list):
        return ""
    for w in items:
        if isinstance(w, dict) and w.get("workspace_id") == ws_id and w.get("label"):
            return w["label"]
    return ""


def _focused_pane_cwd():
    data = _herdr_json(["pane", "current"])
    if not data:
        return ""
    try:
        pane = data["result"]["pane"]
    except Exception:
        return ""
    # foreground_cwd in preference to cwd: Herdr CONSUMES OSC 7 from a pane and
    # writes the reported directory into `cwd`, so `cwd` is only as fresh as the
    # last OSC 7 that pane saw. `foreground_cwd` is read from the foreground
    # process and is right whether or not any shell emits OSC 7 at all.
    #
    # But it is not always THERE. Windows builds omit the key entirely (measured
    # on 0.8.x: `pane current` returns cwd and no foreground_cwd), and indexing
    # it directly raised into the caller's except and returned "" -- so every
    # cwd-derived signal vanished on this platform without a word, taking cold
    # start and the non-label half of project resolution with it. Falling back
    # to `cwd` gives up the freshness guarantee and gets the feature back.
    return pane.get("foreground_cwd") or pane.get("cwd") or ""


def resolve_root():
    """Best directory to OPEN for the current invocation, or "".

    resolve_project() answers a different question and stops as soon as it can:
    a workspace label is enough to match a window title, which is all the
    matching path ever needed, so it returns that label with an empty root and
    never looks at a cwd. Opening the project needs a real directory, and
    "" silently means "do not open" -- so on a Herdr workspace that HAS a label,
    which is the ordinary case, cold start could never fire. This walks the cwd
    signals regardless of whether a label already answered.

    MUST NOT be called from the picker popup. `pane current` reports the FOCUSED
    pane, which is the popup itself once it is up, and Herdr runs plugin
    commands with the plugin directory as their cwd -- so the answer there is
    this plugin's own folder, and the editor would open on it. The caller that
    has the real context is the action; it forwards the result as IDE_JUMP_ROOT.
    """
    ctx = invocation_context()
    candidates = [_focused_pane_cwd(),
                  ctx.get("focused_pane_cwd") or "",
                  ctx.get("workspace_cwd") or ""]
    for c in candidates:
        root = _git_root(c)
        if root:
            return root
    # Not a repo, but a directory is still better than not opening at all.
    for c in candidates:
        if c and os.path.isdir(c):
            return c
    return ""


def resolve_project():
    """Return (name, root, reason). Any field may be empty."""
    ctx = invocation_context()

    label = ctx.get("workspace_label") or ""
    if label:
        return label, "", "plugin context workspace_label"

    ws = ctx.get("workspace_id") or os.environ.get("HERDR_WORKSPACE_ID") or ""
    label = _workspace_label(ws)
    if label:
        return label, "", "workspace label ({})".format(ws)

    # Ask the pane itself before trusting the context's cwd fields: pane.current
    # reports foreground_cwd, which is derived from the foreground process,
    # whereas `focused_pane_cwd` in the context appears to carry the pane's
    # OSC-7-populated `cwd` field and can therefore be stale.
    cwd = _focused_pane_cwd()
    root = _git_root(cwd)
    if root:
        return os.path.basename(root), root, "focused pane foreground_cwd ({})".format(cwd)

    for key in ("focused_pane_cwd", "workspace_cwd"):
        c = ctx.get(key) or ""
        r = _git_root(c)
        if r:
            return os.path.basename(r), r, "plugin context {} ({})".format(key, c)

    if cwd:
        return os.path.basename(cwd), cwd, "focused pane cwd, not a repo ({})".format(cwd)

    return "", "", "unresolved"
