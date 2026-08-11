---
topic: decisions
status: current
---

# DECISIONS — <Product>

Append-only. **Never edit or delete an entry.** When a decision changes, add a new
one that supersedes the old — the record of what was believed when is the whole
value, and rewriting history destroys it.

## Format

```
## D-001 — <the decision, in one line>
Date: 2026-08-08 · Decided by: Hadi
Status: current            (or: superseded by D-014)

What we chose:
What else we considered:
Why this one:
What would make us change our mind:
```

---

## D-001 — Example: one Supabase project, a schema per product
Date: 2026-08-08 · Decided by: Hadi
Status: current

**What we chose:** every new product gets its own schema inside the single
existing Supabase project.

**What else we considered:** a separate Supabase project per product.

**Why this one:** Pro billing is ~$25/month per organisation plus ~$10/month per
project, and a Pro project cannot be paused. Fifteen products as projects is
~$165/month; as schemas it stays $25.

**What would make us change our mind:** a client contractually requiring their
data in an isolated project, or one product outgrowing shared compute.
