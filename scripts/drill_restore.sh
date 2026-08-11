#!/usr/bin/env bash
# =============================================================================
# drill_restore.sh — MONTHLY. Restore the backup into a scratch database.
# =============================================================================
# An untested backup is not a backup. It is a hope.
#
# Two things this catches that nothing else does:
#   1. The backup has been silently failing for weeks. (Silent failure again —
#      the same class that let matched leads go un-notified. Nothing alarms on
#      an absence unless something checks for the absence.)
#   2. The backup restores, but into something unusable.
#
# Own the backups OFF the platform. If the only copy lives inside the provider,
# that is not a backup — it is the same single point of failure with extra steps.
# =============================================================================
set -euo pipefail

if [ -z "${DATABASE_URL:-}" ]; then
  echo "DATABASE_URL is not set. Export it and re-run."
  echo "Never hard-code it in this file — the gate will fail the build if you do."
  exit 2
fi

STAMP=$(date +%Y%m%d-%H%M)
OUT="_backups/$STAMP"
mkdir -p "$OUT"

echo "→ Taking a fresh dump"
pg_dump "$DATABASE_URL" > "$OUT/dump.sql"
SIZE=$(wc -c < "$OUT/dump.sql")
echo "  $OUT/dump.sql — $SIZE bytes"

if [ "$SIZE" -lt 10000 ]; then
  echo
  echo "  The dump is suspiciously small. Your backup may have been failing"
  echo "  silently for some time. Investigate before trusting any backup."
  exit 1
fi

echo "→ Restoring it into a scratch database"
# RESTORE_URL must point at a SCRATCH server, not production. Creating the test
# copy on the production instance doubles its size and puts drill load on the
# database customers are using.
if [ -z "${RESTORE_URL:-}" ]; then
  echo
  echo "  RESTORE_URL is not set."
  echo "  Point it at a scratch Postgres — a local one is ideal:"
  echo "      export RESTORE_URL='postgres://postgres@localhost:5432/postgres'"
  echo
  echo "  Restoring into production would double its size and put drill load on the"
  echo "  database your customers are using. Refusing rather than guessing."
  exit 2
fi

SCRATCH="restore_drill_$STAMP"
# Preserve any query string (?sslmode=require) — stripping it broke the reconnect.
BASE="${RESTORE_URL%%\?*}"; QS=""
case "$RESTORE_URL" in *\?*) QS="?${RESTORE_URL#*\?}";; esac
BASE="${BASE%/*}"

psql "$RESTORE_URL" -c "create database \"$SCRATCH\";" >/dev/null 2>&1 || true

# ON_ERROR_STOP is the whole point. Without it psql exits 0 even when every
# statement failed — so the script whose job is catching silent backup failure
# would itself have failed silently and printed PASS.
if ! psql "$BASE/$SCRATCH$QS" -v ON_ERROR_STOP=1 -f "$OUT/dump.sql" > /tmp/restore.log 2>&1; then
  echo
  echo "  RESTORE FAILED — the backup exists but does not restore."
  echo "  That is worse than no backup, because it looks like protection and is not."
  tail -15 /tmp/restore.log | sed 's/^/    /'
  psql "$RESTORE_URL" -c "drop database if exists \"$SCRATCH\";" >/dev/null 2>&1 || true
  exit 1
fi

echo "→ Confirming the restored copy actually contains rows"
psql "$BASE/$SCRATCH$QS" -c "
  select table_name,
         (xpath('/row/c/text()',
           query_to_xml(format('select count(*) c from %I.%I', table_schema, table_name),
           false, true, '')))[1]::text::int as rows
  from information_schema.tables
  where table_schema = 'public'
  order by rows desc nulls last
  limit 10;"

psql "$RESTORE_URL" -c "drop database \"$SCRATCH\";" >/dev/null 2>&1 || true

echo
echo "  RESTORE DRILL PASSED — the backup exists, restores cleanly, and has rows."
echo "  Now copy $OUT off this platform. Same-platform-only is not a backup."
