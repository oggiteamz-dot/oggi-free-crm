---
topic: spec
status: current
---

# <PRODUCT> — SPEC

**Status:** Draft
**Approved by:** _(type APPROVED and the date here — nothing gets built until you do)_

> This is one page on purpose. The research is unambiguous: of ten real failures
> in past builds, ONE was caused by bad planning. Eight were caused by nobody
> checking the live product. A twelve-page spec would move effort to the wrong
> half of the problem. Everything here earns its place.

---

## 1. In one sentence
<What it is and who it is for.>

## 2. The job it is hired to do
<What the user is trying to get done. What they do today instead.>

## 3. Done looks like
<The one measurable thing that makes this a success in 90 days.>

## 4. Who touches it
| Role | What they do | What they must NEVER be able to do |
|---|---|---|
| | | |

## 5. What it must do
Written so each line is checkable by a person, not just by a developer.

| ID | The system must… | How you personally check it (under 5 min) |
|---|---|---|
| R-01 | | |
| R-02 | | |

## 6. What must survive
Anything listed here must appear on the persistence allow-list AND be proven on a
second device. This is the single most expensive failure class in past builds:
a feature that works until reload and never once works on anyone else's phone.

| What | Where it is stored | Proven on a second device? |
|---|---|---|
| | | |

## 7. Who gets told, and when
If anything here is blank, someone will wait forever for a message that never
arrives — which has already happened, silently, for weeks.

| Event | Who must be told | By what channel | Goes through the outbox? |
|---|---|---|---|
| | | | Yes / No |

## 8. What can be edited later without a developer
Every string, price, link and toggle a non-developer will ever want to change.
Anything not on this list will require a code change and a deploy — decide that
NOW, not at 2am when a price is wrong.

| Thing | Who may edit it | Who may publish it |
|---|---|---|
| | | |

## 9. NO-GOS — at least eight
The most useful section in the document. Each line prevents an argument later.

1. It will NOT …
2. It will NOT …
3. …

## 10. Appetite
- **Time:** <fixed>
- **Money:** <fixed>
- **When these run out we cut scope, not quality.** What gets cut first: <…>

## 11. How it could fail (pre-mortem)
| It fails because… | We prevent it by… |
|---|---|
| | |
