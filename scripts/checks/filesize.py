"""
filesize.py — "is this file too big for an AI to edit safely?"

THE FAILURE THIS PREVENTS
-------------------------
The live wholesale product is a single HTML file of ~396KB containing 500
functions. Consequences observed in the estate, all traceable to file size:

  - The Edit tool silently TRUNCATED the file's tail on save, killing every
    login and button, five separate times.
  - 21 dead duplicate definitions accumulated because nobody could hold the file
    in view at once.
  - A whole-file rewrite became the only practical edit, and a whole-file rewrite
    from memory is exactly how 294 undocumented functions came to exist.

Small files are not a style preference here. They are the mechanism that keeps
edit-in-place possible, which is the mechanism that stops features vanishing.

WARN, NOT FAIL, BY DEFAULT
--------------------------
Existing products would fail this on day one and the gate would get disabled.
It FAILS only for files created after the project adopted the toolkit — set
"filesize_enforce": true once a product has been split.
"""

from __future__ import annotations

from ._common import FAIL, PASS, WARN, Result, is_exempt, iter_source_files, read, rel

NAME = "file-size"
PLAIN = "No file too large to edit safely (large files are where edits silently break things)"


def run(cfg: dict) -> Result:
    cap = int(cfg.get("max_file_lines", 600))
    enforce = bool(cfg.get("filesize_enforce", False))
    over = []

    for path in iter_source_files(cfg):
        if is_exempt(cfg, path):
            continue
        n = read(path).count("\n") + 1
        if n > cap:
            over.append((n, rel(cfg, path)))

    if not over:
        return Result(NAME, PASS, f"Every file is under {cap} lines.")

    over.sort(reverse=True)
    details = [f"{n:>6} lines — {p}  (cap {cap})" for n, p in over[:25]]
    worst = over[0]
    msg = (
        f"{len(over)} file(s) are over {cap} lines — biggest is {worst[1]} at {worst[0]} lines. "
        f"Files this size are where edits silently truncate and features disappear. "
        f"Fix: split it into one file per feature area."
    )
    return Result(NAME, FAIL if enforce else WARN, msg, details)
