#!/usr/bin/env python3
"""
inventory.py — the GENERATED feature ledger. Run it; never write it by hand.

WHY THIS FILE EXISTS
--------------------
The hand-written Feature Ledger was the centrepiece of the previous system and it
drifted badly: 294 of 500 functions never appeared in it, all 25 rows of its
duplicate-function table had wrong line numbers, its own header contradicted
itself four words later, and it described functions that had been deleted months
earlier.

It did not drift through carelessness. It drifted because it was an OUTPUT FORMAT
being used as a SOURCE OF RECORD — every number in it was typed from memory, so
drift was guaranteed on a schedule.

THE FIX, IN ONE SENTENCE
------------------------
Derive it, never type it. This script reads the actual source code and emits the
ledger. The gate then regenerates it and fails the build if the committed copy
differs — the same pattern `terraform-docs --output-check` and API Extractor use.
A generated ledger cannot go stale, because there is nothing to remember.

WHAT IT CANNOT DO
-----------------
No parser knows what a "feature" is. So features are declared ONCE, by a human,
as an annotation in the code:

    // @feature FEAT-0042 Buyer can order multiple colours in one order

and as a small file at features/FEAT-0042.yml. That single convention is what
turns "is anything missing?" into a set of differences a computer can compute.

OUTPUTS
-------
  docs/FEATURE-LEDGER.generated.md   ← for humans; committed; diffed by the gate
  docs/feature-inventory.json        ← for machines; used by surface_diff.py
"""

from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from checks._common import iter_source_files, load_config, read, rel  # noqa: E402

# --------------------------------------------------------------------------
# Extractors — each returns a sorted, stable list so the diff is meaningful
# --------------------------------------------------------------------------

FUNC = re.compile(
    r"^(?:\s{0,4})(?:export\s+)?(?:async\s+)?"
    r"(?:function\s+([A-Za-z_$][\w$]*)"
    r"|(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?(?:function\b|\([^)]*\)\s*=>)"
    r"|class\s+([A-Za-z_$][\w$]*))",
    re.M,
)
PY_FUNC = re.compile(r"^(?:\s{0,4})(?:async\s+)?def\s+([A-Za-z_][\w]*)|^class\s+([A-Za-z_][\w]*)", re.M)
FEATURE_TAG = re.compile(r"@feature\s+(FEAT-\d{3,5})\s*(.*)")
ROUTE = re.compile(
    r"""(?:app|router|server)\.(get|post|put|patch|delete)\s*\(\s*['"]([^'"]+)['"]"""
    r"""|case\s+['"](/[\w/:%-]+)['"]\s*:"""
    r"""|path\s*===?\s*['"](/[\w/:%-]+)['"]""",
    re.I,
)
SCREEN = re.compile(r"""(?:data-screen|id)\s*=\s*["'](screen-[\w-]+|page-[\w-]+)["']""", re.I)
SQL_TABLE = re.compile(r"create\s+table\s+(?:if\s+not\s+exists\s+)?([\w.\"]+)", re.I)
SQL_POLICY = re.compile(r"create\s+policy\s+\"?([^\"\n(]+)\"?\s+on\s+([\w.\"]+)", re.I)
EDGE_FN = re.compile(r"supabase[/\\]functions[/\\]([\w-]+)[/\\]")


def collect(cfg: dict) -> dict:
    inv: dict = {
        "generated": str(date.today()),
        "functions": [],
        "features": [],
        "routes": [],
        "screens": [],
        "tables": [],
        "policies": [],
        "edge_functions": [],
        "files": [],
    }
    seen_edge = set()

    for path in iter_source_files(cfg):
        label = rel(cfg, path)
        text = read(path)
        lines = text.count("\n") + 1
        inv["files"].append({"file": label, "lines": lines})

        m = EDGE_FN.search(str(path).replace("\\", "/"))
        if m and m.group(1) not in seen_edge:
            seen_edge.add(m.group(1))
            inv["edge_functions"].append(m.group(1))

        # Declared features (the one human-authored anchor).
        for fm in FEATURE_TAG.finditer(text):
            inv["features"].append(
                {
                    "id": fm.group(1),
                    "title": fm.group(2).strip(),
                    "file": label,
                    "line": text.count("\n", 0, fm.start()) + 1,
                }
            )

        if path.suffix == ".sql":
            for tm in SQL_TABLE.finditer(text):
                inv["tables"].append(tm.group(1).strip('"'))
            for pm in SQL_POLICY.finditer(text):
                # Split out of the f-string: older Pythons reject backslashes inside one.
                table = pm.group(2).strip('"')
                policy = pm.group(1).strip()
                inv["policies"].append(f"{table} :: {policy}")
            continue

        if path.suffix == ".py":
            for pm in PY_FUNC.finditer(text):
                name = pm.group(1) or pm.group(2)
                inv["functions"].append(
                    {"name": name, "file": label, "line": text.count("\n", 0, pm.start()) + 1}
                )
            continue

        for fnm in FUNC.finditer(text):
            name = fnm.group(1) or fnm.group(2) or fnm.group(3)
            if name:
                inv["functions"].append(
                    {"name": name, "file": label, "line": text.count("\n", 0, fnm.start()) + 1}
                )
        for rm in ROUTE.finditer(text):
            route = rm.group(2) or rm.group(3) or rm.group(4)
            verb = (rm.group(1) or "ANY").upper()
            if route:
                inv["routes"].append(f"{verb} {route}")
        for sm in SCREEN.finditer(text):
            inv["screens"].append(sm.group(1))

    # Feature registry files are the declared truth; merge them in.
    feat_dir = Path(cfg["_root"]) / "features"
    if feat_dir.exists():
        for f in sorted(feat_dir.glob("FEAT-*.yml")):
            title = ""
            for line in read(f).splitlines():
                if line.lower().startswith("title:"):
                    title = line.split(":", 1)[1].strip().strip("\"'")
                    break
            inv["features"].append({"id": f.stem, "title": title, "file": rel(cfg, f), "line": 1})

    # Stable ordering so the diff shows real change, not reshuffling.
    inv["functions"].sort(key=lambda d: (d["name"], d["file"], d["line"]))
    inv["files"].sort(key=lambda d: d["file"])
    for key in ("routes", "screens", "tables", "policies", "edge_functions"):
        inv[key] = sorted(set(inv[key]))
    # De-duplicate features by id, keeping the registry entry if present.
    by_id: dict[str, dict] = {}
    for f in inv["features"]:
        by_id.setdefault(f["id"], f)
        if f["file"].startswith("features/"):
            by_id[f["id"]] = f
    inv["features"] = [by_id[k] for k in sorted(by_id)]
    return inv


# --------------------------------------------------------------------------
# Rendering — the human-readable ledger
# --------------------------------------------------------------------------

def render(inv: dict) -> str:
    total_lines = sum(f["lines"] for f in inv["files"])
    dupes: dict[str, list[dict]] = {}
    for fn in inv["functions"]:
        dupes.setdefault(fn["name"], []).append(fn)
    dupes = {k: v for k, v in dupes.items() if len(v) > 1}

    out = [
        "# FEATURE LEDGER — GENERATED. DO NOT EDIT BY HAND.",
        "",
        "> Produced by `scripts/inventory.py` from the actual source code.",
        "> Any hand edit will be overwritten and will fail the gate.",
        "> This file exists because the previous hand-written ledger drifted until",
        "> 294 of 500 functions were undocumented and every line number was wrong.",
        "",
        f"- Generated: {inv['generated']}",
        f"- Files: {len(inv['files'])} · Lines: {total_lines:,}",
        f"- Functions: {len(inv['functions'])}",
        f"- Declared features: {len(inv['features'])}",
        f"- Routes: {len(inv['routes'])} · Screens: {len(inv['screens'])}",
        f"- Database tables: {len(inv['tables'])} · Policies: {len(inv['policies'])}",
        f"- Edge functions: {len(inv['edge_functions'])}",
        "",
        "## 1. Declared features",
        "",
    ]
    if inv["features"]:
        out += ["| ID | Feature | Declared in |", "|---|---|---|"]
        out += [f"| {f['id']} | {f['title'] or '(no title)'} | `{f['file']}:{f['line']}` |" for f in inv["features"]]
    else:
        out.append("_No features declared yet. Add `// @feature FEAT-0001 <plain-English title>` "
                   "above the code that implements each feature, and a matching `features/FEAT-0001.yml`. "
                   "Until then, 'is anything missing?' cannot be answered mechanically._")

    out += ["", "## 2. Duplicate definitions — EDIT THE ACTIVE ONE", ""]
    if dupes:
        out += ["| Function | ACTIVE (this one runs) | Dead copies |", "|---|---|---|"]
        for name, places in sorted(dupes.items()):
            ordered = sorted(places, key=lambda p: (p["file"], p["line"]))
            active = ordered[-1]
            dead = ", ".join(f"`{p['file']}:{p['line']}`" for p in ordered[:-1])
            out.append(f"| `{name}` | `{active['file']}:{active['line']}` | {dead} |")
    else:
        out.append("None. Every function is defined exactly once.")

    out += ["", "## 3. Routes", ""]
    out += ([f"- `{r}`" for r in inv["routes"]] or ["_none detected_"])
    out += ["", "## 4. Screens", ""]
    out += ([f"- `{s}`" for s in inv["screens"]] or ["_none detected_"])
    out += ["", "## 5. Database", "", "**Tables**", ""]
    out += ([f"- `{t}`" for t in inv["tables"]] or ["_none detected_"])
    out += ["", "**Row-level security policies**", ""]
    out += ([f"- `{p}`" for p in inv["policies"]] or ["_none detected — if this product stores customer data, that is a security hole_"])
    out += ["", "## 6. Server functions (deployed units)", ""]
    out += ([f"- `{e}`" for e in inv["edge_functions"]] or ["_none_"])
    out += ["", "## 7. Every function, by file", "", "| Function | File | Line |", "|---|---|---|"]
    out += [f"| `{f['name']}` | `{f['file']}` | {f['line']} |" for f in inv["functions"]]
    out += ["", "## 8. Files by size", "", "| Lines | File |", "|---|---|"]
    out += [f"| {f['lines']} | `{f['file']}` |" for f in sorted(inv["files"], key=lambda d: -d["lines"])]
    out.append("")
    return "\n".join(out)


def main() -> int:
    cfg = load_config()
    root = Path(cfg["_root"])
    inv = collect(cfg)
    docs = root / "docs"
    docs.mkdir(exist_ok=True)
    (docs / "FEATURE-LEDGER.generated.md").write_text(render(inv), encoding="utf-8")
    (docs / "feature-inventory.json").write_text(json.dumps(inv, indent=1, sort_keys=True), encoding="utf-8")
    print(
        f"Wrote docs/FEATURE-LEDGER.generated.md — "
        f"{len(inv['functions'])} functions, {len(inv['features'])} declared features, "
        f"{len(inv['routes'])} routes, {len(inv['tables'])} tables."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
