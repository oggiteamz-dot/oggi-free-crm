#!/usr/bin/env bash
# =============================================================================
# rollback.sh — go back to the previous released version. READ BEFORE RUNNING.
# =============================================================================
set -euo pipefail

cat <<'WARN'

  BEFORE ROLLING BACK — rolling back restores CODE ONLY.

  It does NOT restore:
    - environment variables or secrets changed since
    - database migrations already applied
    - data already transformed by a migration
    - third-party settings (webhooks, DNS, payment configuration)

  THE QUESTION THAT DECIDES IT:
    Has a database migration run since the version you are rolling back to?

    YES -> a code rollback puts OLD code against a NEW database. That is
           frequently worse than the bug you are fleeing. Roll FORWARD instead.
    NO  -> a rollback is safe. Continue.

WARN

read -r -p "Has a migration run since the target version? (yes/no) " answer
if [ "$answer" != "no" ]; then
  echo
  echo "  Stopping. Roll forward with a fix instead of back."
  echo "  If you are certain anyway, run the deploy manually and take that"
  echo "  consequence deliberately rather than by accident."
  exit 1
fi

TARGET=${1:-$(git tag --sort=-creatordate | sed -n '2p')}
if [ -z "$TARGET" ]; then
  echo "No previous release tag found. Pass one explicitly: just rollback <tag>"
  exit 1
fi

echo "Rolling back to $TARGET"
git checkout "$TARGET"
bash scripts/deploy.sh
node scripts/verify_live.mjs

echo
echo "  Rolled back and verified against the live URL."
echo "  Now write WHY in DECISIONS.md, while you still remember. A rollback with"
echo "  no recorded reason becomes an unexplained version gap six months from now."
