"""
inventory_fresh.py — "does the ledger still match the code?"

THE FAILURE THIS PREVENTS
-------------------------
The old ledger's header claimed 331,388 bytes / 401 functions. Reality was
395,975 bytes and 500 functions — 64KB and 99 functions stale — and the same
line contradicted itself four words later.

THE MECHANISM (borrowed from terraform-docs --output-check and API Extractor)
---------------------------------------------------------------------------
Regenerate the ledger into memory. Compare it to the committed copy. If they
differ, the committed copy is stale — fail, and regenerate.

This is what makes "generated, never typed" enforceable rather than aspirational.
It also catches the specific way an AI fakes this step: writing the "generated"
file by hand instead of running the generator. A hand-written file will not match
a fresh regeneration.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from ._common import FAIL, PASS, Result

NAME = "ledger-fresh"
PLAIN = "The feature ledger matches the code (it is generated, never typed)"


def run(cfg: dict) -> Result:
    root = Path(cfg["_root"])
    gen_path = Path(__file__).resolve().parent.parent / "inventory.py"
    ledger = root / "docs" / "FEATURE-LEDGER.generated.md"

    if not gen_path.exists():
        return Result(NAME, FAIL, "scripts/inventory.py is missing — the generated ledger cannot be produced.")

    spec = importlib.util.spec_from_file_location("_inv", gen_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["_inv"] = module
    spec.loader.exec_module(module)  # type: ignore[union-attr]

    fresh = module.render(module.collect(cfg))

    if not ledger.exists():
        return Result(
            NAME,
            FAIL,
            "docs/FEATURE-LEDGER.generated.md does not exist yet. "
            "Fix: run `python3 scripts/inventory.py` and commit the result.",
        )

    committed = ledger.read_text(encoding="utf-8", errors="replace")
    # The generated date line changes daily and is not a real difference.
    def strip_date(t: str) -> str:
        return "\n".join(l for l in t.splitlines() if not l.startswith("- Generated:"))

    if strip_date(committed) == strip_date(fresh):
        return Result(NAME, PASS, "The feature ledger is an exact match for the current code.")

    # Show the owner WHAT is stale, in plain terms.
    def counts(t: str) -> dict[str, str]:
        out = {}
        for line in t.splitlines():
            if line.startswith("- ") and ":" in line:
                out[line.split(":")[0]] = line
        return out

    c_old, c_new = counts(committed), counts(fresh)
    diffs = [f"was  {c_old[k]}\n      now  {c_new[k]}" for k in c_new if c_old.get(k) != c_new.get(k)]

    return Result(
        NAME,
        FAIL,
        "The feature ledger no longer matches the code — it is stale, which is exactly "
        "how the old ledger ended up 99 functions wrong. "
        "Fix: run `python3 scripts/inventory.py` and commit the updated file.",
        diffs[:12] or ["contents differ (run the generator to see)"],
    )
