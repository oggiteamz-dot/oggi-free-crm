#!/usr/bin/env python3
"""
guard_deploy.py — the gate cannot be walked around.

THE INSIGHT THIS IMPLEMENTS
---------------------------
From the adversarial review: "make it structurally impossible to call something
done without a machine having exercised the real, deployed product." The way to
do that is not a rule asking someone to run the checks. It is to make the deploy
command REFUSE to run when they have not.

So the path of least resistance goes THROUGH the gate rather than around it.

FOUR CONDITIONS, ALL REQUIRED
-----------------------------
1. The gate passed.
2. It ran EVERY check — not a subset. (`check.py --only secrets` used to write a
   "passed" stamp, so one flag defeated the whole gate.)
3. It passed on THIS EXACT version of the code — not an earlier one.
4. It passed recently, so yesterday's green cannot wave through today's changes.

WHAT COUNTS AS "UNCOMMITTED"
----------------------------
The tool's OWN generated files are ignored. An earlier version counted them, which
deadlocked the deploy permanently: running the gate created an untracked stamp
file -> "uncommitted changes" -> commit it -> the commit changes the SHA ->
"checks passed on a different version" -> run the gate again -> stamp modified ->
uncommitted again. Forever. A guard that can never be satisfied is a guard that
gets bypassed, which is worse than no guard at all.

Exit 0 = deploy may proceed. Exit 1 = blocked, with the reason and the fix.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from checks._common import load_config, sh  # noqa: E402

MAX_AGE_SECONDS = 15 * 60

# Files this toolkit generates. They are noise in a dirtiness check, and counting
# them made the deploy permanently unreachable.
GENERATED = (
    ".oggi-gate-status.json",
    "proof-cards.html",
    "content-import.sql",
    "content-replace.md",
    "docs/FEATURE-LEDGER.generated.md",
    "docs/feature-inventory.json",
    "docs/.inventory-baseline.json",
    "evidence/",
    "_backups/",
)


def block(reason: str, fix: str) -> int:
    print()
    print("=" * 68)
    print("  DEPLOY BLOCKED")
    print("=" * 68)
    print(f"  {reason}")
    print()
    print(f"  Fix: {fix}")
    print("=" * 68)
    print()
    return 1


def real_changes(root: Path) -> list[str]:
    """Uncommitted changes to files a human actually wrote."""
    code, out = sh(f"git -C '{root}' status --porcelain", timeout=15)
    if code != 0:
        return []
    changed = []
    for line in out.splitlines():
        path = line[3:].strip().strip('"')
        if any(path == g or path.startswith(g) for g in GENERATED):
            continue
        changed.append(path)
    return changed


def main() -> int:
    cfg = load_config()
    root = Path(cfg["_root"])
    stamp = root / ".oggi-gate-status.json"

    if not stamp.exists():
        return block(
            "The checks have never been run on this project.",
            "Run `just check` first. It takes under a minute.",
        )

    try:
        data = json.loads(stamp.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return block("The gate status file is unreadable.", "Run `just check` again.")

    if not data.get("passed"):
        failed = ", ".join(data.get("failed_checks", [])) or "unknown"
        return block(
            f"The last time the checks ran, these FAILED: {failed}.",
            "Run `just check`, fix what it names, and run it again until it is green.",
        )

    if not data.get("full_run"):
        ran = ", ".join(data.get("checks_run", [])) or "some"
        return block(
            f"The last run only checked part of the product ({ran}), not all of it.",
            "Run `just check` with no filters, so every check runs.",
        )

    code, head = sh(f"git -C '{root}' rev-parse HEAD", timeout=10)
    head = head.strip() if code == 0 else "no-git"
    if data.get("sha") != head:
        return block(
            "The checks passed — but on a DIFFERENT version of the code than the one "
            "you are about to deploy. Something changed since.",
            "Run `just check` again on the current code.",
        )

    dirty = real_changes(root)
    if dirty:
        listed = ", ".join(dirty[:4]) + (" …" if len(dirty) > 4 else "")
        return block(
            f"There are {len(dirty)} unsaved change(s) ({listed}). What you are about to "
            "put live is not what was checked, and there would be no record of what shipped.",
            "Save them to the project history (Claude does this — ask it to commit), "
            "then run `just check`, then deploy.",
        )

    age = int(time.time()) - int(data.get("at", 0))
    if age > MAX_AGE_SECONDS:
        return block(
            f"The checks last passed {age // 60} minutes ago. A green result that old "
            "does not describe the code as it stands now.",
            "Run `just check` again (under a minute) and deploy immediately after.",
        )

    print(f"  Gate: PASSED on {head[:12]}, {age // 60}m ago, all checks. Deploy allowed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
