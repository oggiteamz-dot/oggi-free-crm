#!/usr/bin/env bash
# =============================================================================
# deploy.sh — FILL THIS IN PER PRODUCT. It is the runbook, as a program.
# =============================================================================
# Never called directly. `just deploy` calls guard_deploy.py first, which refuses
# unless the gate passed on THIS exact commit within the last 15 minutes and the
# working tree is clean. That is what makes the path of least resistance go
# THROUGH the gate instead of around it.
#
# THE RULE: if a step is manual, it lives HERE as a prompt — not in a document.
# A document describing steps goes stale the moment the steps change. A program
# that performs them cannot: if it is wrong, it fails today rather than during
# an outage three weeks from now.
# =============================================================================
set -euo pipefail

SHA=$(git rev-parse HEAD)
echo "Deploying ${SHA:0:12}"

# --- 1. Write the build id so /__version can answer truthfully ---------------
# Without this, "is the live site running my latest change?" is unanswerable and
# "deployed" stays an opinion instead of a fact.
mkdir -p public
echo "$SHA" > public/__version

# --- 2. Database FIRST, always -----------------------------------------------
# Code that expects a column deploys AFTER the column exists. The other order is
# how a deploy produces 500 errors on a customer's screen.
if [ -d supabase/migrations ]; then
  supabase db push
fi

# --- 3. Server functions -----------------------------------------------------
if [ -d supabase/functions ]; then
  for fn in supabase/functions/*/; do
    name=$(basename "$fn")
    [ "$name" = "_shared" ] && continue
    echo "  deploying function: $name"
    supabase functions deploy "$name"
  done
fi

# --- 4. The front end --------------------------------------------------------
# REMINDER — this has broken this estate five separate times:
#   * Upload the APP SUBFOLDER, never the parent folder.
#   * A PWA needs ALL its files: sw.js, every manifest-*.json, every icon.
#     Uploading only index.html silently strips install, icons and offline
#     support while appearing to succeed.
#
# --- FILL IN THE ONE LINE FOR THIS PRODUCT, THEN DELETE THIS BLOCK ---
echo ""
echo "  deploy.sh has no front-end step for this product yet."
echo "  Add it here — one line — and it can never go stale again."
exit 1

# --- 5. A genuinely manual step, if one exists -------------------------------
# Do not move it into a document. Put it here, so it cannot be forgotten:
#
#   read -p "Now click Deploy in the Cloudflare dashboard. It often needs a
#            SECOND click. Press enter once the dashboard says it is done. "
