#!/usr/bin/env python3
"""
check.py — THE GATE. One command. One colour. Under 60 seconds.

WHAT THIS IS
------------
Everything the owner needs to know about whether the product is safe to ship,
reduced to green or red plus a plain-English sentence naming the file and the fix.

He never reads a diff. He reads this table.

THE THREE DESIGN CONSTRAINTS (from the adversarial review — these are not
negotiable, because violating any one of them gets the gate disabled at 11pm on
a client deadline and never re-enabled):

  1. UNDER 60 SECONDS. A six-minute gate gets bypassed on night three.
  2. ZERO FALSE ALARMS. One bogus block teaches the owner the gate lies, and he
     will route around it forever. Better to catch six failure classes with
     perfect precision than ten with noise.
  3. EVERY FAILURE NAMES THE FILE, THE LINE AND THE FIX IN PLAIN ENGLISH.
     "Exit code 1" is a gate that gets deleted.

ADOPTING AN EXISTING PRODUCT
----------------------------
Running this on a product that already exists will be red. That is the point —
it is describing problems that were already there. But a gate that blocks every
deploy on day one gets uninstalled on day one, so:

    python3 scripts/check.py --adopt

records everything currently wrong as a dated, accepted backlog. After that, only
NEW problems fail the build. The old ones stay visible in every report, listed as
pre-existing, so they are never quietly forgotten — just not blocking.

USAGE
    python3 scripts/check.py             # run everything
    python3 scripts/check.py --adopt     # accept today's problems as a backlog
    python3 scripts/check.py --only placeholders,persistence
    python3 scripts/check.py --json      # machine output for CI

EXIT CODES
    0  everything passed (warnings and pre-existing findings allowed)
    1  at least one NEW problem — do not ship
    2  the gate itself could not run (config broken, files missing)
"""

from __future__ import annotations

import importlib
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from checks._common import FAIL, PASS, SKIP, WARN, Result, load_config, sh  # noqa: E402

# Order matters: cheapest and most damaging first, so a failure surfaces fast.
CHECKS = [
    "completeness",     # is anything MISSING? the only check that sees an absence
    "wip",              # am I running ahead of you? one feature at a time
    "placeholders",     # a fake value reaching a customer
    "persistence",      # data that vanishes on reload / never reaches another device
    "silent_catch",     # failures nobody is ever told about
    "orphans",          # buttons wired to nothing, dead links
    "xss",              # customer input becoming code on someone else's screen
    "boundaries",       # one feature's code reaching into another's
    "secrets",          # credentials sitting in the code
    "duplicates",       # editing a dead copy that changes nothing
    "sources",          # two documents both claiming to be the truth
    "inventory_fresh",  # the ledger no longer matching the code
    "filesize",         # files too big to edit safely
]

ADOPTED_FILE = ".oggi-adopted.json"
STAMP_FILE = ".oggi-gate-status.json"


# ---------------------------------------------------------------------------
# Running
# ---------------------------------------------------------------------------

def run_all(cfg: dict, only: list[str] | None = None) -> list[Result]:
    results: list[Result] = []
    for name in CHECKS:
        if only and name not in only:
            continue
        try:
            mod = importlib.import_module(f"checks.{name}")
            results.append(mod.run(cfg))
        except Exception as exc:  # a broken check must be loud, never silent
            results.append(
                Result(
                    name,
                    FAIL,
                    f"The '{name}' check could not run: {type(exc).__name__}: {exc}. "
                    f"A check that cannot run is not a check that passed.",
                )
            )
    return results


# ---------------------------------------------------------------------------
# Adoption baseline — pre-existing problems stay visible but stop blocking
# ---------------------------------------------------------------------------

def load_adopted(root: Path) -> dict:
    p = root / ADOPTED_FILE
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def apply_adoption(results: list[Result], adopted: dict) -> tuple[list[Result], int]:
    """Downgrade findings that were already present when the toolkit was adopted."""
    known = adopted.get("findings", {})
    carried = 0
    out = []
    for r in results:
        if r.status != FAIL or r.name not in known:
            out.append(r)
            continue
        already = set(known[r.name])
        fresh = [d for d in r.details if d not in already]
        carried += len(r.details) - len(fresh)
        if fresh:
            # Name a NEW finding, never the first of the whole list. Pointing at a
            # pre-existing line while saying "new" sends the fix to the wrong place
            # and teaches the owner that the message cannot be trusted.
            first = fresh[0].splitlines()[0].strip()
            older = len(r.details) - len(fresh)
            r.details = fresh + ([f"(+ {older} pre-existing, accepted {adopted.get('at', '')})"] if older else [])
            r.plain = (
                f"{len(fresh)} NEW problem(s) since you adopted the checks — "
                f"this one is new: {first}"
            )
            out.append(r)
        else:
            out.append(Result(
                r.name,
                WARN,
                f"No new problems. {len(r.details)} pre-existing issue(s) from before "
                f"{adopted.get('at', 'adoption')} — on the backlog, not blocking.",
                r.details[:10],
            ))
    return out, carried


def write_adoption(root: Path, results: list[Result]) -> None:
    findings = {r.name: r.details for r in results if r.status == FAIL}
    total = sum(len(v) for v in findings.values())
    (root / ADOPTED_FILE).write_text(
        json.dumps(
            {
                "at": time.strftime("%Y-%m-%d"),
                "note": "Problems that already existed when this product adopted the "
                        "checks. They stay visible in every report but do not block a "
                        "deploy. Anything NEW does. Delete an entry once it is fixed.",
                "findings": findings,
            },
            indent=1,
        ),
        encoding="utf-8",
    )
    print()
    print("=" * 72)
    print("  ADOPTED")
    print("=" * 72)
    print(f"  {total} existing problem(s) across {len(findings)} check(s) recorded as a")
    print("  backlog in .oggi-adopted.json.")
    print()
    print("  From now on:")
    print("    * these stay listed in every report, so they are not forgotten")
    print("    * they do NOT block you from shipping")
    print("    * anything NEW does block, which is the whole point")
    print()
    print("  Ask Claude to work through the backlog a few at a time when there is room.")
    print("=" * 72)
    print()


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

ICON = {PASS: "PASS", FAIL: "FAIL", WARN: "WARN", SKIP: "SKIP"}


def print_report(results: list[Result], seconds: float, carried: int) -> None:
    width = 72
    print()
    print("=" * width)
    print("  OGGI BUILD GATE")
    print("=" * width)

    label_w = max((len(r.name) for r in results), default=10) + 2
    for r in results:
        print(f"  [{ICON[r.status]}]  {r.name:<{label_w}} {r.plain}")

    failures = [r for r in results if r.failed]
    warnings = [r for r in results if r.status == WARN]
    skipped = [r for r in results if r.status == SKIP]

    if failures or warnings:
        print()
        print("-" * width)
        for r in failures + warnings:
            if not r.details:
                continue
            print(f"\n  {r.status} — {r.name}")
            for d in r.details:
                for line in str(d).splitlines():
                    print(f"      {line}")
        print("-" * width)

    passed = len(results) - len(failures) - len(warnings) - len(skipped)
    print()
    print(f"  {passed} passed · {len(warnings)} warning · {len(skipped)} skipped · "
          f"{len(failures)} FAILED   ({seconds:.1f}s)")
    if carried:
        print(f"  {carried} pre-existing problem(s) on the backlog — listed, not blocking.")
    print()

    if skipped:
        print("  NOTE — a SKIPPED check is protecting you from nothing. Ask Claude to")
        print("  finish setting it up; the persistence one especially, because it is the")
        print("  check for the bug that has cost you the most.")
        print()

    if failures:
        print("  RESULT: RED — do not ship.")
        print()
        print("  What to do: copy the FAIL lines above and paste them to Claude with")
        print("  \"fix these\". Each one names the file and the fix already.")
        print()
        print("  If this is the first run on a product that already exists, most of these")
        print("  were already there. Run `just adopt` to put them on a backlog instead.")
    else:
        print("  RESULT: GREEN — the mechanical checks pass.")
        print()
        print("  This does NOT mean the product works. It means nothing is obviously")
        print("  broken in the ways that have burned you before. Working is proven by")
        print("  the Proof Cards (you click) and by `just verify-live` (the live URL).")
    print("=" * width)
    print()


# ---------------------------------------------------------------------------

def main() -> int:
    args = sys.argv[1:]

    only = None
    if "--only" in args:
        i = args.index("--only") + 1
        if i >= len(args) or args[i].startswith("--"):
            print("--only needs a list, e.g.  --only placeholders,persistence")
            print(f"Available: {', '.join(CHECKS)}")
            return 2
        only = [c.strip() for c in args[i].split(",") if c.strip()]
        unknown = [c for c in only if c not in CHECKS]
        if unknown:
            print(f"Unknown check(s): {', '.join(unknown)}")
            print(f"Available: {', '.join(CHECKS)}")
            return 2

    started = time.time()
    try:
        cfg = load_config()
    except SystemExit:
        return 2

    root = Path(cfg["_root"])
    results = run_all(cfg, only)
    elapsed = time.time() - started

    if "--adopt" in args:
        write_adoption(root, results)
        return 0

    carried = 0
    adopted = load_adopted(root)
    if adopted:
        results, carried = apply_adoption(results, adopted)

    if "--json" in args:
        print(json.dumps(
            [{"name": r.name, "status": r.status, "plain": r.plain, "details": r.details}
             for r in results],
            indent=1,
        ))
    else:
        print_report(results, elapsed, carried)

    failed = any(r.failed for r in results)

    # Record the result against the current commit. The deploy script refuses to
    # run unless this stamp exists, is recent, is for this exact commit, and
    # covers EVERY check — so a partial run cannot wave a deploy through.
    try:
        code, sha = sh(f"git -C '{root}' rev-parse HEAD", timeout=10)
        (root / STAMP_FILE).write_text(json.dumps({
            "passed": not failed,
            "full_run": only is None,
            "checks_run": [r.name for r in results],
            "sha": sha.strip() if code == 0 else "no-git",
            "at": int(time.time()),
            "failed_checks": [r.name for r in results if r.failed],
            "pre_existing_carried": carried,
        }, indent=1), encoding="utf-8")
    except OSError:
        pass

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
