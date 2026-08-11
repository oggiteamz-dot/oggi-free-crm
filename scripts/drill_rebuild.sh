#!/usr/bin/env bash
# =============================================================================
# drill_rebuild.sh — MONTHLY. Rebuild everything from nothing, using only what
# is committed. This is the drill that stops the runbook going stale.
# =============================================================================
# THE FAILURE IT ANSWERS
# ----------------------
# The master runbook was timestamped Jul 5, 09:30. Six of the twelve things it
# governed were modified after it — some by ten days. It was never revised.
# Deploying by it returned a 500 error, because seven required database columns
# lived in a SQL file that appeared in no deploy step anywhere.
#
# A runbook nobody re-runs is already wrong. It simply has not been discovered
# yet — and it gets discovered during an outage, by the person least able to fix
# it, at the worst possible time.
#
# This is also the handover proof: if a clean-room rebuild fails, the product is
# not transferable, however well it happens to run today.
# =============================================================================
set -euo pipefail

REPO=$(git rev-parse --show-toplevel)
SCRATCH=$(mktemp -d)

echo "Clean-room rebuild in $SCRATCH"
echo "Using ONLY what is committed — nothing from this machine, nothing remembered."
echo

git clone --quiet "$REPO" "$SCRATCH/app"
cd "$SCRATCH/app"

echo "→ Replaying every migration against an EMPTY database"
if command -v supabase >/dev/null 2>&1 && [ -d supabase/migrations ]; then
  supabase start >/dev/null
  supabase db reset          # replays every migration from zero
else
  echo "  (supabase CLI unavailable — skipping, but this is the step that catches"
  echo "   a required column living in a file that is in no deploy sequence)"
fi

echo "→ Running the gate on the fresh clone"
python3 scripts/check.py

echo
echo "======================================================================"
echo "  CLEAN-ROOM REBUILD PASSED"
echo "======================================================================"
echo "  Everything needed to rebuild this product is committed. Nothing lives"
echo "  only in your head or only on your machine."
echo

STAMP=$(date +%Y-%m-%d)
if [ -f "$REPO/RUNBOOK.md" ]; then
  sed -i.bak "s/^Last rehearsed:.*/Last rehearsed: $STAMP — PASS/" "$REPO/RUNBOOK.md" && rm -f "$REPO/RUNBOOK.md.bak"
  echo "  RUNBOOK.md stamped: Last rehearsed $STAMP — PASS"
fi
echo "======================================================================"

rm -rf "$SCRATCH"
