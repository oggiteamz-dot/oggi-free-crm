#!/usr/bin/env bash
# =============================================================================
# census.sh — STEP 0 OF EVERY SESSION. Run this before touching anything.
# =============================================================================
#
# THE FAILURE THIS PREVENTS
# -------------------------
# Four production functions — send-otp, verify-otp, save-intake-copy,
# save-target-nations — existed ONLY inside Supabase. There was no source code
# for them anywhere on disk. A rebuild from the project folder would have
# silently deleted lead OTP verification and both owner content tools, and
# nobody would have known until a customer complained.
#
# Fourteen more functions existed in no document at all.
#
# WHY IT RUNS FIRST
# -----------------
# Auditing the wrong copy is worse than not auditing. If the thing on your disk
# is not the thing that is live, every other check in the gate is measuring
# fiction. So this runs before everything, and the rest of the gate is meaningless
# until it is clean.
#
# WHAT IT COMPARES (three places truth can hide)
#   1. Server functions   vs  functions on disk        — BOTH directions
#   2. Live served bytes  vs  the committed build
#   3. The real database  vs  the migration files
#
# USAGE:  bash scripts/census.sh
# EXIT :  0 = clean, 1 = drift found (with the recovery command printed)
# =============================================================================

set -uo pipefail

# Run against the PRODUCT, not against wherever this script happens to live.
# Resolving ROOT from the script's own path meant that invoking it by its full
# path audited the toolkit folder and cheerfully reported "CENSUS CLEAN" about a
# product it had never looked at.
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT" || exit 2

if [ ! -f oggi-build.config.json ] && [ ! -d supabase ] && [ ! -d src ]; then
  echo
  echo "  This folder does not look like a product: no oggi-build.config.json,"
  echo "  no supabase/ and no src/ here ($ROOT)."
  echo "  Run the census from inside the product folder."
  echo
  exit 2
fi

CFG="oggi-build.config.json"
LIVE_URL=""
[ -f "$CFG" ] && LIVE_URL=$(python3 -c "import json;print(json.load(open('$CFG')).get('live_url',''))" 2>/dev/null)

PROBLEMS=0
line() { printf '%s\n' "----------------------------------------------------------------------"; }

echo
line
echo "  CENSUS — is what's on your computer the same as what's running live?"
line

# -----------------------------------------------------------------------------
# 1. SERVER FUNCTIONS vs DISK — both directions
# -----------------------------------------------------------------------------
echo
echo "1. Server functions vs your computer"

if command -v supabase >/dev/null 2>&1 && [ -d supabase/functions ]; then
  # Parse JSON, not the pretty table. The CLI prints a bordered table whose
  # column 2 is a border character or the function ID, so an awk '$2' parse
  # compared IDs against folder names and reported EVERY function as missing
  # from disk — a false DANGER on the first command of every session, which is
  # the fastest possible way to teach someone to ignore the census.
  if supabase functions list --output json >/tmp/_census_raw.json 2>/dev/null && command -v jq >/dev/null 2>&1; then
    jq -r '.[].slug // .[].name // empty' /tmp/_census_raw.json 2>/dev/null | sort -u > /tmp/_census_server.txt
  elif supabase functions list --output json >/tmp/_census_raw.json 2>/dev/null; then
    python3 -c "
import json,sys
try:
    data=json.load(open('/tmp/_census_raw.json'))
except Exception:
    sys.exit(0)
for f in data if isinstance(data,list) else []:
    v=f.get('slug') or f.get('name')
    if v: print(v)
" | sort -u > /tmp/_census_server.txt
  else
    : > /tmp/_census_server.txt
    echo "   NOTE: could not read the function list from Supabase in a reliable format."
    echo "         Skipping rather than guessing — a wrong answer here is worse than none."
  fi
  ls -1 supabase/functions 2>/dev/null | grep -v '^_' | sort -u > /tmp/_census_disk.txt

  ONLY_SERVER=$(comm -23 /tmp/_census_server.txt /tmp/_census_disk.txt)
  ONLY_DISK=$(comm -13 /tmp/_census_server.txt /tmp/_census_disk.txt)

  if [ -n "$ONLY_SERVER" ]; then
    PROBLEMS=$((PROBLEMS+1))
    COUNT=$(echo "$ONLY_SERVER" | wc -l | tr -d ' ')
    echo "   DANGER: $COUNT thing(s) are running on the server with NO source on your computer."
    echo "           If we rebuild now, these disappear and cannot be recovered."
    echo "$ONLY_SERVER" | sed 's/^/             - /'
    echo
    echo "   DO THIS FIRST, before any other work:"
    echo "$ONLY_SERVER" | sed 's/^/             supabase functions download /'
    echo "             git add supabase/functions && git commit -m 'recover server-only functions'"
  else
    echo "   OK: nothing is running on the server that is missing from your computer."
  fi

  if [ -n "$ONLY_DISK" ]; then
    COUNT=$(echo "$ONLY_DISK" | wc -l | tr -d ' ')
    echo "   NOTE: $COUNT thing(s) exist on your computer but were never deployed:"
    echo "$ONLY_DISK" | sed 's/^/             - /'
    echo "         (Not dangerous — but if you think these are live, they are not.)"
  fi
else
  echo "   SKIPPED: no supabase CLI or no supabase/functions folder."
  echo "            If this product has server functions, this check is the one that"
  echo "            stops a rebuild from deleting them. Worth setting up."
fi

# -----------------------------------------------------------------------------
# 2. LIVE BYTES vs COMMITTED BUILD
# -----------------------------------------------------------------------------
echo
echo "2. What the live site is actually serving"

if [ -n "$LIVE_URL" ]; then
  LIVE_VER=$(curl -s -H 'Cache-Control: no-store' -H 'Pragma: no-cache' \
             "${LIVE_URL%/}/__version" 2>/dev/null | tr -d '"\n ')
  LOCAL_SHA=$(git rev-parse HEAD 2>/dev/null | cut -c1-12)
  if [ -z "$LIVE_VER" ]; then
    echo "   UNKNOWN: ${LIVE_URL%/}/__version did not answer."
    echo "            Add a /__version endpoint that returns the build id. Without it,"
    echo "            'is the live site running my latest change?' is unanswerable, and"
    echo "            a dashboard saying 'deployed' is not proof."
  elif [ "${LIVE_VER:0:12}" = "$LOCAL_SHA" ]; then
    echo "   OK: live site is running your current version ($LOCAL_SHA)."
  else
    PROBLEMS=$((PROBLEMS+1))
    echo "   MISMATCH: live site is running '$LIVE_VER' but your computer is on '$LOCAL_SHA'."
    echo "             Whatever you test locally is NOT what your customers are using."
  fi
else
  echo "   SKIPPED: no live_url set in $CFG."
fi

# -----------------------------------------------------------------------------
# 3. DATABASE vs MIGRATION FILES
# -----------------------------------------------------------------------------
echo
echo "3. The real database vs your migration files"

if command -v supabase >/dev/null 2>&1; then
  DIFF=$(supabase db diff --linked 2>/dev/null | grep -v '^$' | head -30)
  if [ -z "$DIFF" ]; then
    echo "   OK: the database matches your migration files."
  else
    PROBLEMS=$((PROBLEMS+1))
    echo "   DRIFT: the live database does not match your migration files."
    echo "          Following your own runbook would produce a broken system — this is"
    echo "          exactly what caused the missing-columns 500 errors."
    echo "$DIFF" | sed 's/^/          /'
  fi
else
  echo "   SKIPPED: supabase CLI not available."
fi

# -----------------------------------------------------------------------------
echo
line
if [ "$PROBLEMS" -eq 0 ]; then
  echo "  CENSUS CLEAN — your computer, the server and the database agree."
  echo "  Safe to start work."
  line; echo
  exit 0
fi
echo "  CENSUS FOUND $PROBLEMS PROBLEM(S) — fix these BEFORE any other work."
echo "  Everything else you check today is measuring the wrong copy until this is clean."
line; echo
exit 1
