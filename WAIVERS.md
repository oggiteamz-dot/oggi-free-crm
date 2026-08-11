# WAIVERS — the only sanctioned way to skip a gate

A gate is skipped by writing a line here. Not by disabling it, not by adding an
exclusion, not by saying "this one time".

**Why it works this way:** the highest-probability way this system dies is not
someone skipping a check — it is someone quietly weakening one. An exclusion in a
config file looks like maintenance. A dated line here looks like what it is.

## The format — all five parts required

```
2026-08-08 | GATE: live-verification | PRODUCT: wholesale
  SKIPPED BECAUSE: client demo in 40 minutes, Cloudflare propagation is stuck
  THIS REOPENS: shipping a build that is not actually live (failure class #7)
  WILL BE CLOSED BY: 2026-08-09, before any customer traffic
  APPROVED BY: Hadi
```

An empty or vague reason is not a waiver. "To move faster" is not a reason —
it is the thing the gate exists to prevent.

## Standing rule

**More than three open waivers means the gates are wrong, not the work.**
Either they are too slow, too noisy, or checking the wrong things. Fix the gates.
A gate routinely waived is a gate that will be deleted.

---

## Open waivers

_(none)_

## Closed waivers

_(none)_
