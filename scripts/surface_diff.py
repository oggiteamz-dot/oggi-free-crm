#!/usr/bin/env python3
"""
surface_diff.py — "did this change quietly remove something?"

THE FAILURE THIS PREVENTS
-------------------------
This is the #1 recurring pain in the estate and the reason the Feature Ledger was
invented in the first place: an update rebuilds what the AI remembers and silently
drops the rest. The previous defence was a rule ("edit in place, never regenerate
from memory") plus a hand-maintained before/after count. Rules are requests. This
is a check.

HOW IT WORKS
------------
1. Read the previous inventory (from git HEAD, or from a saved baseline file).
2. Read the current inventory (freshly generated).
3. Compute what was ADDED, what was CHANGED, and — the only one that blocks —
   what was REMOVED.
4. REMOVED lines fail the build, UNLESS the commit message carries an explicit
   approval token naming the removed symbol:

       REMOVES: addToCart — approved by Hadi 2026-08-08

   The token is deliberately awkward to type. Removal should be a decision, not
   an accident.

WHAT THE OWNER SEES
-------------------
A short list titled "things that disappeared in this change". Normally empty.
That list is the entire interface — no diff reading required.

USAGE
    python3 scripts/surface_diff.py                # compare against git HEAD
    python3 scripts/surface_diff.py --save-baseline # accept current as the baseline
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from checks._common import load_config, sh  # noqa: E402

INVENTORY = "docs/feature-inventory.json"
BASELINE = "docs/.inventory-baseline.json"
#
# The approval line must be able to name things that CONTAIN hyphens and spaces:
#   REMOVES: send-otp — approved by Hadi 2026-08-08
#   REMOVES: GET /catalog — approved by Hadi 2026-08-08
# An earlier version excluded hyphens, which made every real edge-function name
# permanently unapprovable — a gate that cannot be satisfied is a gate that gets
# deleted. Everything up to the em-dash (or a double hyphen, or end of line) is
# the symbol name.
APPROVAL = re.compile(r"REMOVES:\s*(.+?)\s*(?:—|--|–|$)", re.I | re.M)

# The parts of the inventory whose disappearance is a real loss.
TRACKED = ["functions", "features", "routes", "screens", "tables", "policies", "edge_functions"]


def _keys(inv: dict, section: str) -> set[str]:
    """Reduce a section to a comparable set of identity strings."""
    items = inv.get(section, [])
    if section == "functions":
        return {i["name"] for i in items}
    if section == "features":
        return {i["id"] for i in items}
    return set(items)


def _previous(root: Path) -> dict | None:
    """Prefer git HEAD (true history); fall back to a saved baseline file."""
    code, out = sh(f"git -C '{root}' show HEAD:{INVENTORY}", timeout=20)
    if code == 0 and out.strip().startswith("{"):
        try:
            return json.loads(out)
        except json.JSONDecodeError:
            pass
    bp = root / BASELINE
    if bp.exists():
        try:
            return json.loads(bp.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None
    return None


def _commit_message(root: Path) -> str:
    """Everything that could carry the approval token: staged message + last commit."""
    parts = []
    msg_file = root / ".git" / "COMMIT_EDITMSG"
    if msg_file.exists():
        parts.append(msg_file.read_text(encoding="utf-8", errors="replace"))
    code, out = sh(f"git -C '{root}' log -1 --pretty=%B", timeout=20)
    if code == 0:
        parts.append(out)
    approvals_file = root / "REMOVALS-APPROVED.md"
    if approvals_file.exists():
        parts.append(approvals_file.read_text(encoding="utf-8", errors="replace"))
    return "\n".join(parts)


def main() -> int:
    cfg = load_config()
    root = Path(cfg["_root"])
    cur_path = root / INVENTORY

    if not cur_path.exists():
        print("No inventory yet. Run: python3 scripts/inventory.py")
        return 2
    current = json.loads(cur_path.read_text(encoding="utf-8"))

    if "--save-baseline" in sys.argv:
        (root / BASELINE).write_text(json.dumps(current, indent=1, sort_keys=True), encoding="utf-8")
        print(f"Baseline saved. Future changes will be compared against this state.")
        return 0

    previous = _previous(root)
    if previous is None:
        print("No previous inventory found — nothing to compare against yet.")
        print("This is normal on the very first run. Run with --save-baseline to set the starting point.")
        return 0

    approved = {a.strip().lower() for a in APPROVAL.findall(_commit_message(root)) if a.strip()}
    removed_all: list[str] = []
    added_all: list[str] = []

    for section in TRACKED:
        before, after = _keys(previous, section), _keys(current, section)
        for gone in sorted(before - after):
            if gone.lower() in approved:
                continue
            removed_all.append(f"{section[:-1] if section.endswith('s') else section}: {gone}")
        for new in sorted(after - before):
            added_all.append(f"{section}: {new}")

    print("=" * 68)
    print("WHAT CHANGED IN THIS EDIT")
    print("=" * 68)
    print(f"  Added:   {len(added_all)}")
    print(f"  Removed: {len(removed_all)}")
    print()

    if added_all:
        print("New things:")
        for a in added_all[:40]:
            print(f"  + {a}")
        if len(added_all) > 40:
            print(f"  … and {len(added_all) - 40} more")
        print()

    if not removed_all:
        print("THINGS THAT DISAPPEARED IN THIS CHANGE: none.")
        print("Nothing was removed. This is what a safe edit looks like.")
        return 0

    print("THINGS THAT DISAPPEARED IN THIS CHANGE:")
    for r in removed_all:
        print(f"  - {r}")
    print()
    print("-" * 68)
    print("This edit removed the things above. If that was NOT intended, the edit")
    print("has silently destroyed working features — stop and restore them.")
    print()
    print("If every removal above was deliberate and approved, add one line per")
    print("removed item to REMOVALS-APPROVED.md (or the commit message):")
    print()
    for r in removed_all[:5]:
        name = r.split(": ", 1)[-1]
        print(f"    REMOVES: {name} — approved by <name> <date> — reason")
    print("-" * 68)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
