# HOW TO CHECK MY APP
### One page. No jargon. Print it if you like.

---

## The only three things you ever need to say

### 1. `just census`
**Ask it:** "is what's on my computer the same as what's live?"

Run this FIRST, at the start of any session. If it says something is running on
the server that is not on your computer, **stop and fix that before anything
else** — otherwise everything you check today is measuring the wrong copy.

### 2. `just check`
**Ask it:** "is anything obviously broken?"

Takes under a minute. Comes back **GREEN** or **RED**.

- **GREEN** means nothing is broken in the ways that have burned you before.
  It does **not** mean the product works. Only step 3 and the Proof Cards mean that.
- **RED** lists exactly what is wrong, which file, and the fix. Copy those lines,
  paste them to Claude, say "fix these". That is the whole workflow.

### 3. `just verify-live`
**Ask it:** "does it actually work for a real customer, right now?"

This is the important one. It opens the real live site in a real browser, does
the real thing, reloads it, then **opens it again on a completely separate
device** and checks it is still there.

That last step is the one that catches the bug that hurt you most: a feature that
works perfectly on the phone that made it and has **never once worked** on
anybody else's.

---

## The three ticks — the four minutes only you can do

Before any feature is "done", open `proof-cards.html` on your phone and tick:

- ☐ **Works** — you saw what you expected
- ☐ **Survives reload** — close the page fully, open it again, still there
- ☐ **Survives another device** — different phone or a private window, still there

**If 1 and 2 pass but 3 fails, say this to Claude, word for word:**

> "It passes reload but fails on a second device — it's saving to the browser
> only, not to the server."

Claude will know exactly what that means and exactly where to look.

---

## What to say when something is wrong

Do not say "it's broken." Say these three things:

1. What I clicked
2. What I expected
3. What actually happened

Then add: **which page, which login, phone or computer.** That is a bug report.

---

## The one sentence to never accept

> **"Done, tested, working."**

Ask for: **the live link, the build number, and the second-device result.**

Everything else — pasted test output, a screenshot, a video recorded in the same
session that built it — you cannot tell real from fabricated, and neither can
anyone else. A live URL and a build number you can check yourself in three clicks,
you can.

---

## Red flags, in plain sight

You do not need to read code to spot these on any screen:

- Any word in `[brackets]`, `<angle brackets>` or `{{braces}}`
- Anything ALL-CAPS-WITH-HYPHENS like `PAY-LINK-HERE`
- The words `undefined`, `null`, `NaN`, `TODO`, `[object Object]`
- A button that does nothing when you tap it
- A form that submits and shows no message at all — not even an error

Any of these means the feature is not finished, whatever anyone says.
