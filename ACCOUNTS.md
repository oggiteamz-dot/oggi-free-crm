# ACCOUNTS — <Product>

Who owns what. **Never put a password in this file** — the checks will fail the
build, and rightly: a password in a file is a password that has leaked.

| Service | What it's for | Root owner | Client contact | Rotated on |
|---|---|---|---|---|
| Hosting (Cloudflare) | serves the site | | | |
| Supabase | database + server functions | | | |
| Domain registrar | the address | | | |
| Payments (Whish/Stripe) | taking money | | | |
| Email / WhatsApp | messages to customers | | | |

## Where the secrets actually live

Environment variables only. Never in the code, never in a document, never in a
chat message.

| Name | Used by | Where it's set |
|---|---|---|
| `DATABASE_URL` | drills, migrations | local environment |
| `VERIFY_PASSWORD` | the live check's test login | local environment / CI secret |

## On handover

1. Transfer at **root/owner** level — not as an invited collaborator.
2. **Rotate everything**, then record the date above.
3. Confirm the client can sign in to each one, in front of you, before invoicing.
