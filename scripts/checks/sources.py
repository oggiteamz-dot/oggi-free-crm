"""
sources.py — "which document do I actually believe?"

THE FAILURE THIS PREVENTS
-------------------------
The MASTER FEATURE LEDGER said the Fable stack was "✅ Deployed."
The MASTER BACKLOG, four days later, said "Blocked on Supabase keys."
Both claimed to be authoritative. Neither carried a marker saying which was
current, so both stayed in circulation and both got quoted in later decisions.

Pricing was written five different ways in six days, and two build sessions were
run against two different versions of it.

THE MECHANISM
-------------
Every document that asserts facts carries three lines of front matter:

    ---
    topic: pricing
    status: current          # or: superseded
    superseded_by: [C] Pricing (LOCKED Jul 27).md
    ---

This check asserts: AT MOST ONE document marked `current` per topic, and every
`superseded` document names the file that replaced it. That single rule ends the
"two sources of truth" class of failure permanently.
"""

from __future__ import annotations

import os
import re
from collections import defaultdict
from pathlib import Path

from ._common import FAIL, PASS, SKIP, Result, is_exempt, rel

NAME = "sources-of-truth"
PLAIN = "Exactly one 'current' document per topic — no two docs disagreeing"

FRONT = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.S)


def _front_matter(text: str) -> dict[str, str]:
    m = FRONT.match(text)
    if not m:
        return {}
    out = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            out[k.strip().lower()] = v.strip().strip("\"'")
    return out


def run(cfg: dict) -> Result:
    root = Path(cfg["_root"])
    ignore = set(cfg["ignore_dirs"])
    by_topic: dict[str, list[tuple[str, str]]] = defaultdict(list)
    orphan_supersedes: list[str] = []
    scanned = 0

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in ignore and not d.startswith(".")]
        for fn in filenames:
            if not fn.lower().endswith(".md"):
                continue
            p = Path(dirpath) / fn
            # Without this, copying templates/SPEC.md to SPEC.md — which the
            # skills explicitly instruct — instantly reports two documents
            # claiming to be the current spec. A false alarm on the documented
            # happy path is the worst possible first impression.
            if is_exempt(cfg, p):
                continue
            try:
                head = p.read_text(encoding="utf-8", errors="replace")[:2000]
            except OSError:
                continue
            fm = _front_matter(head)
            topic = fm.get("topic")
            if not topic:
                continue
            scanned += 1
            status = fm.get("status", "current").lower()
            by_topic[topic].append((status, rel(cfg, p)))
            if status == "superseded" and not fm.get("superseded_by"):
                orphan_supersedes.append(
                    f"{rel(cfg, p)} is marked superseded but does not say what replaced it"
                )

    if scanned == 0:
        return Result(
            NAME,
            SKIP,
            "No documents carry a topic: marker yet. Add topic/status front matter to any "
            "document that states facts (pricing, architecture, status) so two versions can "
            "never both look authoritative.",
        )

    problems = list(orphan_supersedes)
    for topic, entries in sorted(by_topic.items()):
        currents = [f for s, f in entries if s == "current"]
        if len(currents) > 1:
            problems.append(
                f"topic '{topic}' has {len(currents)} documents claiming to be current: "
                + " | ".join(currents)
            )
        if not currents:
            problems.append(f"topic '{topic}' has NO current document — all copies are superseded")

    if problems:
        return Result(
            NAME,
            FAIL,
            f"{len(problems)} topic(s) have conflicting sources of truth. "
            f"Fix: pick one file per topic, mark it status: current, and mark every other "
            f"copy status: superseded with superseded_by: <the winning file>.",
            problems[:30],
        )

    return Result(NAME, PASS, f"{len(by_topic)} topic(s), exactly one current document each.")
