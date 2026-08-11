# ACCOUNTS — OGGI Free CRM

Who owns what. **Never put a password in this file** — the `secrets` check fails the
build if one appears, and rightly: a password in a file is a password that has leaked.

| Service | What it's for | Root owner | Client contact | Rotated on |
|---|---|---|---|---|
| Cloudflare | serves the site | OGGI (Hadi Hamza) | n/a — OGGI-hosted | _(record the date)_ |
| Supabase | database, auth, edge functions | OGGI (Hadi Hamza) | n/a — OGGI-hosted | _(record the date)_ |
| Domain registrar | the address | OGGI (Hadi Hamza) | n/a | _(record the date)_ |
| GitHub | source code and history | OGGI (`oggiteamz-dot`) | CTO / partner — admin | _(record the date)_ |
| Meta Business Portfolio | WhatsApp Tech Provider app | OGGI (Hadi Hamza) | n/a | _(record the date)_ |
| **Each client's WhatsApp Business Account** | **their** messaging | **the client** | the client | **client rotates** |
| Payments | not applicable — the product is free | — | — | — |

## The WhatsApp ownership rule

This is the one line in this file that is a product decision, not an admin note.

**OGGI never owns a client's WhatsApp Business Account.** Under the Meta Tech Provider
model with Embedded Signup, each business creates or selects its own WABA, verifies its
own number, and attaches its own payment method. Meta bills them directly. OGGI is
authorised to act on their account and can be de-authorised by them at any time.

Three consequences, and all three are deliberate:

1. **OGGI carries no messaging cost.** That is what makes a free product survivable.
2. **A client can leave with their number and their history intact.** No lock-in, which
   is the complaint this whole product is built against.
3. **One client's quality downgrade or block cannot affect another's messaging.**

If anyone proposes routing every client through one shared OGGI number to simplify
onboarding, the answer is no — see NO-GO 5 in `SPEC.md`.

## Where the secrets actually live

Environment variables only. Never in the code, never in a document, never in a chat
message. The `secrets` check enforces this on every commit.

| Name | Used by | Where it is set |
|---|---|---|
| `DATABASE_URL` | drills, migrations | local environment |
| `VERIFY_PASSWORD` | the live check's test login | local environment / CI secret |
| `SUPABASE_SERVICE_ROLE_KEY` | edge functions only | Supabase function secrets — **never** in front-end source |
| `META_APP_SECRET` | Embedded Signup callback | Supabase function secrets |
| `META_WEBHOOK_VERIFY_TOKEN` | WhatsApp webhook handshake | Supabase function secrets |

The Supabase **publishable** key (`sb_publishable_…`) is not a secret. It is designed to
be served to every visitor; access control is row-level security in the database, not key
secrecy. Do not treat its presence in front-end source as a finding.

## On handover

If this product is ever handed to a client or a partner:

1. Transfer at **root/owner** level — not as an invited collaborator.
2. **Rotate everything**, then record the date in the table above.
3. Confirm they can sign in to each service, in front of you, before invoicing.
4. WhatsApp needs no transfer — each client already owns their own account. That is the
   point of the architecture.
