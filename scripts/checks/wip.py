"""
wip.py — "am I running ahead of you?"

THE GAP THIS FILLS
------------------
The owner said it plainly:

    "there's no way for me to look at one feature, make sure it works,
     then we move to the next, then the next, then the next."

"One feature at a time" was written down as a rule. A rule is a request. Nothing
mechanically stopped four features being built and handed over as a pile — and a
pile is untestable, so nothing in it gets properly checked, which is how a feature
reaches customers marked done and broken.

THIS MAKES IT A GATE
--------------------
Two things in flight at once FAILS the build. So the way to get back to green is
to finish one — which means the owner has to have tested it. His approval becomes
load-bearing rather than polite.

It also flags a feature that has been sitting in 'awaiting-test' with the owner
for a long time, because a forgotten test is the same as no test.
"""

from __future__ import annotations

import sys
from pathlib import Path

from ._common import FAIL, PASS, SKIP, WARN, Result

NAME = "one-at-a-time"
PLAIN = "Only one feature in flight — nothing is built while something waits for you"

IN_FLIGHT = ("building", "awaiting-test")


def run(cfg: dict) -> Result:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    try:
        import feature as F  # the board module
    except Exception as exc:
        return Result(NAME, SKIP, f"Could not read the feature board ({exc}).")

    feats = F.load_all(cfg)
    if not feats:
        return Result(
            NAME, SKIP,
            "No features declared yet, so there is no build loop to protect. Ask Claude to "
            "turn the spec into the feature list.",
        )

    flight = [f for f in feats if f["status"] in IN_FLIGHT]
    waiting = [f for f in feats if f["status"] == "awaiting-test"]
    approved = [f for f in feats if f["status"] == "approved"]

    if len(flight) > 1:
        return Result(
            NAME,
            FAIL,
            f"{len(flight)} features are being worked on at once. That is how you end up with a "
            f"pile to test instead of one thing to check. Finish one before starting another.",
            [f"{f['id']}  {f['title']}  —  {f['status']}" for f in flight],
        )

    if waiting:
        f = waiting[0]
        return Result(
            NAME,
            WARN,
            f"{f['id']} is built and waiting for YOU to test it — nothing new starts until you do. "
            f"Open feature-board.html, do the three ticks, then say approve {f['id']}.",
            [f"{f['id']}  {f['title']}"],
        )

    return Result(
        NAME, PASS,
        f"Nothing is stuck waiting on you. {len(approved)} of {len(feats)} features approved.",
    )
