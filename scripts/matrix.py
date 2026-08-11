#!/usr/bin/env python3
"""
matrix.py — the feature matrix: written once at the start, scored against the finish.

WHAT IT IS FOR
--------------
The research stage produces one file — `docs/FEATURE-MATRIX.csv` — listing every
feature the research says a product like this needs, where that finding came from,
and whether we're going to match it, beat it, or deliberately skip it.

That single file does two jobs at opposite ends of the project:

  START  it is the agreed scope. You read it and approve it before anything is built.
  FINISH it is the checklist scored against what actually shipped.

One artifact, both ends — so the plan and the final check can never drift apart,
which is exactly how the previous Feature-Completeness Matrix died.

COMMANDS
    python3 scripts/matrix.py new              create a blank matrix
    python3 scripts/matrix.py link             match matrix rows to feature files by title
    python3 scripts/matrix.py score            the scorecard: agreed vs built vs approved
    python3 scripts/matrix.py score --html     the same, as a page you can read on your phone
"""

from __future__ import annotations

import csv
import html
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from checks._common import load_config, read  # noqa: E402

MATRIX = "docs/FEATURE-MATRIX.csv"
COLUMNS = [
    "id",          # FM-001
    "feature",     # plain English, the way the owner would say it
    "area",        # contacts / pipeline / billing ...
    "rivals_have", # who already has it, semicolon separated
    "verdict",     # match | beat | skip
    "why",         # required for skip; the reason we're not doing it
    "source",      # research | complaint | interview | journey
    "feat_id",     # FEAT-0007 once it becomes a real feature
]

HEADER_NOTE = [
    "# FEATURE MATRIX — the agreed scope, and the final checklist. Same file, both ends.",
    "# verdict: match = build it · beat = build it better than they do · skip = deliberately not",
    "# EVERY match/beat row must end up with a feat_id, or the build goes red.",
    "# EVERY skip row must have a why. 'We didn't get to it' is not a why.",
]


def _clean(v) -> str:
    """A cell may arrive as a list when a row has more fields than the header."""
    if isinstance(v, list):
        return "; ".join(str(x).strip() for x in v if str(x).strip())
    return (v or "").strip()


def _rows_without_comments(p: Path):
    """Drop the leading '#' guidance lines so the real header is the header.

    Without this, csv.DictReader treats the first comment line as the column
    names, every data row overflows into the restkey, and cells arrive as lists.
    """
    return [ln for ln in p.read_text(encoding="utf-8-sig").splitlines()
            if ln.strip() and not ln.lstrip().startswith("#")]


def load(root: Path) -> list[dict]:
    p = root / MATRIX
    if not p.exists():
        return []
    return [
        {_clean(k).lower(): _clean(v) for k, v in r.items() if k}
        for r in csv.DictReader(_rows_without_comments(p))
        if any(_clean(v) for v in r.values())
    ]


def save(root: Path, rows: list[dict]) -> None:
    p = root / MATRIX
    p.parent.mkdir(exist_ok=True)
    with p.open("w", encoding="utf-8", newline="") as fh:
        for line in HEADER_NOTE:
            fh.write(line + "\n")
        w = csv.DictWriter(fh, fieldnames=COLUMNS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in COLUMNS})


def features(root: Path) -> dict[str, dict]:
    out = {}
    fdir = root / "features"
    if not fdir.exists():
        return out
    for f in sorted(fdir.glob("FEAT-*.yml")):
        text = read(f)
        def scalar(k, d=""):
            m = re.search(rf"^{k}:\s*(.*)$", text, re.M)
            if not m:
                return d
            v = re.sub(r"\s+#\s.*$", "", m.group(1)).strip()
            return v[1:-1] if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'" else v
        out[f.stem.upper()] = {"title": scalar("title"), "status": scalar("status", "planned")}
    return out


def cmd_new(root: Path) -> int:
    if (root / MATRIX).exists():
        print(f"{MATRIX} already exists. Delete it first if you really mean to start over.")
        return 1
    save(root, [{
        "id": "FM-001", "feature": "Example — replace this row",
        "area": "", "rivals_have": "", "verdict": "match", "why": "",
        "source": "research", "feat_id": "",
    }])
    print(f"Created {MATRIX}. Fill it from the research, then run: python3 scripts/matrix.py link")
    return 0


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def cmd_link(root: Path) -> int:
    """Fill in feat_id by matching matrix titles to feature titles."""
    rows, feats = load(root), features(root)
    if not rows:
        print(f"No {MATRIX} yet. Run: python3 scripts/matrix.py new")
        return 1

    by_title = {_norm(v["title"]): k for k, v in feats.items()}
    linked = 0
    for r in rows:
        if r.get("feat_id") or r.get("verdict", "").lower() == "skip":
            continue
        key = _norm(r.get("feature", ""))
        hit = by_title.get(key)
        if not hit:  # fall back to a containment match
            hit = next((fid for t, fid in by_title.items()
                        if key and (key in t or t in key)), None)
        if hit:
            r["feat_id"] = hit
            linked += 1

    save(root, rows)
    print(f"Linked {linked} matrix row(s) to feature files.")
    unlinked = [r for r in rows
                if r.get("verdict", "").lower() in ("match", "beat") and not r.get("feat_id")]
    if unlinked:
        print(f"\n{len(unlinked)} agreed feature(s) still have no feature file — the gate will be red:")
        for r in unlinked[:15]:
            print(f"   {r.get('id')}  {r.get('feature')}")
        print("\nEither create a feature for each, or change the verdict to 'skip' and say why.")
    return 0


def cmd_score(root: Path, as_html: bool = False) -> int:
    rows, feats = load(root), features(root)
    if not rows:
        print(f"No {MATRIX} yet — so nothing can tell you whether anything is MISSING.")
        return 1

    agreed = [r for r in rows if r.get("verdict", "").lower() in ("match", "beat")]
    skipped = [r for r in rows if r.get("verdict", "").lower() == "skip"]

    buckets = {"approved": [], "built": [], "building": [], "not started": [], "MISSING": []}
    for r in agreed:
        fid = r.get("feat_id", "").upper()
        if not fid or fid not in feats:
            buckets["MISSING"].append(r)
        else:
            st = feats[fid]["status"]
            buckets.setdefault(st if st in buckets else "not started", []).append(r)

    total = len(agreed)
    done = len(buckets["approved"])
    pct = int(100 * done / total) if total else 0

    W = 72
    print("\n" + "=" * W)
    print("  COMPLETENESS SCORECARD — the research checklist vs what actually shipped")
    print("=" * W)
    bar = int(40 * done / total) if total else 0
    print(f"  [{'#' * bar}{'.' * (40 - bar)}]  {done}/{total} approved ({pct}%)")
    print()
    for name in ("MISSING", "not started", "building", "built", "approved"):
        rs = buckets[name]
        if not rs:
            continue
        label = "NEVER BUILT — nothing else can see this" if name == "MISSING" else name.upper()
        print(f"  {label}  ({len(rs)})")
        for r in rs[:20]:
            print(f"     {r.get('id'):<7} {r.get('feature','')[:56]}")
        print()
    if skipped:
        print(f"  DELIBERATELY SKIPPED  ({len(skipped)})")
        for r in skipped[:15]:
            print(f"     {r.get('id'):<7} {r.get('feature','')[:40]} — {r.get('why','(no reason!)')[:40]}")
        print()
    print("=" * W + "\n")

    if as_html:
        out = root / "completeness.html"
        parts = ["""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Completeness</title><style>
:root{--ink:#0E2230;--mint:#54E5A0;--em:#00845F;--red:#D9534F;--bg:#f6f8f8}
body{margin:0;background:var(--bg);color:var(--ink);padding:16px;
font:16px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
h1{font-size:20px;margin:0 0 2px}.s{color:#5a6b78;font-size:14px;margin:0 0 14px}
.bar{height:10px;border-radius:6px;background:#dde5e8;overflow:hidden;margin:0 0 18px}
.bar i{display:block;height:100%;background:var(--mint)}
.g{font:600 11px system-ui;letter-spacing:.1em;text-transform:uppercase;color:#7b8b96;margin:20px 0 7px}
.r{background:#fff;border-radius:10px;padding:11px 13px;margin:0 0 7px;border-left:4px solid #dde5e8;
box-shadow:0 1px 3px rgba(14,34,48,.08)}
.r.MISSING{border-left-color:var(--red);background:#fdf3f3}
.r.approved{border-left-color:var(--em)}
.id{font:600 11px ui-monospace,monospace;color:var(--em)}
.w{font-size:13px;color:#5a6b78}</style></head><body>""",
            f"<h1>Completeness</h1><p class='s'>{done} of {total} agreed features approved by you.</p>",
            f"<div class='bar'><i style='width:{pct}%'></i></div>"]
        for name in ("MISSING", "not started", "building", "built", "approved"):
            rs = buckets[name]
            if not rs:
                continue
            title = "Never built" if name == "MISSING" else name.title()
            parts.append(f"<div class='g'>{title} ({len(rs)})</div>")
            for r in rs:
                parts.append(f"<div class='r {name}'><span class='id'>{html.escape(r.get('id',''))}</span> "
                             f"{html.escape(r.get('feature',''))}</div>")
        if skipped:
            parts.append(f"<div class='g'>Deliberately skipped ({len(skipped)})</div>")
            for r in skipped:
                parts.append(f"<div class='r'><span class='id'>{html.escape(r.get('id',''))}</span> "
                             f"{html.escape(r.get('feature',''))}"
                             f"<div class='w'>{html.escape(r.get('why','(no reason given)'))}</div></div>")
        parts.append("</body></html>")
        out.write_text("\n".join(parts), encoding="utf-8")
        print(f"  Also written to completeness.html — open it on your phone.\n")

    return 1 if buckets["MISSING"] else 0


def main() -> int:
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 2
    root = Path(load_config()["_root"])
    cmd = args[0]
    if cmd == "new":
        return cmd_new(root)
    if cmd == "link":
        return cmd_link(root)
    if cmd == "score":
        return cmd_score(root, "--html" in args)
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
