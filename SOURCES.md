---
topic: sources-of-truth
status: current
---

# SOURCES OF TRUTH — one owning file per fact

Ten minutes of work that permanently ends the "two documents both claiming to be
authoritative and disagreeing" problem.

**The rule:** for each category of fact below, exactly ONE file owns it. Every
other document that mentions it must REFERENCE that file, never restate the fact.
The gate enforces this: at most one document may be marked `status: current` per
topic.

| Fact category | The file that owns it | Everyone else must |
|---|---|---|
| Pricing | `<file>` | link to it, never restate a number |
| What is built and what is not | `docs/FEATURE-LEDGER.generated.md` (generated) | never hand-write a feature list |
| What is deployed right now | the live `/__version` endpoint | never trust a dashboard message |
| Database shape | `supabase/migrations/` | never describe columns in prose |
| How to deploy | `justfile` | never write deploy steps in a document |
| Roles and permissions | the `role_permission` table | never describe permissions in prose |
| Open work | `TASKS.md` | never keep a second to-do list |
| Decisions made | `DECISIONS.md` (append-only) | never edit an old decision, only supersede it |

## Front matter every fact-stating document must carry

```
---
topic: pricing
status: current            # or: superseded
superseded_by: <the file that replaced this one>
---
```

**Superseding is a one-line status change, never a rewrite.** The old document
stays exactly as it was, marked superseded, so the history of what was believed
when remains readable.
