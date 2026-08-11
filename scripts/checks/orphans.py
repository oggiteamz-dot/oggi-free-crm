"""
orphans.py — "is anything here wired to nothing?"

THE FAILURES THIS PREVENTS
--------------------------
1. A button whose handler does not exist  → the user clicks and nothing happens,
   forever, with no error. (Checked: every onclick/onsubmit target must resolve.)
2. A dead anchor  → `href="#"`, `href=""`, or a link rendered as literal text.
   One shipped OGGI product rendered `[Portfolio Builder file]?p=<token>` as a
   dead link on a client-facing page.
3. Dead code  → functions nobody calls. Harmless individually, but they are how a
   540-function file gets to 540 functions and stops being editable safely.

PRECISION OVER RECALL
---------------------
Only the first two FAIL. Dead code WARNs, because a genuinely-unused export can
be legitimate (a public API, a handler bound at runtime) and a false alarm here
would teach the owner to distrust the whole gate.
"""

from __future__ import annotations

import re

from ._common import FAIL, PASS, WARN, Result, is_exempt, iter_source_files, read, rel

NAME = "orphans"
PLAIN = "No button wired to nothing, no dead links, no unreachable code"

HANDLER = re.compile(
    r"""\bon(?:click|submit|change|input|keyup|keydown|blur|focus)\s*=\s*["']\s*([A-Za-z_$][\w$]*)\s*\(""",
    re.I,
)
DECL = re.compile(
    r"(?:function\s+([A-Za-z_$][\w$]*)"
    r"|(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?(?:function\b|\([^)]*\)\s*=>|[A-Za-z_$][\w$]*\s*=>)"
    r"|([A-Za-z_$][\w$]*)\s*:\s*(?:async\s*)?function\b"
    r"|window\.([A-Za-z_$][\w$]*)\s*=)"
)
# An anchor with href="#" is only dead if nothing else handles the click.
# <a href="#" onclick="doThing()"> is a completely standard pattern, and failing
# it was a false alarm — which is the one thing that gets a gate deleted.
DEAD_ANCHOR = re.compile(
    r"""<a\b(?![^>]*\bon[a-z]+\s*=)(?![^>]*\b(?:@click|v-on:|\(click\)|data-action))"""
    r"""[^>]*href\s*=\s*["'](\s*|#|javascript:void\(0\)|javascript:;|null|undefined)["']""",
    re.I,
)
# An anchor whose href still contains an unrendered template token.
UNRENDERED_HREF = re.compile(r"""<a\b[^>]*href\s*=\s*["'][^"']*(\{\{|<[a-z_]+>|\[[A-Z][A-Za-z ]{3,})""", re.I)

HTML_EXTS = {".html", ".vue", ".svelte", ".jsx", ".tsx"}


def run(cfg: dict) -> Result:
    declared: set[str] = set()
    handler_uses: list[tuple[str, int, str]] = []
    dead_links: list[str] = []
    all_text: list[tuple[str, str]] = []

    for path in iter_source_files(cfg):
        if is_exempt(cfg, path):
            continue
        text = read(path)
        label = rel(cfg, path)
        all_text.append((label, text))

        for m in DECL.finditer(text):
            name = m.group(1) or m.group(2) or m.group(3) or m.group(4)
            if name:
                declared.add(name)

        for m in HANDLER.finditer(text):
            handler_uses.append((m.group(1), text.count("\n", 0, m.start()) + 1, label))

        if path.suffix.lower() in HTML_EXTS:
            for pattern, why in ((DEAD_ANCHOR, "link goes nowhere"), (UNRENDERED_HREF, "link still contains a template placeholder")):
                for m in pattern.finditer(text):
                    lineno = text.count("\n", 0, m.start()) + 1
                    dead_links.append(f"{label}:{lineno}  →  {why}: {m.group(0)[:90]}")

    # --- 1. handlers that point at nothing --------------------------------
    missing = [
        f"{label}:{line}  →  onclick calls {name}() but {name} is never defined — "
        f"this button does nothing when clicked"
        for name, line, label in handler_uses
        if name not in declared
    ]

    # --- 2. dead code (WARN only) -----------------------------------------
    corpus = "\n".join(t for _, t in all_text)
    unused = []
    for name in sorted(declared):
        if len(name) < 4:
            continue  # too short to count references reliably
        refs = len(re.findall(rf"\b{re.escape(name)}\b", corpus))
        if refs <= 1:
            unused.append(name)

    hard = missing + dead_links
    if hard:
        return Result(
            NAME,
            FAIL,
            f"{len(missing)} button(s) wired to nothing and {len(dead_links)} dead link(s). "
            f"A user clicking these gets silence. First: {hard[0].split('  →  ')[0]}. "
            f"Fix: either write the missing function or remove the control.",
            hard[:40] + ([f"(also {len(unused)} unused functions — see WARN detail)"] if unused else []),
        )

    if unused:
        return Result(
            NAME,
            WARN,
            f"Everything is wired. {len(unused)} function(s) are never called — dead weight "
            f"that makes future edits riskier. Worth deleting when convenient.",
            [f"never called: {n}" for n in unused[:30]],
        )

    return Result(NAME, PASS, "Every control is wired, every link resolves, no dead code.")
