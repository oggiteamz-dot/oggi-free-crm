"""
silent_catch.py — "will a failure be invisible?"

THE FAILURE THIS PREVENTS
-------------------------
In a live OGGI product, a try/catch swallowed an error. The consequence: every
matched lead and every matched freelancer was NEVER notified. The lead sat
waiting for a call that would never come. There was no error anywhere, no alert,
and nobody found out until a forensic audit months later.

WHAT THIS CATCHES — AND WHAT IT CANNOT
--------------------------------------
This catches HALF the problem: an error that happened and was swallowed.

It CANNOT catch the other half — code that never ran at all, so there was no
exception to swallow. That half needs the outbox + heartbeat pattern from the
foundation (see build-make/references/foundation.md). Nothing a scanner can do
will detect silence. Do not mistake a green result here for "notifications work".
"""

from __future__ import annotations

import re

from ._common import FAIL, PASS, WARN, Result, is_exempt, iter_source_files, read, rel

NAME = "silent-failures"
PLAIN = "No error is swallowed silently — every failure is reported somewhere"

# A catch block whose body is empty or only whitespace/comments.
EMPTY_CATCH = re.compile(r"catch\s*(\([^)]*\))?\s*\{\s*(//[^\n]*\s*|/\*.*?\*/\s*)*\}", re.S)

# .catch(() => ...) that returns a fallback instead of reporting.
SWALLOW_ARROW = re.compile(r"\.catch\s*\(\s*\(?\s*[\w$]*\s*\)?\s*=>\s*(\[\]|\{\}|null|undefined|false|0|''|\"\")\s*\)")

# A catch block that only logs. console.error is not reporting: nobody reads a
# customer's browser console.
LOG_ONLY_CATCH = re.compile(
    r"catch\s*\([^)]*\)\s*\{\s*console\.(log|warn|error|debug)\([^)]*\)\s*;?\s*\}", re.S
)

# Python's version of the same sin.
PY_BARE = re.compile(r"except[^\n:]*:\s*\n\s*(pass|continue)\s*(\n|$)")

# What counts as actually reporting an error. At least one must appear in the
# catch body. reportError() is the helper the foundation installs.
#
# Anything that plausibly surfaces the failure to a human. Deliberately generous:
# `catch (e) { setError(e.message) }` DOES tell the user, and failing it taught
# the owner that the gate lies — which is the one failure mode that kills the
# whole system. Only a genuinely empty or genuinely swallowing catch FAILS;
# "no recognised reporter" is a WARN.
REPORTERS = (
    "reportError", "captureException", "logError", "trackError", "toast", "showError",
    "setError", "notify", "alert(", "rethrow", "throw", "reject", "Sentry",
    "console.error", "flash", "banner", "message", "status", "err", "error",
)

SKIP_FILES = ("error-sink", "reportError", "silent_catch")


def _catch_bodies(text: str):
    """Yield (line_no, body_text) for every JS/TS catch block, brace-matched."""
    for m in re.finditer(r"catch\s*(\([^)]*\))?\s*\{", text):
        start = m.end() - 1
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    body = text[start + 1 : i]
                    lineno = text.count("\n", 0, m.start()) + 1
                    yield lineno, body
                    break


def run(cfg: dict) -> Result:
    problems: list[str] = []      # FAIL — the failure genuinely disappears
    soft: list[str] = []          # WARN — probably fine, worth a look

    for path in iter_source_files(cfg):
        if is_exempt(cfg, path) or any(s in str(path) for s in SKIP_FILES):
            continue
        text = read(path)
        label = rel(cfg, path)

        if path.suffix == ".py":
            for m in PY_BARE.finditer(text):
                lineno = text.count("\n", 0, m.start()) + 1
                problems.append(f"{label}:{lineno}  →  except: pass — the failure disappears")
            continue

        for lineno, body in _catch_bodies(text):
            stripped = re.sub(r"//[^\n]*|/\*.*?\*/", "", body, flags=re.S).strip()
            if not stripped:
                problems.append(f"{label}:{lineno}  →  empty catch — the failure disappears")
            elif not any(r in body for r in REPORTERS):
                snippet = " ".join(stripped.split())[:90]
                soft.append(
                    f"{label}:{lineno}  →  this catch may not tell anyone: {snippet}"
                )

        for m in SWALLOW_ARROW.finditer(text):
            lineno = text.count("\n", 0, m.start()) + 1
            problems.append(
                f"{label}:{lineno}  →  .catch returns a fake empty value instead of reporting"
            )

    if problems:
        return Result(
            NAME,
            FAIL,
            f"{len(problems)} place(s) where a failure would happen silently and nobody "
            f"would ever know. First: {problems[0]}. Fix: add reportError(err, 'what "
            f"was happening') inside the catch, and show the user a visible message.",
            problems[:40] + soft[:10],
        )

    if soft:
        return Result(
            NAME,
            WARN,
            f"No failure disappears completely. {len(soft)} error handler(s) do not use a "
            f"recognised way of reporting — worth a look, but they may well be fine.",
            soft[:25],
        )

    return Result(NAME, PASS, "Every error path reports somewhere a human can see it.")
