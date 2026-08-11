---
topic: prd
status: current
version: 1.0
date: 2026-08-11
---

# OGGI Free CRM — Product Requirements Document

**Version 1.0 · 11 August 2026**
**Owner:** Hadi Hamza (OGGI)
**Status:** For review. Not yet approved for build.

---

## Read this first

This document is written to be argued with. Every number in it has a source, every
scope decision has a reason, and the places where the evidence ran out are marked
as such rather than smoothed over. Three claims in the previous research pass turned
out to be wrong when re-checked on 11 August 2026; they are corrected below and the
corrections are called out explicitly, because a reviewer who finds a stale claim
himself will reasonably discount everything else.

**The assumption this document rests on, stated up front so it can be rejected:**

> OGGI Free CRM is given away free, permanently, to the professionals and wholesalers
> OGGI already works with. It is not a revenue product. It is structurally free
> because Lead Pool and Wholesale are the revenue engines, and a client whose entire
> client book lives inside an OGGI product converts better on both.

If that assumption is wrong, sections 3, 4 and 12 change materially and the document
needs a revision before build. **Confirm or correct it before approving.**

---

## 1. In one sentence

A free, permanently free, mobile-first CRM for Lebanese and MENA professionals and
small wholesalers, in which WhatsApp is a first-class channel rather than an add-on.

## 2. The job it is hired to do

A wholesaler in Beirut runs their entire client book through WhatsApp and a phone
contact list. They know who owes them money and who has gone quiet only because they
remember. When a rep leaves, the relationships leave with them, because the history
lived in that rep's phone.

They do not want "a CRM." They want to stop losing customers they simply forgot to
follow up with, and they want the record of a relationship to survive a staff change.

**What they do today instead:** WhatsApp plus memory. Sometimes an Excel sheet.
Occasionally a CRM trial that was abandoned within a month because setup took days
and the data lived somewhere their phone couldn't reach.

## 3. Done looks like

**Ninety days after launch, 30 OGGI clients have logged into the CRM in the last
7 days and have more than 50 contacts each.**

One number, deliberately. Not signups — *returning* users with real data in it. A
CRM with contacts in it that nobody opens is a failure that looks like a success on
a signup chart.

**Secondary, watched but not the target:** the number of those users who have
connected WhatsApp. That is the differentiator working or not working.

## 4. Who touches it

| Role | What they do | What they must NEVER be able to do |
|---|---|---|
| **Owner** | Everything. Billing, team, deletion, export, settings. | Be removed while they are the last owner. |
| **Manager** | Sees all contacts and deals across the team. Assigns work. Invites Reps. | Change billing, delete the workspace, remove an Owner. |
| **Rep** | Sees and edits **only their own** contacts and deals. Logs activity. | See another Rep's contacts. Open Settings. Export the full database. |
| **View-only** | Reads everything they are scoped to. For an accountant or a partner. | Create, edit or delete anything. Send a WhatsApp message. |
| **Quality Control** | Reviews and approves text changes before they go live. | Edit content directly — approval and authorship are separate people. |
| **Writer / Copywriter** | Edits any user-visible text and submits it for approval. | Publish their own edit. Touch data, contacts or settings. |

The last two roles come from the OGGI Build System's content layer: every user-visible
string in the product is a database row, editable without a developer and without a
deploy, with authorship and publishing separated so that one person's typo cannot
reach customers unreviewed. This is not aspirational — the SQL is in `sql/01_content_and_roles.sql`
and the separation is enforced by a `SECURITY DEFINER` publish function, not by convention.

## 5. What it must do

Every line is written so a non-developer can check it in under five minutes. That is
the point: of ten real failures in previous OGGI builds, one was caused by bad
planning and eight by nobody checking the live product.

| ID | The system must… | How you personally check it |
|---|---|---|
| R-01 | Let a pro add a contact with a name, phone and WhatsApp number, and show it at the top of the list | Add one. Look at the list. |
| R-02 | Warn — never block — when a phone or email already exists, and offer to open the existing record | Add the same number twice. |
| R-03 | Treat `03 123 456`, `+961 3 123 456` and `00961 3 123 456` as the same number | Add one, then try the others. |
| R-04 | Filter the contact list as you type, on name or number | Type three letters. |
| R-05 | Export every contact and every field to CSV, with no paywall, ever | Tap Export. Open the file. |
| R-06 | Import a CSV, matching on normalised phone/email, defaulting to skip-existing | Import the same file twice. Count should not double. |
| R-07 | Let a user undo a bulk delete or an entire import as one operation | Delete 5, tap Undo. |
| R-08 | Keep deleted records recoverable for 30 days | Delete one. Find it in the bin. |
| R-09 | Show a pipeline and let a deal be dragged between stages, surviving a full app restart | Drag it. Force-quit. Reopen. |
| R-10 | Show every call, message and note against a contact, newest first | Open a contact. |
| R-11 | Let a pro message a contact on WhatsApp from the contact record and log that it happened | Tap WhatsApp. Send. Return. |
| R-12 | Show what is due today, and mark anything late as overdue | Add a task dated yesterday. |
| R-13 | Show a "Gone quiet" list of contacts with no activity in N days, N default 30 | Wait, or backdate one. |
| R-14 | Let an Owner invite a Rep who then sees only their own contacts | Invite. Sign in on a second phone. |
| R-15 | Be usable within one minute of signup, with a pipeline already populated | Sign up fresh. |
| R-16 | Install to a phone home screen as a real app | Add to Home Screen. Open it offline. |
| R-17 | Let a Writer edit any user-visible text, and require a different person to publish it | Change a button label. Try to publish it yourself. |

## 6. What must survive

Anything here must appear on the persistence allow-list (`src/core/store.js`, `DATA_KEYS`)
**and** be proven on a second device before the feature is approved.

This is the single most expensive failure class in OGGI's history: a feature that
works until reload and never once works on anyone else's phone. `localStorage` is a
cache, never the record.

| What | Where it is stored | Proven on a second device? |
|---|---|---|
| Contacts | Supabase `crm.contacts` | Required |
| Companies | Supabase `crm.companies` | Required |
| Deals and their stage | Supabase `crm.deals` | Required |
| Activity timeline | Supabase `crm.activities` | Required |
| WhatsApp messages | Supabase `crm.messages` | Required |
| Tasks | Supabase `crm.tasks` | Required |
| Users and roles | Supabase `auth.users` + `crm.user_roles` | Required |
| Editable text | Supabase `content_string` | Required |
| Soft-deleted records | `deleted_at` on each table, 30-day retention | Required |
| Operation log (for undo) | Supabase `crm.operations` | Required |

## 7. Who gets told, and when

If any row here is blank, someone waits forever for a message that never arrives.
That has already happened in this estate, silently, for weeks.

| Event | Who must be told | Channel | Through the outbox? |
|---|---|---|---|
| A teammate is invited | The invitee | Email, WhatsApp fallback | **Yes** |
| A task becomes overdue | The task owner | In-app badge; push if PWA installed | No — computed on read |
| A customer replies on WhatsApp | The assigned pro | Push + in-app | **Yes** |
| A contact goes quiet past its threshold | The assigned pro | In-app "Gone quiet" list | No — computed on read |
| A text change is submitted for approval | Quality Control | Email | **Yes** |
| A bulk delete of more than 25 records | The Owner | Email receipt | **Yes** |

"Through the outbox" means a transactional-outbox row plus a heartbeat, so that a
notification path that silently stops running is detected within minutes rather than
weeks. Absent-signal detection is the specific mechanism; the schema is in
`sql/02_errors_and_outbox.sql`.

## 8. What can be edited later without a developer

Everything on this list is a `content_string` row. Anything **not** on this list
requires a code change and a deploy — decide that now, not at 2am when a price is wrong.

| Thing | Who may edit | Who may publish |
|---|---|---|
| Every button label, heading, empty-state and error message | Writer, Copywriter | Quality Control, Owner |
| Pipeline stage names | Owner, Manager | Owner |
| The "Gone quiet" day threshold | Owner | Owner |
| WhatsApp message templates | Copywriter | Quality Control + Meta approval |
| Role descriptions on the invite screen | Writer | Quality Control |
| Onboarding welcome and first-step text | Writer, Copywriter | Quality Control |

## 9. NO-GOS

The most useful section in this document. Each line prevents an argument later.

1. It will **NOT** have a paid tier on any core relationship-management function.
   If a paid tier ever exists it is adjacent capacity — high-volume WhatsApp
   automation, AI drafting, advanced reporting — never contacts, deals, tasks or export.
2. It will **NOT** cap the number of users, contacts or deals on the free tier.
   Zoho's free tier caps at 5,000 records; Bitrix24's at 1–2 users. That resentment
   is the thing being avoided.
3. It will **NOT** gate CSV export behind anything, ever, including account expiry.
4. It will **NOT** be built on an unofficial WhatsApp library (Baileys, whatsapp-web.js,
   or any linked-device puppeteer). See §11 — the ban risk lands on the client's
   primary business number, not on us.
5. It will **NOT** send WhatsApp from a shared OGGI-owned number on behalf of clients.
   Each business connects its own WhatsApp Business Account via Meta Embedded Signup.
6. It will **NOT** do proposals, contracts, e-signature or invoicing in v1. That is
   Lead Pool's territory and the schemas are not stable enough to merge.
7. It will **NOT** be a custom-object platform. Custom *fields* yes; a Salesforce-style
   object builder no. Inventory customisation belongs in Wholesale Apps.
8. It will **NOT** two-way sync with Lead Pool. One direction only: a Lead Pool deal
   marked Won creates or updates a contact here. Two-way sync means conflict
   resolution, and conflict resolution means silent data loss.
9. It will **NOT** ship an AI feature without an explicit off-switch.
10. It will **NOT** hard-delete on a user action. Everything is soft-deleted with a
    30-day window, because there is no support team to restore from backups.
11. It will **NOT** ship as a single HTML file. Hard limit: 300 lines per file,
    enforced by the gate, refusing the commit. This is the specific failure that
    has cost this estate the most.
12. It will **NOT** rely on Lebanese A2P SMS for anything — not OTP, not notification.
    It has been broken on both carriers since at least February 2025.

## 10. Appetite

- **Time:** 6 working sessions to a usable v1 (features FEAT-0001 through FEAT-0010).
  A further 4 for the WhatsApp two-way integration.
- **Money:** $0 recurring for the CRM's own WhatsApp usage — see §11. Supabase and
  Cloudflare on existing OGGI plans.
- **When these run out we cut scope, not quality.** Cut order, first to last:
  the automation rule, companies, then the pipeline itself. **Never cut:** export,
  soft delete, the second-device proof, or the 300-line limit.

## 11. WhatsApp — the differentiator, examined honestly

This section exists because the entire product thesis rests on it, and because the
thesis as originally written is no longer true.

### 11.1 The correction

The 3 August research concluded that *"nobody treats WhatsApp as a first-class CRM
channel."* Re-checked on 11 August 2026, **that is false.**

- **Pipedrive shipped native two-way WhatsApp on 26 May 2026** — inside the CRM,
  connected directly to Meta with no third-party BSP, included in the plan rather than
  sold as an add-on. Open beta, Growth plan and above.
  ([Businesswire, 26 May 2026](https://www.businesswire.com/news/home/20260526056366/en/Pipedrive-Bridges-the-Sales-to-Delivery-Gap-With-New-Project-Management-and-Messaging-Tools);
  [Pipedrive KB](https://support.pipedrive.com/en/article/whatsapp-integration-setup?category=integrations))
- **HubSpot** has a native WhatsApp channel in the conversations inbox, gated to
  Marketing or Service Hub Professional and above.
  ([HubSpot KB](https://knowledge.hubspot.com/inbox/connect-whatsapp-to-the-conversations-inbox))
- **Zoho CRM** ships it on paid editions; **Freshsales** from Pro ($47/user/mo);
  **Folk** claims native two-way included on all plans — though the only sources for
  that are Folk's own marketing pages, so treat it as unconfirmed.
- **Bitrix24, monday CRM, Attio and Salesforce Starter** have no native
  implementation — third-party connectors only.

### 11.2 The claim that survives

> **No CRM in the competitive set offers native two-way WhatsApp on a free tier.**

Every native implementation is behind a paid plan: Pipedrive Growth ($39–49/seat),
HubSpot Professional ($100/seat + $1,500 onboarding), Freshsales Pro ($47/user),
Zoho paid editions, Folk (no free tier at all). The three products with genuinely
usable free tiers — Zoho, Bitrix24, Attio — either paywall WhatsApp or lack it.

**This is a timing advantage, not a structural moat.** Pipedrive's move suggests
native WhatsApp is becoming table stakes at the paid tier. The PRD assumes the gap
closes within 18 months and does not plan around it lasting.

The genuinely durable advantages are the other two: **free with no cap on a product
that does not need to monetise itself**, and **one login connected to Lead Pool and
Wholesale**, which no external competitor can offer at any price.

### 11.3 What it actually costs

Meta moved from conversation-based to **per-message pricing on 1 July 2025**
([Meta pricing docs](https://developers.facebook.com/documentation/business-messaging/whatsapp/pricing)).
Lebanon bills under the "Rest of Middle East" band. Rates effective 1 July 2026:

| Category | Rate per message |
|---|---|
| Marketing | $0.0392 |
| Utility | $0.0105 |
| Authentication | $0.0105 |
| **Service** | **Free** |

Two changes make this economically trivial for a conversational CRM:

1. **Since 1 November 2024, all service conversations are free, with no monthly cap.**
   The widely-repeated "1,000 free conversations per month" figure is obsolete.
2. **Since 1 July 2025, utility templates delivered inside an open 24-hour window
   are also free.**

A CRM whose dominant pattern is *customer messages the business, business replies from
the contact record* operates almost entirely in the free tier.

**At 50 businesses each sending 200 messages a month (10,000 messages):**

| Scenario | Billable | Monthly, all 50 | Per business |
|---|---|---|---|
| Realistic — 70% in-window replies (free), 30% templates | 3,000 | **≈ $60** | **≈ $1.20** |
| All outside window, utility templates | 10,000 | ≈ $105 | ≈ $2.10 |
| Worst case, all marketing templates | 10,000 | ≈ $392 | ≈ $7.84 |

**In the recommended architecture, OGGI pays $0 of this.** See §11.4.

*Caveat for the reviewer:* published rate tables disagree — SetSmart lists UAE
marketing at $0.0816 against SleekFlow's $0.0574, and HighLevel's July 2026 changelog
gives Rest of Middle East as $0.0358/$0.0096. Meta warns rates may change quarterly.
**Do not hard-code rates. Fetch and re-check.**

### 11.4 The architecture, and why the alternatives are rejected

**Recommended: Meta Tech Provider + Embedded Signup + Coexistence.**

- **Tech Provider** (not Solution Partner): no Meta credit line, so each client business
  attaches its own payment method and **Meta bills them directly**. OGGI bills nothing
  for messaging and carries no messaging cost. Requires App Review for Advanced access
  plus `whatsapp_business_management` and `whatsapp_business_messaging`.
  ([Meta Solution Providers](https://developers.facebook.com/documentation/business-messaging/whatsapp/solution-providers/overview))
- **Embedded Signup**: the onboarding widget launched from our own app. The client
  creates or selects **their own** WhatsApp Business Account and verifies **their own**
  number. They own the asset; we are authorised to act on it.
  ([Meta Embedded Signup](https://developers.facebook.com/documentation/business-messaging/whatsapp/embedded-signup/overview/))
- **Coexistence** — global since May 2026 — lets the business **keep using the WhatsApp
  Business App on its existing number and phone** while the API runs alongside, with up
  to 6 months of 1:1 history imported. This removes the objection that kills most
  WhatsApp API sales to small businesses: *"you want me to give up my number?"*
  Trade-offs: Broadcast Lists, Disappearing Messages, View Once and Live Location are
  permanently disabled for 1:1 chats afterwards, and group chats do not sync.
  ([Chakra, Jun 2026](https://chakrahq.com/article/whatsapp-business-app-api-coexistence-202/))

**Rejected — one shared OGGI number relaying for many businesses.** The display name
must reflect the business the customer is talking to; the WhatsApp Business Terms
prohibit misrepresenting affiliation and prohibit making the service available over a
network for use by multiple parties outside authorised tools. Operationally, one bad
tenant's quality downgrade would take messaging down for every client at once.

**Rejected — unofficial libraries (Baileys, whatsapp-web.js, WAHA, Evolution API).**
The WhatsApp Business Terms forbid developing or using applications that interact with
the service without prior written consent, and forbid reverse engineering. Detection is
pattern-based and bans are reported as a matter of when, not if. The consequence does
not land on us: it takes out **the client's primary business number** — the one on their
invoices, van and shopfront. A banned number also cannot later be migrated to the
official API until the ban is appealed. Since the official route costs OGGI nothing,
there is no cost argument for the risk.

### 11.5 The 24-hour window, and what it forces the UI to do

A customer message opens a **24-hour service window**, resetting on each new inbound
message. While it is open, any free-form message is allowed and free. While it is
closed, free-form messages are **rejected by the API** — only pre-approved templates
may be sent, and they are charged.

Three consequences that must be built, not documented:

1. The contact record shows a **live window countdown**. A user who cannot see the
   window will write a message the API refuses.
2. The composer **switches mode automatically** — free text when open, template picker
   when closed.
3. The template picker **shows the cost of the selected category before sending**.

### 11.6 The open risk

**Whether Meta's billing system accepts Lebanese-issued cards is unverified.** Stripe
does not support Lebanon-registered businesses at all, and founders routinely
incorporate a US LLC or UAE entity to work around it
([Voxire, Apr 2026](https://voxire.com/blog/payment-gateways-lebanon-ecommerce-2026/)).
Meta's own acceptance could not be confirmed from documentation.

**Action before the WhatsApp features are approved for build: onboard one real client
end-to-end and confirm the card attaches.** If it does not, the fallback is that OGGI
becomes a Solution Partner with a credit line and bills clients in local rails — which
changes §11.4 and adds cost.

Lebanon is **not** on Meta's restricted-country list. Business verification accepts
Arabic and French documents. Neither of those was the risk.

### 11.7 Delivery order

- **FEAT-0007 (v1, ships first):** a `wa.me` deep link from the contact record with a
  pre-filled message, plus a one-tap "log this conversation" note. Zero cost, zero
  approval, ships in a day. It is honest, and it is what most MENA CRMs actually do.
  It does **not** capture inbound.
- **FEAT-0014 (v2, the real wedge):** Embedded Signup, two-way sync, window countdown,
  templates.

Shipping the deep link first means the contact record is useful on day one and the
architecture question does not block the rest of the product.

## 12. Competitive position

Verified 11 August 2026. **Six claims from the 3 August research were stale and are
corrected here.** Each figure is from the vendor's own pricing page on that date.

| Product | Free tier | Entry paid price | Native two-way WhatsApp |
|---|---|---|---|
| **Dubsado** | None (21-day trial, no card) | $335/yr Starter, $525/yr Premier | No evidence |
| **HoneyBook** | None | $36/mo Starter (Feb-2025 rise of 89.5%) | No evidence |
| **Bonsai** | None (7-day trial, no card) | $15/user/mo | No evidence |
| **17hats** | **Yes — new** (4 invoices/quarter) | $60/mo flat | No evidence |
| **Zoho CRM** | 3 users, **5,000 records**, 10 rules (5 active) | $14/user/mo | Paid editions |
| **Bitrix24** | 1–2 users, 5 GB | $49/mo for 5 users | No — third party only |
| **Pipedrive** | None | $24/user/mo (annual $14) | **Yes — May 2026, Growth+** |
| **monday CRM** | None meaningful | Per seat | No — third party only |
| **Freshsales** | 3 users | $11/user/mo Growth | Pro ($47) and above |
| **Attio** | 3 seats, 50,000 records | **$44/user/mo** Plus | No — third party only |
| **Folk** | **None** (14-day trial) | $30/user/mo | Claimed, vendor-sourced only |
| **HubSpot** | Yes, workflows paywalled | **$100/seat/mo** Pro + $1,500 onboarding | Professional and above |

**Corrections against the 3 August research, called out so a reviewer can verify:**

1. **Folk has no free tier.** The prior research said it did. It has a 14-day trial
   after which the account is blocked. ([folk.app/pricing](https://www.folk.app/pricing))
2. **Attio Plus is $44/user/mo, not $29.** Pro is $99, not $69. The free tier detail
   was correct. ([attio.com/pricing](https://attio.com/pricing))
3. **Dubsado is $335/$525 per year**, and the trial is 21 days of full Premier access
   with no card — not a 3-client trial. ([dubsado.com/pricing](https://www.dubsado.com/pricing))
4. **Zoho's free tier is capped at 5,000 records**, not unlimited, and allows 10 workflow
   rules with 5 active, not 1. ([zoho.com/crm/free-edition.html](https://www.zoho.com/crm/free-edition.html))
5. **17hats now has a free tier.** The "no free option at all" framing is stale.
   ([17hats.com/pricing](https://www.17hats.com/pricing))
6. **HubSpot Sales Hub Pro is $100/seat/mo**, not ~$500. The old figure reflected a
   5-seat minimum that no longer applies. ([hubspot.com/pricing/sales](https://www.hubspot.com/pricing/sales))

**Also revised: unconditional CSV export is weaker as a differentiator than claimed.**
Zoho's free edition allows 200,000 records per module and 10 exports a day; HubSpot's
free CRM exports contacts. Export is closer to table stakes. The defensible version is
**exit terms** — no account lockout at trial end, no deletion for inactivity, and export
that includes message history — not export itself.

**New entrants worth knowing:** **Clarify** (June 2025, AI-native, free tier with
unlimited seats) is the most direct free-tier threat found. **Twenty** is free when
self-hosted. In MENA specifically, the competition is WhatsApp-first platforms — Wati,
respond.io, SleekFlow, ChatDaddy — which are messaging tools that added CRM rather than
the reverse. All are paid. No venture-backed MENA-native free CRM was found launched
since mid-2025, though search coverage for Lebanon specifically was thin enough that
this should not be treated as proven.

## 13. Scope decisions requiring a reason

Three features were left unresolved in the previous scope matrix. All three are now
decided, with evidence.

### 13.1 Duplicate detection — **build in MVP, warning only**

The premise was wrong: **Dubsado has no duplicate detection and no merge at all**
(*"There is no way to merge two clients"*), and **Attio has no bulk merge**. HubSpot's
real duplicate tool is Professional-and-above and capped. Free tiers ship a *warning*,
not a dedup engine.

The closest comparable to this product — **Less Annoying CRM** — does exactly the cheap
version: at save time, if name, email or phone already exists, a red warning links to
the existing record. No scan engine, no rules, no fuzzy scoring.

The failure modes of going further are documented. Zoho hard-blocks on a unique field,
and its own community shows the result: a user asking whether they should *leave the
email address blank* to get past the gate. Teaching users to strip identifiers is worse
than the duplicate. And merge is irreversible everywhere — HubSpot unenrols merged
records from all workflows and resets every property timestamp; Bigin, Attio and
OnePageCRM all warn it cannot be undone.

**The load-bearing part is phone normalisation, not matching.** `03 123 456`,
`+961 3 123 456`, `00961 3 123 456` and `70 123 456` must normalise to E.164 before
comparison, or the matching silently does nothing. Strip the trunk `0`, default to
`+961`, store canonical and display forms.

**Not building:** fuzzy name matching. It is the false-positive generator, and name
collisions are common in a market with a small set of very frequent surnames.

**Deferred-merge stand-in:** a reversible "Mark as duplicate of…" flag that hides the
loser from lists and banners the winner. Destroys nothing, and produces the audit trail
that real merge will need in v2.

### 13.2 Bulk delete and undo — **build in MVP. Bulk merge — v2**

Shipping CSV import without a way to reverse it is the one combination the evidence
punishes without exception. **Five vendors independently built import-scoped rollback:**
Salesforce publishes a document titled *Using Mass Delete to Undo Imports*; Zoho allows
undo within 30 days; Pipedrive 48 hours, admin only; HubSpot 14 days, Super Admin only;
Dubsado a blunt delete-everything-ever-imported.

Bulk *merge*, by contrast, is not table stakes even in paid products — Attio has no
native bulk merge, Dubsado has no merge at all.

**The safety net is not optional here, for a reason specific to this product.** Less
Annoying CRM ships bulk delete with no recycle bin at all; recovery means emailing
support, who restore from backup. That is viable for a paid product with a support
team. **A free product has no support team.** The undo must live in the software.

Minimum: `deleted_at` soft delete with 30-day retention; multi-select delete with a
count confirmation (type-the-number gate above 25 records); an **undo the operation,
not the records** model where the last N bulk actions — including each import — revert
as a batch; export-before-delete offered in the confirm dialog. On mobile, bulk delete
sits behind an explicit Select mode so a long-press cannot trigger it.

### 13.3 Recurring tasks — **skip deliberately**

Two of the best-regarded CRMs for this exact segment ship without them: Less Annoying
CRM repeats *events* only, and OnePageCRM's entire model is one Next Action per contact
with no recurrence at all.

The vendor evidence is weaker than it appears. **17hats' own published examples** of
recurring to-dos are *refresh your bank connection*, *clean out inbox*, *reconcile
bookkeeping* — four of five are admin, not client relationship — and they attach to
to-do lists rather than to clients. That is a reminders app inside a CRM, competing with
the one already on the user's phone.

For wholesale specifically, the need the distribution literature names is *"customers
at risk of churning, those who haven't ordered in a long time"* — a **computed signal**,
not a calendar repeat. Pipedrive ships this as **Rotting** (per-stage day threshold,
resets on any activity, tile goes red); Capsule as a *Contacts you haven't contacted
recently* report; LACRM as a last-updated filter.

The functional difference decides it. **A recurring task fires whether or not anything
happened** — if the stockist reordered yesterday, Monday's "check on him" task fires
anyway. Dismiss it four times and the user stops trusting the task list entirely. An
inactivity signal fires only when the relationship actually went cold, and self-clears.

**What replaces it:** a **Gone quiet** view — contacts with no logged activity in N days,
N default 30, settable per contact — plus a per-contact `check_in_every_days` field,
which is the field-sales "call cycle" expressed as one column rather than a scheduler.
For genuine admin recurrence, the deliberate answer is the phone's reminders app.

`last_activity_at` must be built in MVP regardless, updated on any note, message, call
log, completed task or order — retrofitting it means starting with no history.

**No evidence was found of anyone abandoning a CRM over missing recurring tasks.**
HubSpot left the request open from 2017 to roughly 2025 at scale without visible churn.

## 14. How it could fail

| It fails because… | We prevent it by… |
|---|---|
| It becomes one 500KB HTML file again and an editor truncates it | 300-line hard limit per file, enforced by the gate, refusing the commit |
| A feature works on the builder's laptop and never on a customer's phone | Every feature proven on a second device before approval, in a fresh browser context |
| A notification path silently stops running | Transactional outbox plus heartbeat; absent-signal detection, not error detection |
| Meta billing rejects Lebanese cards and WhatsApp cannot be onboarded | Test with one real client before FEAT-0014 is approved. Deep-link version ships regardless |
| A client's WhatsApp number is banned | Official API only. No unofficial library, at any point, for any reason |
| Duplicate detection blocks legitimate entries | Warn, never block. No fuzzy name matching |
| A bulk delete destroys a client's book | Soft delete, 30 days, undo-the-operation, export-before-delete |
| Scope creeps into invoicing and it never ships | NO-GO #6, and the feature matrix fails the build if an unagreed feature appears |
| The differentiator disappears because competitors ship WhatsApp free | Assumed. The durable advantages are free-with-no-cap and the Lead Pool connection |
| Documentation drifts until it is lying | The feature ledger is generated from source, never typed. Freshness is a gate |

## 15. Sources

Every factual claim above is traceable. Full source list, including the ones that
contradict each other, is in `docs/RESEARCH-2026-08-11.md`.

---

*This document is maintained under the OGGI Build System. It is reviewed whenever the
feature matrix changes. If the code and this document disagree, the code is wrong until
a decision is recorded in `DECISIONS.md` saying otherwise.*
