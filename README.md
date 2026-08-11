# OGGI Free CRM

A permanently free, mobile-first CRM for Lebanese and MENA professionals and small
wholesalers, in which WhatsApp is a first-class channel rather than an add-on.

**Status: specified, not yet built.** This repository currently contains the
specification, the scope contract, the feature definitions and the quality toolkit that
will govern the build. `src/` holds the modular scaffold and no features yet. Nothing
here claims to be working software, and the build has not started.

That is deliberate. The rest of this file explains why the specification came first and
what will enforce it.

---

## If you are reviewing this, read in this order

| # | File | What it answers |
|---|---|---|
| 1 | [`docs/PRD.md`](docs/PRD.md) | What this is, who it is for, what it costs to run, and where the plan could be wrong |
| 2 | [`SPEC.md`](SPEC.md) | The one page that gets checked against the finished product |
| 3 | [`docs/FEATURE-MATRIX.csv`](docs/FEATURE-MATRIX.csv) | The agreed scope — and every deliberate omission, with its reason |
| 4 | [`features/`](features/) | One file per feature: the steps, what must survive, and the ways it can fail |
| 5 | [`docs/RESEARCH-2026-08-11.md`](docs/RESEARCH-2026-08-11.md) | Every factual claim, its source, and the places the evidence ran out |
| 6 | [`GOTCHAS.md`](GOTCHAS.md) | Known problems, including unfixed security debt, stated plainly |

Roughly forty minutes end to end. §11 and §13 of the PRD are where the real arguments are.

---

## What is in here

```
src/            the application — modular ES modules, no build step
                core/ is shared; features/ is one folder per feature
features/       one YAML file per feature: steps, persistence, failure modes
docs/           PRD, research appendix, feature matrix, generated inventory
scripts/        the quality gate — 13 checks, ~6 seconds, plain Python
sql/            roles, the editable-content layer, the outbox, diagnostics
regression/     journeys that must keep working
SPEC.md         the one-page contract
SCREENMAP.md    every screen and who can reach it, checked mechanically
GOTCHAS.md      known problems, including the unfixed ones
```

## Running it

No build step, no dependencies. Static files plus Supabase.

```bash
cd src && python3 -m http.server 8080
# then open http://localhost:8080
```

## Run the checks

```bash
python3 scripts/inventory.py     # regenerate the feature inventory from the source
python3 scripts/check.py         # the gate
```

Thirteen checks, about six seconds, Python 3 only. Each prints the file, the line and the
remedy in plain language. Every one exists because of a specific defect that reached
production in this estate; the reasoning is in the comment header of each script.

The ones worth looking at first, because they are the unusual ones:

- **`filesize`** — refuses any source file over 300 lines. The estate's most expensive
  structural failure was a single 464 KB, 6,249-line HTML file that editors silently
  truncated on save, five separate times, each incident killing every login and button.
  This check is the fix, and it is a gate rather than a guideline.
- **`inventory_fresh`** — the feature ledger is generated from source and CI fails if the
  committed copy is stale. A previously hand-maintained ledger reached the point where
  294 of 500 functions were undocumented and every line number was wrong.
- **`persistence`** — anything the product saves must be declared on an allow-list and
  proven on a second device. A feature that works until reload and never works on anyone
  else's phone is the single most expensive failure class here.
- **`completeness`** — reads `docs/FEATURE-MATRIX.csv` and fails the build if an agreed
  feature has no feature file, or if a skipped one has no stated reason. It catches the
  thing every other check is blind to: something that was never built at all.
- **`silent_catch`** — a catch block that discards the error. The estate's most expensive
  individual defect was of this class: a notification path that silently never ran,
  undetected for weeks.

## The build loop

One feature at a time, with a hard work-in-progress limit. `just start FEAT-0001` refuses
while anything is still awaiting the owner's test. When a feature is built and deployed,
the owner tests it against the three Proof Cards and either approves — which locks it onto
a list that later changes cannot silently break — or rejects it with a reason.

```bash
just board            # what is built, what is waiting on you, what is next
just start FEAT-0001
just built FEAT-0001 --url https://...
just approve FEAT-0001
```

Removal detection is the other half: `just diff` reports what a change **removed**, not
just what it added, and a removal must be explicitly approved in `REMOVALS-APPROVED.md`
before the gate will pass.

## What is deliberately not here

The specification names twenty-four scope decisions and eight of them are refusals — no
recurring tasks, no bulk merge in v1, no fuzzy name matching, no custom-object builder,
no two-way Lead Pool sync, no SMS anywhere, no invoicing, no reporting dashboard in v1.
Each has a written reason in `docs/FEATURE-MATRIX.csv`. "We didn't get to it" is not
accepted as a reason by the completeness check.

## The known open question

The product's differentiator is native two-way WhatsApp on a free tier. The architecture
is settled — Meta Tech Provider with Embedded Signup, each business connecting its own
WhatsApp Business Account so Meta bills them directly and OGGI carries no messaging cost.

**What is not settled: whether Meta's billing accepts Lebanese-issued cards.** Stripe does
not serve Lebanon-registered businesses at all, and this could not be verified from
documentation. `FEAT-0014` is marked `blocked` until one real client is onboarded
end to end. The deep-link version (`FEAT-0007`) ships regardless and does not depend on it.

---

*Built and maintained with the OGGI Build System. If the code and the specification
disagree, the code is wrong until a decision is recorded in `DECISIONS.md` saying
otherwise.*
