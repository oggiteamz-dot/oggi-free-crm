"""
persistence.py — "will this still be there after a reload, on another device?"

THE FAILURE THIS PREVENTS — the most expensive one in the estate
---------------------------------------------------------------
A 📣 Notify button wrote `STATE.announcements`. That key was missing from all
three persistence lists (DATA_KEYS, saveLocal, hydrate). So:

  - On the device that clicked it, the badge appeared and survived until reload.
  - On the buyer's device, the announcement NEVER arrived. Not once. Ever.
  - Both features were marked ✅ done and tested.

The product's own feature ledger contained a written warning about exactly this
trap. The warning did not help, because a warning is not a check.

WHY A RELOAD TEST IS NOT ENOUGH
-------------------------------
In this architecture localStorage is the cache layer. A same-tab reload reads
the value straight back out of localStorage, the test goes green, and the feature
has still never once worked on a second device. That is why the runtime test in
verify_live.mjs opens a FRESH BROWSER CONTEXT and asserts again, and reports
`survives_reload` and `survives_fresh_device` as two separate results.

Failing only the second is the exact fingerprint of this bug.

This static check is the cheap early-warning version of that runtime test.
"""

from __future__ import annotations

import re

from ._common import FAIL, PASS, SKIP, Result, is_exempt, iter_source_files, read, rel

NAME = "persistence"
PLAIN = "Everything the app saves is actually on the save list (survives reload + other devices)"


def _written_keys(cfg: dict) -> dict[str, list[str]]:
    """Find every key the UI assigns onto the shared state object.

    Matches, for a state object named STATE:
        STATE.foo = ...
        STATE['foo'] = ...
        STATE.foo.push(...)      (a mutation still needs persisting)
        STATE.foo ||= ...
    """
    obj = cfg.get("state_object", "STATE")
    patterns = [
        re.compile(rf"\b{re.escape(obj)}\.([A-Za-z_$][\w$]*)\s*(=[^=]|\|\|=|\?\?=|\+=)"),
        re.compile(rf"\b{re.escape(obj)}\[\s*['\"]([A-Za-z_$][\w$]*)['\"]\s*\]\s*="),
        re.compile(rf"\b{re.escape(obj)}\.([A-Za-z_$][\w$]*)\.(push|splice|unshift|pop|shift|sort)\("),
    ]
    found: dict[str, list[str]] = {}
    for path in iter_source_files(cfg):
        if is_exempt(cfg, path):
            continue
        text = read(path)
        if obj not in text:
            continue
        for pat in patterns:
            for m in pat.finditer(text):
                key = m.group(1)
                lineno = text.count("\n", 0, m.start()) + 1
                found.setdefault(key, []).append(f"{rel(cfg, path)}:{lineno}")
    return found


def _allowlist(cfg: dict) -> set[str] | None:
    """Read the declared list of keys that get saved and synced.

    Looks for an array literal assigned to the configured symbol, e.g.
        const DATA_KEYS = ['products', 'orders', 'clients'];
    """
    path_str = cfg.get("persistence_allowlist") or ""
    symbol = cfg.get("persistence_symbol", "DATA_KEYS")
    if not path_str:
        return None
    from pathlib import Path

    p = Path(cfg["_root"]) / path_str
    if not p.exists():
        return None
    text = read(p)
    m = re.search(rf"{re.escape(symbol)}\s*[:=]\s*\[(.*?)\]", text, re.S)
    if not m:
        return None
    return set(re.findall(r"['\"]([A-Za-z_$][\w$]*)['\"]", m.group(1)))


def run(cfg: dict) -> Result:
    allow = _allowlist(cfg)
    if allow is None:
        return Result(
            NAME,
            SKIP,
            "No save-list configured. Set persistence_allowlist + persistence_symbol in "
            "oggi-build.config.json so this check can protect you. Until then, the "
            "'worked until reload' bug can happen again.",
        )

    written = _written_keys(cfg)
    # Keys the app writes but never saves -> the dangerous direction.
    unsaved = {k: v for k, v in written.items() if k not in allow}
    # Keys on the save list that nothing ever writes -> dead weight, worth knowing.
    unwritten = sorted(allow - set(written))

    details = []
    for key, locations in sorted(unsaved.items()):
        details.append(f"'{key}' written at {', '.join(locations[:3])} — NOT on the save list")
    for key in unwritten:
        details.append(f"'{key}' is on the save list but nothing ever writes it (dead)")

    if unsaved:
        first = sorted(unsaved)[0]
        return Result(
            NAME,
            FAIL,
            f"{len(unsaved)} thing(s) the app saves would VANISH on reload and would "
            f"never appear on another device — starting with '{first}'. "
            f"Fix: add '{first}' to {cfg.get('persistence_symbol', 'DATA_KEYS')} in "
            f"{cfg.get('persistence_allowlist')}, then re-test on a second device.",
            details[:40],
        )

    if unwritten:
        return Result(
            NAME,
            PASS,
            f"Everything the app saves is on the save list. "
            f"({len(unwritten)} unused entries on the list — harmless, listed below.)",
            details[:20],
        )

    return Result(NAME, PASS, f"All {len(written)} saved things are on the save list.")
