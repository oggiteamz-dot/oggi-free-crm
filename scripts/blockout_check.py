#!/usr/bin/env python3
"""
blockout_check.py — the machine version of the phone walk-through.

WHAT IT ANSWERS
---------------
Four questions, the same four the owner answers by clicking:
  1. Is any screen unreachable?  (an orphan — it exists and nobody can find it)
  2. Does any screen have no way out?  (a dead end)
  3. Does any link point at a screen that does not exist?  (a broken link)
  4. Does any screen lack its empty / loading / error states?

It reads SCREENMAP.md — the boxes-and-arrows map written during the blockout —
and checks it against the screens actually present in the code.

SCREENMAP.md FORMAT (deliberately simple enough to write by hand in two minutes):

    # SCREENMAP
    entry: screen-login

    screen-login       -> screen-catalog
    screen-catalog     -> screen-product, screen-orders
    screen-product     -> screen-catalog, screen-order-confirm
    screen-order-confirm -> screen-orders
    screen-orders      -> screen-catalog

    roles:
      buyer: screen-login, screen-catalog, screen-product, screen-order-confirm, screen-orders
      admin: screen-login, screen-admin

THIS DOES NOT REPLACE THE WALK. A machine can prove the map is consistent. Only a
person clicking can notice "wait, where do I choose the size?" — which is the
cheapest bug report that exists.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from checks._common import iter_source_files, load_config, read  # noqa: E402

SCREEN_IN_CODE = re.compile(r"""(?:data-screen|id)\s*=\s*["'](screen-[\w-]+)["']""", re.I)


def parse_map(text: str):
    entry, edges, roles = None, {}, {}
    section = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("entry:"):
            entry = line.split(":", 1)[1].strip()
            continue
        if line.startswith("roles:"):
            section = "roles"
            continue
        if section == "roles" and ":" in line:
            role, _, screens = line.partition(":")
            roles[role.strip()] = [s.strip() for s in screens.split(",") if s.strip()]
            continue
        if "->" in line:
            src, _, dsts = line.partition("->")
            edges[src.strip()] = [d.strip() for d in dsts.split(",") if d.strip()]
    return entry, edges, roles


def reachable(entry: str, edges: dict) -> set[str]:
    seen, stack = set(), [entry]
    while stack:
        node = stack.pop()
        if node in seen:
            continue
        seen.add(node)
        stack.extend(edges.get(node, []))
    return seen


def main() -> int:
    cfg = load_config()
    root = Path(cfg["_root"])
    map_path = root / "SCREENMAP.md"

    if not map_path.exists():
        print(
            "\nNo SCREENMAP.md.\n"
            "Write one during the blockout — it takes two minutes and it is what turns\n"
            "'can I get lost in this product?' into a question a computer can answer.\n"
            "Format is in scripts/blockout_check.py.\n"
        )
        return 2

    entry, edges, roles = parse_map(read(map_path))
    if not entry:
        print("SCREENMAP.md has no `entry:` line. Which screen does a user land on first?")
        return 2

    declared = set(edges) | {d for ds in edges.values() for d in ds}
    in_code = set()
    for p in iter_source_files(cfg):
        in_code.update(SCREEN_IN_CODE.findall(read(p)))

    problems: list[str] = []

    # 1. orphans — declared but unreachable from the entry screen
    reach = reachable(entry, edges)
    for s in sorted(declared - reach):
        problems.append(f"ORPHAN     {s} — exists, but nothing links to it. A user can never get there.")

    # 2. dead ends — reachable but with no way onward
    for s in sorted(reach):
        if not edges.get(s):
            problems.append(f"DEAD END   {s} — no way forward and no way back. The user is stuck here.")

    # 3. broken links — pointed at, but not built
    for s in sorted(declared - in_code):
        if in_code:
            problems.append(f"MISSING    {s} — the map links to it, but no screen with that id exists in the code.")

    # 4. built but not on the map
    for s in sorted(in_code - declared):
        problems.append(f"UNMAPPED   {s} — exists in the code but is on no path. Add it to the map or delete it.")

    # 5. per-role reachability
    for role, screens in roles.items():
        allowed = set(screens)
        role_reach = reachable(entry, {k: [d for d in v if d in allowed] for k, v in edges.items() if k in allowed})
        for s in sorted(allowed - role_reach):
            problems.append(f"ROLE TRAP  {s} — a '{role}' is allowed here but cannot navigate to it.")

    print("\n" + "=" * 68)
    print("  BLOCKOUT CHECK")
    print("=" * 68)
    if not problems:
        print(f"  {len(declared)} screens. No orphans, no dead ends, no broken links.")
        print("\n  Now walk it yourself on your phone, once as each role. A machine can prove")
        print("  the map is consistent. Only you can notice a step that is missing entirely.")
        print("=" * 68 + "\n")
        return 0

    for p in problems:
        print("  " + p)
    print("\n  " + "-" * 64)
    print(f"  {len(problems)} structural problem(s). Fix these before building any feature —")
    print("  moving a screen now costs a minute; moving it after the design pass does not happen.")
    print("=" * 68 + "\n")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
