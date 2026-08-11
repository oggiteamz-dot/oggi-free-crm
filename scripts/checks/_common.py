"""
_common.py — shared helpers for every check in the OGGI Build gate.

WHAT THIS FILE IS FOR (plain English)
-------------------------------------
Every individual check (placeholders, persistence, orphans, ...) needs the same
three things: a way to read the project config, a way to walk the source files
while skipping junk, and a standard way to report PASS / FAIL / WARN.

This file provides all three so the checks themselves stay short and readable.

NOTHING IN HERE DECIDES ANYTHING. It only reads files and formats results.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

# --------------------------------------------------------------------------
# Result object — the single shape every check returns
# --------------------------------------------------------------------------

PASS = "PASS"
FAIL = "FAIL"
WARN = "WARN"
SKIP = "SKIP"


@dataclass
class Result:
    """The outcome of one check.

    status  — PASS / FAIL / WARN / SKIP
    plain   — ONE sentence a non-technical person can act on. Never jargon.
              On FAIL this MUST name the file (and line, if known) and the fix.
    details — the specific offending lines, shown underneath the table.
    """

    name: str
    status: str
    plain: str
    details: list[str] = field(default_factory=list)

    @property
    def failed(self) -> bool:
        return self.status == FAIL


# --------------------------------------------------------------------------
# Config — read once from oggi-build.config.json at the project root
# --------------------------------------------------------------------------

DEFAULT_CONFIG = {
    # Where the product's own source code lives (relative to project root).
    "source_dirs": ["src", "app", "supabase/functions", "public", "scripts/app"],
    # File extensions treated as source code.
    "source_exts": [".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".html", ".sql", ".py", ".vue", ".svelte"],
    # Never scanned. Add anything generated or vendored.
    #
    # NOTE: scripts/, sql/, templates/ and ci/ are the TOOLKIT'S OWN files. They
    # are full of the very strings the checks look for, because they document
    # them. Scanning them produced ~60 false alarms on a clean install — and one
    # false alarm is stated to be fatal to adoption. They are excluded by default.
    "ignore_dirs": [
        ".git", "node_modules", "dist", "build", ".next", ".cache", "vendor",
        "_backup_bundles", "_releases", "coverage", ".venv", "venv", "__pycache__",
        ".claude", "evidence", "scripts", "sql", "templates", "ci", "docs",
        "_backups", ".github",
    ],
    # The live product URL. Used by the live checks. "" disables them.
    "live_url": "",
    # Path to the file that lists which state keys are persisted/synced.
    # The persistence check compares "keys written by the UI" against this list.
    "persistence_allowlist": "",
    # Extra banned strings on top of the built-in list.
    "extra_placeholders": [],
    # Files where a placeholder is legitimately allowed (templates, examples).
    "placeholder_exempt": [
        "templates/", "examples/", "README", ".sample", ".example",
        "scripts/", "toolkit/", "/sql/", "PROJECT-SKELETON",
    ],
    # Max lines per source file. Big files are where AI edits go wrong.
    "max_file_lines": 600,
    # Set false for products that genuinely have no database.
    "has_database": True,
}


def project_root(start: Path | None = None) -> Path:
    """Walk upward until we find the config file or a .git folder."""
    p = (start or Path.cwd()).resolve()
    for candidate in [p, *p.parents]:
        if (candidate / "oggi-build.config.json").exists():
            return candidate
        if (candidate / ".git").exists():
            return candidate
    return p


def load_config(root: Path | None = None) -> dict:
    root = root or project_root()
    cfg = dict(DEFAULT_CONFIG)
    cfg_path = root / "oggi-build.config.json"
    if cfg_path.exists():
        try:
            cfg.update(json.loads(cfg_path.read_text(encoding="utf-8")))
        except json.JSONDecodeError as exc:
            # A broken config must be loud, not silently ignored.
            print(f"ERROR: oggi-build.config.json is not valid JSON — {exc}", file=sys.stderr)
            raise SystemExit(2)
    cfg["_root"] = str(root)
    return cfg


# --------------------------------------------------------------------------
# Walking the source tree
# --------------------------------------------------------------------------

def iter_source_files(cfg: dict):
    """Yield every source file the checks should look at, as Path objects."""
    root = Path(cfg["_root"])
    ignore = set(cfg["ignore_dirs"])
    exts = set(cfg["source_exts"])
    search_roots = [root / d for d in cfg["source_dirs"] if (root / d).exists()]
    # If none of the configured dirs exist, fall back to the whole project — but
    # say so, because a silent fallback scans the toolkit's own templates and
    # produces failures that look real and are not.
    if not search_roots:
        print(
            f"NOTE: none of the configured source folders exist "
            f"({', '.join(cfg['source_dirs'])}) — scanning the whole project instead. "
            f"Set source_dirs in oggi-build.config.json to point at your app's code.",
            file=sys.stderr,
        )
        search_roots = [root]
    seen = set()
    for base in search_roots:
        if not base.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames if d not in ignore and not d.startswith(".")]
            for fn in filenames:
                fp = Path(dirpath) / fn
                if fp.suffix.lower() not in exts:
                    continue
                if fp in seen:
                    continue
                seen.add(fp)
                yield fp


def rel(cfg: dict, path: Path) -> str:
    """Path shown to the human — always relative to the project root."""
    try:
        return str(path.relative_to(Path(cfg["_root"])))
    except ValueError:
        return str(path)


def read(path: Path) -> str:
    """Read a file without ever throwing on a weird byte."""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def is_exempt(cfg: dict, path: Path) -> bool:
    s = str(path).replace("\\", "/")
    return any(frag in s for frag in cfg.get("placeholder_exempt", []))


# --------------------------------------------------------------------------
# Comment stripping — so a check does not fire on a commented-out example
# --------------------------------------------------------------------------

_LINE_COMMENT = re.compile(r"^\s*(//|#|--|\*|/\*)")


def code_lines(text: str):
    """Yield (line_number, line) for lines that look like real code, not comments.

    Deliberately simple. A false negative (missing a hit inside a comment) is
    fine; a false POSITIVE would teach the owner that the gate lies, which is
    the one failure mode that kills the whole system.
    """
    for i, line in enumerate(text.splitlines(), start=1):
        if _LINE_COMMENT.match(line):
            continue
        yield i, line


# --------------------------------------------------------------------------
# Shell helper
# --------------------------------------------------------------------------

def sh(cmd: str, cwd: str | None = None, timeout: int = 60) -> tuple[int, str]:
    """Run a shell command, return (exit_code, combined_output). Never raises."""
    try:
        proc = subprocess.run(
            cmd, shell=True, cwd=cwd, capture_output=True, text=True, timeout=timeout
        )
        return proc.returncode, (proc.stdout or "") + (proc.stderr or "")
    except subprocess.TimeoutExpired:
        return 124, f"timed out after {timeout}s"
    except OSError as exc:
        return 127, str(exc)


def have(tool: str) -> bool:
    """Is a command-line tool available?"""
    code, _ = sh(f"command -v {tool}")
    return code == 0
