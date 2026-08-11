"""
xss.py — "can something a customer typed become code on someone else's screen?"

THE FAILURE THIS PREVENTS
-------------------------
A live product in this estate had **no HTML escaping anywhere**. Lead names came
from a public, ad-facing form and went straight into the page — stored XSS aimed
at the professionals' own dashboards. The moderation gate that would have caught
it shipped disabled. The Owner Console in the same estate *did* escape, with a
comment explaining this exact risk, which is what makes the omission legible: it
was known and simply not applied everywhere.

WHAT IT CHECKS
--------------
Every place where a string becomes markup — innerHTML, outerHTML, document.write,
insertAdjacentHTML, dangerouslySetInnerHTML, v-html, eval — and asks: is the value
escaped or sanitised first?

WHAT COUNTS AS SAFE
-------------------
  * a literal string with no interpolation           ->  safe
  * wrapped in esc(), escapeHtml(), DOMPurify.sanitize -> safe
  * textContent / innerText instead of innerHTML     ->  safe (and preferred)

WHAT IT CANNOT DO
-----------------
It cannot tell whether the data reaching a safe-looking sink came from a customer.
Escaping everything is the only reliable rule, so it flags unescaped interpolation
regardless of source rather than trying to trace it — tracing produces false
negatives, and a false negative here is a security hole.
"""

from __future__ import annotations

import re

from ._common import FAIL, PASS, WARN, Result, code_lines, is_exempt, iter_source_files, read, rel

NAME = "escaping"
PLAIN = "Nothing a customer types can become code on someone else's screen"

SINKS = [
    (re.compile(r"\.innerHTML\s*[+]?=\s*(.+)"), "innerHTML"),
    (re.compile(r"\.outerHTML\s*[+]?=\s*(.+)"), "outerHTML"),
    (re.compile(r"insertAdjacentHTML\s*\([^,]+,\s*(.+)"), "insertAdjacentHTML"),
    (re.compile(r"document\.write(?:ln)?\s*\((.+)"), "document.write"),
    (re.compile(r"dangerouslySetInnerHTML\s*=\s*\{\{\s*__html:\s*(.+)"), "dangerouslySetInnerHTML"),
    (re.compile(r"\bv-html\s*=\s*[\"'](.+)"), "v-html"),
    (re.compile(r"\{@html\s+(.+)"), "svelte {@html}"),
]

EVAL = re.compile(r"(?<![\w.])eval\s*\(|new\s+Function\s*\(")

# Anything that makes the value safe before it becomes markup.
SAFE = re.compile(
    r"(esc\(|escapeHtml|escapeHTML|htmlEscape|sanitize|sanitise|DOMPurify|"
    r"encodeURIComponent|textContent|innerText|\.toFixed|JSON\.stringify)",
    re.I,
)

# A value with no interpolation at all cannot carry customer input.
INTERPOLATED = re.compile(r"[`$]\{|\+\s*[A-Za-z_$]|\$\{|\bconcat\(")


def run(cfg: dict) -> Result:
    unsafe: list[str] = []
    evals: list[str] = []
    sinks_seen = 0

    for path in iter_source_files(cfg):
        if is_exempt(cfg, path) or path.suffix == ".sql":
            continue
        label = rel(cfg, path)
        for lineno, line in code_lines(read(path)):
            for pattern, sink in SINKS:
                m = pattern.search(line)
                if not m:
                    continue
                sinks_seen += 1
                value = m.group(1)
                if SAFE.search(line):
                    continue
                if not INTERPOLATED.search(value):
                    continue  # a fixed literal — no customer data can reach it
                unsafe.append(
                    f"{label}:{lineno}  →  {sink} with un-escaped data\n"
                    f"      {line.strip()[:130]}"
                )
                break
            if EVAL.search(line):
                evals.append(f"{label}:{lineno}  →  runs text as code: {line.strip()[:110]}")

    if unsafe:
        return Result(
            NAME,
            FAIL,
            f"{len(unsafe)} place(s) put un-escaped data straight into the page. If a "
            f"customer types a script into a form, it runs on your staff's screens. "
            f"Fix: wrap the value in esc() — or use .textContent instead of .innerHTML, "
            f"which is safe by default.",
            unsafe[:30] + evals[:5],
        )

    if evals:
        return Result(
            NAME,
            WARN,
            f"Nothing un-escaped reaches the page. {len(evals)} place(s) run text as code "
            f"(eval / new Function) — almost always avoidable and worth removing.",
            evals[:15],
        )

    return Result(
        NAME,
        PASS,
        f"All {sinks_seen} place(s) that write into the page escape their data first."
        if sinks_seen
        else "Nothing writes raw markup into the page.",
    )
