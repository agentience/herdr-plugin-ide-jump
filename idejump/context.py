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
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
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
        # foreground_cwd, never cwd: Herdr CONSUMES OSC 7 from a pane and writes
        # the reported directory into `cwd`, so `cwd` is only as fresh as the
        # last OSC 7 that pane saw. `foreground_cwd` is read from the foreground
        # process and is right whether or not any shell emits OSC 7 at all.
        return data["result"]["pane"]["foreground_cwd"] or ""
    except Exception:
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
