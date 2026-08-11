---
topic: runbook
status: current
---

# RUNBOOK — <Product>

Last rehearsed: never — PASS pending

## Read this first

**The steps are not in this document.** They are in the `justfile`, because a
document describing steps goes stale the moment the steps change, and a program
that performs them cannot: if it's wrong, it fails today rather than during an
outage three weeks from now.

That is not a stylistic preference. A previous runbook in this estate was
timestamped Jul 5; six of the twelve things it governed changed after it; nobody
revised it; and deploying by it returned a 500 error because seven required
database columns appeared in no step anywhere.

## What to run

| To do this | Run |
|---|---|
| Check my computer matches what's live | `just census` |
| Check nothing is broken | `just check` |
| Put it live | `just deploy` (refuses if the checks didn't pass) |
| Prove it actually went live | `just verify-live` |
| Go back a version | `just rollback` |
| Rebuild everything from scratch (monthly) | `just drill-rebuild` |
| Prove the backup works (monthly) | `just drill-restore` |

## This product's specifics

- **Live URL:** 
- **Where the front end is hosted:** 
- **Supabase project / schema:** 
- **Anything genuinely manual:** _(if there is a manual step, it belongs INSIDE
  `scripts/deploy.sh` as a prompt, not written here where it can be forgotten)_

## The rehearsal

`just drill-rebuild` clones the project into an empty folder and rebuilds it
using only what's committed. If it fails, this runbook is broken — which is far
better learned on a quiet Tuesday than during an outage.

Run it monthly. It stamps the date at the top of this file when it passes.
**A stamp older than 30 days, or older than the last database change, means the
runbook can no longer be trusted.**
