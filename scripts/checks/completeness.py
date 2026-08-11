"""
completeness.py — "is anything MISSING?"

THE HOLE THIS FILLS
-------------------
Every other check in this gate proves nothing was *removed*. Not one of them can
tell that something was never *added*. Eight features nobody thought of, and the
whole gate still goes green while the product is inadequate.

That gap is invisible to a forensic audit — a missing feature leaves no trace,
because nobody files a bug about the thing you never built. It is the one failure
mode the original ten-failure analysis was structurally blind to.

WHY THE PREVIOUS ATTEMPT ROTTED
-------------------------------
The Product Engine already had a "Feature-Completeness Matrix". It rotted for the
same reason the hand-written Feature Ledger did: it was a DOCUMENT. Documents are
opinions, and nobody re-reads them.

THE ONE CHANGE THAT MAKES IT SURVIVE
------------------------------------
The research does not end in a report. It ends in a FILE THIS SCRIPT READS:

    docs/FEATURE-MATRIX.csv

    Every row marked `match` or `beat` MUST have a feature file.
    Every row marked `skip` MUST say why.
    At ship time, every agreed feature must be approved by the owner.

So "is anything missing?" becomes computable, exactly the way "is anything
removed?" already is — and the same matrix that starts the project becomes the
checklist scored against the finished build. One artifact, both ends.
"""

from __future__ import annotations

import csv
from pathlib import Path

from ._common import FAIL, PASS, SKIP, WARN, Result

NAME = "completeness"
PLAIN = "Every feature we agreed to build actually exists"

MATRIX = "docs/FEATURE-MATRIX.csv"
BUILD_VERDICTS = {"match", "beat"}


def _cell(v) -> str:
    """A cell arrives as a list when a row has more fields than the header."""
    if isinstance(v, list):
        return "; ".join(str(x).strip() for x in v if str(x).strip())
    return (v or "").strip()


def _read_matrix(root: Path) -> list[dict]:
    p = root / MATRIX
    if not p.exists():
        return []
    # Drop the leading '#' guidance lines, or DictReader treats the first comment
    # as the header and every real row overflows into a list.
    lines = [ln for ln in p.read_text(encoding="utf-8-sig", errors="replace").splitlines()
             if ln.strip() and not ln.lstrip().startswith("#")]
    return [
        {_cell(k).lower(): _cell(v) for k, v in row.items() if k}
        for row in csv.DictReader(lines)
        if any(_cell(v) for v in row.values())
    ]


def _declared_features(root: Path) -> dict[str, str]:
    """FEAT id -> status, read from the feature files."""
    out: dict[str, str] = {}
    fdir = root / "features"
    if not fdir.exists():
        return out
    for f in sorted(fdir.glob("FEAT-*.yml")):
        status = "planned"
        for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.lower().startswith("status:"):
                status = line.split(":", 1)[1].split("#")[0].strip().strip("\"'")
                break
        out[f.stem.upper()] = status
    return out


def run(cfg: dict) -> Result:
    root = Path(cfg["_root"])
    rows = _read_matrix(root)

    if not rows:
        return Result(
            NAME,
            SKIP,
            "No feature matrix yet, so nothing can tell you whether something is MISSING — "
            "only whether something was removed. Run the research stage (build-envision) to "
            "produce docs/FEATURE-MATRIX.csv. Until then this is the biggest blind spot you have.",
        )

    feats = _declared_features(root)
    agreed = [r for r in rows if r.get("verdict", "").lower() in BUILD_VERDICTS]
    skipped = [r for r in rows if r.get("verdict", "").lower() == "skip"]

    missing_feat: list[str] = []   # agreed, but never turned into a feature
    dangling: list[str] = []       # points at a feature file that does not exist
    unapproved: list[str] = []     # built but not yet signed off by the owner
    unexplained_skip: list[str] = []

    for r in agreed:
        label = f"{r.get('id', '?')}  {r.get('feature', '(unnamed)')}"
        fid = r.get("feat_id", "").upper()
        if not fid:
            missing_feat.append(f"{label}  —  agreed to build, but no feature was ever created for it")
        elif fid not in feats:
            dangling.append(f"{label}  —  points at {fid}, which does not exist")
        elif feats[fid] != "approved":
            unapproved.append(f"{label}  —  {fid} is '{feats[fid]}', not approved by you yet")

    for r in skipped:
        if not r.get("why"):
            unexplained_skip.append(
                f"{r.get('id', '?')}  {r.get('feature', '(unnamed)')}  —  skipped with no reason given"
            )

    total = len(agreed)
    done = total - len(missing_feat) - len(dangling) - len(unapproved)

    # Never built at all, or pointing nowhere -> the product is incomplete. FAIL.
    hard = missing_feat + dangling + unexplained_skip
    if hard:
        return Result(
            NAME,
            FAIL,
            f"{len(missing_feat) + len(dangling)} feature(s) you agreed to build do not exist, "
            f"and {len(unexplained_skip)} were skipped without a reason. Every check can be green "
            f"and the product still be missing things — this is the only check that sees that. "
            f"Fix: create the missing feature files, or change the verdict to 'skip' with a reason.",
            hard[:30] + (["", f"({done} of {total} agreed features are approved)"] if total else []),
        )

    # Built but not yet signed off -> not a failure, but not finished either.
    if unapproved:
        return Result(
            NAME,
            WARN,
            f"{done} of {total} agreed features are approved. {len(unapproved)} still waiting on you "
            f"— the product is not complete until every one is ticked.",
            unapproved[:20],
        )

    return Result(
        NAME,
        PASS,
        f"All {total} agreed features exist and are approved by you"
        + (f", {len(skipped)} deliberately skipped with reasons." if skipped else "."),
    )
