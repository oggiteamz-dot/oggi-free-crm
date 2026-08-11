"""
boundaries.py — "can editing one feature break another one?"

THE PROBLEM THIS EXISTS FOR — and it is the root cause of the worst pain
------------------------------------------------------------------------
Claude's habit is to build a whole product as ONE enormous HTML file. There are
real reasons for it: no install, no build step, no server, deploy by dragging one
file. For a non-technical owner it removes six setup steps that could each fail.

And it is a one-way door. The wholesale app reached ~396KB and 500 functions, at
which point:

  * the editing tool silently truncated the file's tail on save — five separate
    times, killing every login and button
  * the file stopped fitting in view, so edits became whole-file REGENERATIONS
    from memory
  * regeneration from memory is exactly how 294 of 500 functions ended up
    undocumented and how features vanished during "updates"
  * 18 functions ended up defined twice, 21 dead copies, so editing the wrong
    copy changed nothing while looking successful

Every one of those is downstream of one choice: everything in one file.

THE STRUCTURE THAT FIXES IT WITHOUT ADDING TOOLS
-----------------------------------------------
Browsers run ES modules natively. `<script type="module">` plus `import`. No npm,
no bundler, no build step — still deployed by dragging a folder. So:

    src/
      index.html
      core/          shared: state, storage, text, errors   (everyone may import)
      features/
        orders/      one folder per feature                 (nobody else's business)
        catalog/
        admin/

THE RULE THIS CHECK ENFORCES

    A feature may import from core/.
    A feature may NOT import from another feature.

That single rule is what makes "editing the booking calendar cannot break the
payment code" a structural fact rather than a hope. If two features genuinely need
to share something, the shared thing belongs in core/ — which is a deliberate,
visible move rather than a quiet tangle.
"""

from __future__ import annotations

import re

from ._common import FAIL, PASS, SKIP, Result, is_exempt, iter_source_files, read, rel

NAME = "boundaries"
PLAIN = "No feature reaches into another feature's code"

IMPORT = re.compile(
    r"""(?:import\s[^'"]*from\s*|import\s*|export\s[^'"]*from\s*|require\s*\(\s*)['"]([^'"]+)['"]"""
)
FEATURE_PATH = re.compile(r"(?:^|/)features/([^/]+)/")


def run(cfg: dict) -> Result:
    root_marker = cfg.get("features_dir", "features")
    problems: list[str] = []
    seen_features: set[str] = set()

    for path in iter_source_files(cfg):
        if is_exempt(cfg, path):
            continue
        posix = str(path).replace("\\", "/")
        m = FEATURE_PATH.search(posix)
        if not m:
            continue
        mine = m.group(1)
        seen_features.add(mine)

        for im in IMPORT.finditer(read(path)):
            target = im.group(1)
            if not target.startswith("."):
                continue          # a package, not a local file
            # Resolve the import relative to the importing file, then see whose
            # feature folder it lands in.
            resolved = (path.parent / target).resolve()
            other = FEATURE_PATH.search(str(resolved).replace("\\", "/"))
            if other and other.group(1) != mine:
                lineno = read(path).count("\n", 0, im.start()) + 1
                problems.append(
                    f"{rel(cfg, path)}:{lineno}  →  '{mine}' imports from '{other.group(1)}'\n"
                    f"      {target}"
                )

    if not seen_features:
        return Result(
            NAME,
            SKIP,
            f"No feature folders found under {root_marker}/. This product is not laid out one "
            f"folder per feature yet, so nothing keeps features from tangling. That layout is "
            f"what stops an edit to one thing breaking another.",
        )

    if problems:
        return Result(
            NAME,
            FAIL,
            f"{len(problems)} place(s) where one feature reaches directly into another. "
            f"That is how editing one thing breaks a different thing. "
            f"Fix: move what they share into core/ and have both import it from there.",
            problems[:25],
        )

    return Result(
        NAME,
        PASS,
        f"{len(seen_features)} feature(s), each self-contained. Editing one cannot break another.",
    )
