"""
duplicates.py — "am I about to edit a copy that does nothing?"

THE FAILURE THIS PREVENTS
-------------------------
A live OGGI app contained 18 functions defined more than once — 21 dead copies
in total. Because later definitions overwrite earlier ones in JavaScript, editing
the wrong copy changes nothing at all, while every check still passes and the
edit looks successful. The product's own documentation ended up carrying the
instruction "patch the ACTIVE one, e.g. edit addToCart at L1896 not L1336" —
and every line number in that table was wrong.

A table of line numbers maintained by hand goes stale immediately.
A script that recomputes them cannot.

WHAT "ACTIVE" MEANS
-------------------
For scripts loaded in order, the LAST definition wins. This check reports the
active line and marks every earlier copy as dead, so an edit always lands on the
copy that actually runs.
"""

from __future__ import annotations

import re
from collections import defaultdict

from ._common import FAIL, PASS, Result, is_exempt, iter_source_files, read, rel

NAME = "duplicates"
PLAIN = "No function defined twice (editing a dead copy changes nothing)"

# Top-level declarations only. Methods inside classes/objects are allowed to
# repeat across different objects, so they are deliberately not matched.
DECL = re.compile(
    r"^(?:\s{0,2})(?:export\s+)?(?:async\s+)?"
    r"(?:function\s+([A-Za-z_$][\w$]*)"
    r"|(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?(?:function\b|\([^)]*\)\s*=>)"
    r"|class\s+([A-Za-z_$][\w$]*))",
    re.M,
)

JS_EXTS = {".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".html", ".vue", ".svelte"}


def run(cfg: dict) -> Result:
    # symbol -> list of (file, line)
    defs: dict[str, list[tuple[str, int]]] = defaultdict(list)

    for path in iter_source_files(cfg):
        if path.suffix.lower() not in JS_EXTS or is_exempt(cfg, path):
            continue
        text = read(path)
        for m in DECL.finditer(text):
            name = m.group(1) or m.group(2) or m.group(3)
            if not name:
                continue
            lineno = text.count("\n", 0, m.start()) + 1
            defs[name].append((rel(cfg, path), lineno))

    dupes = {k: v for k, v in defs.items() if len(v) > 1}

    if not dupes:
        return Result(NAME, PASS, f"All {len(defs)} functions are defined exactly once.")

    details = []
    for name, places in sorted(dupes.items(), key=lambda kv: -len(kv[1])):
        # Later definition wins, so the last one in file+line order is active.
        ordered = sorted(places, key=lambda p: (p[0], p[1]))
        active = ordered[-1]
        dead = ordered[:-1]
        details.append(
            f"{name}()  ACTIVE → {active[0]}:{active[1]}   "
            f"DEAD → {', '.join(f'{f}:{l}' for f, l in dead)}"
        )

    total_dead = sum(len(v) - 1 for v in dupes.values())
    return Result(
        NAME,
        FAIL,
        f"{len(dupes)} function(s) are defined more than once ({total_dead} dead copies). "
        f"Editing a dead copy changes nothing while appearing to work. "
        f"Fix: delete the dead copies listed below, keeping only the ACTIVE one.",
        details[:40],
    )
