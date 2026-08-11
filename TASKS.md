---
topic: tasks
status: current
---

# TASKS — <Product>

The single to-do list for this product. **Do not keep a second one anywhere.**

Every task is a **vertical slice**: one whole feature, cut through every layer —
the screen, saving it, reading it back, deployed — before the next one starts.
Never "build all the screens", then "wire up saving". That order looks like fast
progress and produces a beautiful app that doesn't save.

## Phase 1 — Setup (once)
- [ ] T001 · repo created, toolkit copied, `.gitignore` in place, first commit
- [ ] T002 · `oggi-build.config.json` filled in — live URL, source folders, save list
- [ ] T003 · `just adopt` if this product already existed
- [ ] T004 · Claude Project created, the five knowledge files attached

## Phase 2 — FOUNDATION · BLOCKING · nothing else starts until this is done
- [ ] T010 · content + roles installed (`01_content_and_roles.sql` as a migration)
- [ ] T011 · errors + outbox + heartbeats installed (`02_...sql` as a migration)
- [ ] T012 · `/__version` and `/health` live
- [ ] T013 · `error-sink.js` loaded before any app code
- [ ] T014 · admin console: Content · Users · Roles · Error Inbox
- [ ] T015 · every existing string extracted into the content table
- [ ] T016 · `deploy.sh` filled in for this product — first real deploy works
- [ ] T017 · `verify.journeys.json` written (payment, sign-in, main action)

## Phase 3 — Blockout
- [ ] T020 · every screen as a grey box, navigation wired, deployed
- [ ] T021 · `SCREENMAP.md` written, `blockout_check.py` clean
- [ ] T022 · **walked on a phone, once as each role** — signed off

## Phase 4 — Features, one at a time
Each task names its feature ID, and is not done until its Proof Card has all three ticks.

- [ ] T030 · FEAT-0001 · <feature>
      Independent test: <what you personally do to check it>
      Checkpoint: gate green · nothing removed · proven on a second device

## Phase 5 — Ship
- [ ] T090 · all Golden Paths pass
- [ ] T091 · `just drill-rebuild` passes
- [ ] T092 · acceptance script executed by the client on the live URL
