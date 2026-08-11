---
topic: spec
status: current
---

# OGGI Free CRM — SPEC

**Status:** Draft — awaiting owner approval
**Approved by:** _(type APPROVED and the date here — nothing gets built until you do)_

> This is one page on purpose. Of ten real failures in past OGGI builds, ONE was caused
> by bad planning. Eight were caused by nobody checking the live product. A twelve-page
> spec would move effort to the wrong half of the problem.
>
> The long-form reasoning, sources and competitive analysis live in `docs/PRD.md`.
> This page is what gets checked against the finished product.

---

## 1. In one sentence

A permanently free, mobile-first CRM for Lebanese and MENA professionals and small
wholesalers, in which WhatsApp is a first-class channel rather than an add-on.

## 2. The job it is hired to do

A Beirut wholesaler runs their client book through WhatsApp and memory. They lose
customers they simply forgot to follow up with, and when a rep leaves, the relationships
leave in that rep's phone.

**What they do today instead:** WhatsApp plus memory, sometimes an Excel sheet, and
occasionally an abandoned CRM trial.

## 3. Done looks like

**Ninety days after launch: 30 OGGI clients signed in within the last 7 days, each with
more than 50 contacts.** Returning users with real data — not signups.

## 4. Who touches it

| Role | What they do | What they must NEVER be able to do |
|---|---|---|
| Owner | Everything: billing, team, deletion, export, settings | Be removed while they are the last owner |
| Manager | Sees all contacts and deals; assigns work; invites Reps | Change billing, delete the workspace, remove an Owner |
| Rep | Sees and edits only their own contacts and deals | See another Rep's contacts; open Settings; export everything |
| View-only | Reads what they are scoped to | Create, edit, delete, or send a WhatsApp message |
| Quality Control | Approves text changes before they go live | Author the edit they are approving |
| Writer / Copywriter | Edits any user-visible text, submits for approval | Publish their own edit; touch data or settings |

## 5. What it must do

| ID | The system must… | How you personally check it (under 5 min) |
|---|---|---|
| R-01 | Add a contact with name, phone, WhatsApp number — appears top of the list | Add one, look at the list |
| R-02 | Warn, never block, when a phone or email already exists; offer to open it | Add the same number twice |
| R-03 | Treat `03 123 456`, `+961 3 123 456`, `00961 3 123 456` as one number | Add one, try the others |
| R-04 | Filter the contact list as you type, on name or number | Type three letters |
| R-05 | Export every contact and field to CSV, no paywall, ever | Tap Export, open the file |
| R-06 | Import a CSV matching on normalised phone/email, defaulting to skip-existing | Import the same file twice; count must not double |
| R-07 | Undo a bulk delete, or an entire import, as one operation | Delete 5, tap Undo |
| R-08 | Keep deleted records recoverable for 30 days | Delete one, find it in the bin |
| R-09 | Drag a deal between pipeline stages; survives a full app restart | Drag, force-quit, reopen |
| R-10 | Show every call, message and note on a contact, newest first | Open a contact |
| R-11 | Message a contact on WhatsApp from their record, and log that it happened | Tap WhatsApp, send, come back |
| R-12 | Show what is due today; mark anything late as overdue | Add a task dated yesterday |
| R-13 | Show contacts with no activity in N days (default 30) | Backdate one, open Gone quiet |
| R-14 | Owner invites a Rep who then sees only their own contacts | Invite; sign in on a second phone |
| R-15 | Be usable within one minute of signup, pipeline already populated | Sign up fresh |
| R-16 | Install to a phone home screen as a real app | Add to Home Screen; open it |
| R-17 | Writer edits any visible text; a different person must publish it | Change a label; try to publish it yourself |

## 6. What must survive

Everything here is on the persistence allow-list (`src/core/store.js`, `DATA_KEYS`) **and**
proven on a second device before approval. `localStorage` is a cache, never the record.
This is the most expensive failure class in OGGI's history.

| What | Where it is stored | Proven on a second device? |
|---|---|---|
| Contacts | `crm.contacts` | Required |
| Companies | `crm.companies` | Required |
| Deals and stage | `crm.deals` | Required |
| Activity timeline | `crm.activities` | Required |
| WhatsApp messages | `crm.messages` | Required |
| Tasks | `crm.tasks` | Required |
| Users and roles | `auth.users` + `crm.user_roles` | Required |
| Editable text | `content_string` | Required |
| Soft-deleted rows | `deleted_at`, 30-day retention | Required |
| Operation log (undo) | `crm.operations` | Required |

## 7. Who gets told, and when

| Event | Who must be told | Channel | Through the outbox? |
|---|---|---|---|
| A teammate is invited | The invitee | Email, WhatsApp fallback | **Yes** |
| A task becomes overdue | The task owner | In-app badge, push if installed | No — computed on read |
| A customer replies on WhatsApp | The assigned pro | Push + in-app | **Yes** |
| A contact passes its quiet threshold | The assigned pro | The Gone quiet list | No — computed on read |
| A text change is submitted | Quality Control | Email | **Yes** |
| A bulk delete over 25 records | The Owner | Email receipt | **Yes** |

## 8. What can be edited later without a developer

| Thing | Who may edit | Who may publish |
|---|---|---|
| Every button, heading, empty-state, error message | Writer, Copywriter | Quality Control, Owner |
| Pipeline stage names | Owner, Manager | Owner |
| The Gone quiet day threshold | Owner | Owner |
| WhatsApp templates | Copywriter | Quality Control + Meta approval |
| Role descriptions on the invite screen | Writer | Quality Control |
| Onboarding welcome and first step | Writer, Copywriter | Quality Control |

## 9. NO-GOS

1. NOT a paid tier on any core function — contacts, deals, tasks, export stay free forever.
2. NOT a cap on users, contacts or deals.
3. NOT gating CSV export behind anything, including account expiry.
4. NOT built on an unofficial WhatsApp library. The ban lands on the client's business number.
5. NOT one shared OGGI WhatsApp number. Each business connects its own via Embedded Signup.
6. NOT proposals, contracts, e-signature or invoicing in v1 — that is Lead Pool.
7. NOT a custom-object platform. Custom fields yes; an object builder no.
8. NOT two-way sync with Lead Pool. One direction: a Won deal creates a contact here.
9. NOT an AI feature without an explicit off-switch.
10. NOT hard-delete on a user action. 30-day soft delete — there is no support team to restore.
11. NOT a single HTML file. 300 lines per file, enforced by the gate, refusing the commit.
12. NOT dependent on Lebanese A2P SMS for anything — broken on both carriers since Feb 2025.

## 10. Appetite

- **Time:** 6 sessions to v1 (FEAT-0001 … FEAT-0013). 4 more for two-way WhatsApp (FEAT-0014).
- **Money:** $0 recurring for messaging — clients pay Meta directly under the Tech Provider
  model. Supabase and Cloudflare on existing OGGI plans.
- **When these run out we cut scope, not quality.** Cut order: the automation rule, then
  companies, then the pipeline. **Never cut:** export, soft delete, the second-device
  proof, the 300-line limit.

## 11. How it could fail (pre-mortem)

| It fails because… | We prevent it by… |
|---|---|
| It becomes one giant HTML file and an editor truncates it | 300-line limit, enforced, refusing the commit |
| A feature works on the laptop and never on a customer's phone | Second-device proof in a fresh browser context before approval |
| A notification path silently stops | Outbox plus heartbeat — absent-signal detection, not error detection |
| Meta billing rejects Lebanese cards | Test with one real client before FEAT-0014. The deep-link version ships regardless |
| A client's WhatsApp number is banned | Official API only, no exceptions |
| Duplicate detection blocks legitimate entries | Warn, never block. No fuzzy name matching |
| A bulk delete destroys a client's book | Soft delete, 30 days, undo-the-operation, export-before-delete |
| Scope creeps into invoicing and it never ships | NO-GO 6, and an unagreed feature fails the completeness check |
| Competitors ship free WhatsApp and the wedge closes | Assumed. The durable edges are free-with-no-cap and the Lead Pool link |
| The docs drift until they lie | The feature ledger is generated from source; freshness is a gate |
