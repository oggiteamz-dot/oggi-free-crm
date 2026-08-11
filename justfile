# =============================================================================
# justfile — THE RUNBOOK, AS A PROGRAM.
# =============================================================================
#
# WHY THIS FILE EXISTS INSTEAD OF A RUNBOOK DOCUMENT
# --------------------------------------------------
# "Following your own runbook produces a broken system." The MASTER RUNBOOK was
# timestamped Jul 5 09:30. Six of the twelve things it governed were modified
# after it — some by ten days. It was never revised. Deploying by it returned a
# 500 error because seven database columns it never mentioned were required.
#
# A document describing steps goes stale the moment the steps change.
# A program that PERFORMS the steps cannot: if it is wrong, it fails today.
#
# Every command is documented in plain English. Run `just` with no arguments to
# see the menu. If `just` is not installed, every recipe is a one-line shell
# command you can run directly — they are printed below each name.
# =============================================================================

# Show the menu (this is the default when you type `just`)
default:
    @just --list --unsorted

# ── THE BUILD LOOP — one feature at a time, you decide when it's done ───────

# Where are we? What's built, what's waiting for you, what's next.
board:
    python3 scripts/feature.py board

# I start ONE feature. Refuses while anything is still waiting on you.
start FEAT:
    python3 scripts/feature.py start {{FEAT}}

# I finished it and it's live — now it's your turn to test.
built FEAT URL:
    python3 scripts/feature.py built {{FEAT}} --url {{URL}}

# You tested it and all three ticks passed. Locks it onto the never-break list.
approve FEAT:
    python3 scripts/feature.py approve {{FEAT}} --by Hadi

# You tested it and something was wrong. Say what.
reject FEAT WHY:
    python3 scripts/feature.py reject {{FEAT}} --why "{{WHY}}"

# ── THE THREE COMMANDS THAT MATTER ──────────────────────────────────────────

# STEP 0 of every session: is my computer the same as what's live?
census:
    bash scripts/census.sh

# THE GATE: green or red, under 60 seconds. Run before every commit and deploy.
check:
    python3 scripts/check.py

# FIRST RUN ON AN EXISTING PRODUCT: put today's problems on a backlog so they
# stay visible but stop blocking you. Only NEW problems fail after this.
# Without it, installing the toolkit on a live client product freezes it.
adopt:
    python3 scripts/check.py --adopt

# Prove it works ON THE LIVE SITE, including on a second device.
verify-live:
    node scripts/verify_live.mjs

# ── SCOPE — the plan, and the same plan scored against what shipped ────────

# The scorecard: agreed features vs never-built vs approved. Open on your phone.
score:
    python3 scripts/matrix.py score --html

# Match matrix rows to feature files after adding features
link:
    python3 scripts/matrix.py link

# ── SUPPORTING ──────────────────────────────────────────────────────────────

# Regenerate the feature ledger from the code (never write it by hand)
inventory:
    python3 scripts/inventory.py

# Show what this change added and — the important one — what it REMOVED
diff:
    python3 scripts/inventory.py && python3 scripts/surface_diff.py

# Accept the current state as the comparison point for future changes
baseline:
    python3 scripts/inventory.py && python3 scripts/surface_diff.py --save-baseline

# Print the Proof Cards you personally tick for each feature
proof:
    python3 scripts/proof_cards.py

# Everything at once, in the right order. This is the pre-deploy ritual.
ready: census inventory check
    @echo ""
    @echo "  Mechanical checks are green. Two things left, and neither is optional:"
    @echo "    1. just proof        — tick the Proof Cards yourself"
    @echo "    2. just deploy       — then it verifies against the live URL"
    @echo ""

# ── DEPLOY ──────────────────────────────────────────────────────────────────

# Deploy. REFUSES to run unless the gate passed on this exact version recently.
deploy:
    @python3 scripts/guard_deploy.py
    @echo "Gate verified. Deploying…"
    bash scripts/deploy.sh
    @echo "Deployed. Now proving it actually went live…"
    node scripts/verify_live.mjs

# Roll back to the previous released version
rollback:
    bash scripts/rollback.sh

# ── DRILLS (run monthly — these are what stop the runbook going stale) ───────

# Rebuild the whole system from scratch using ONLY this file. If it fails, the
# runbook is broken — which is better learned now than during an outage.
drill-rebuild:
    bash scripts/drill_rebuild.sh

# Restore the latest backup into a scratch database and confirm it works.
# An untested backup is not a backup. It is a hope.
drill-restore:
    bash scripts/drill_restore.sh

# Run the read-only database security queries
audit-db:
    supabase db query -f sql/03_diagnostics.sql
