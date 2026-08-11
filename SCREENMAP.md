# SCREENMAP — OGGI Free CRM

Boxes and arrows. Checked mechanically by `python3 scripts/blockout_check.py`, which
walks this graph and fails if any screen in the built product is unreachable, or if any
screen named here does not exist in the code.

Every screen id must match a `data-screen="..."` in `src/`.

---

entry: screen-login

screen-login          -> screen-home
screen-home           -> screen-contacts, screen-pipeline, screen-today, screen-quiet, screen-settings
screen-contacts       -> screen-contact, screen-contact-new, screen-import, screen-home
screen-contact-new    -> screen-contact, screen-contacts
screen-contact        -> screen-contacts, screen-task-new, screen-deal
screen-import         -> screen-contacts
screen-pipeline       -> screen-deal, screen-home
screen-deal           -> screen-pipeline, screen-contact
screen-today          -> screen-contact, screen-task-new, screen-home
screen-task-new       -> screen-contact, screen-today
screen-quiet          -> screen-contact, screen-home
screen-settings       -> screen-team, screen-content, screen-bin, screen-whatsapp, screen-home
screen-team           -> screen-settings
screen-content        -> screen-settings
screen-bin            -> screen-settings, screen-contacts
screen-whatsapp       -> screen-settings

roles:
  owner:     screen-login, screen-home, screen-contacts, screen-contact, screen-contact-new, screen-import, screen-pipeline, screen-deal, screen-today, screen-task-new, screen-quiet, screen-settings, screen-team, screen-content, screen-bin, screen-whatsapp
  manager:   screen-login, screen-home, screen-contacts, screen-contact, screen-contact-new, screen-import, screen-pipeline, screen-deal, screen-today, screen-task-new, screen-quiet, screen-team
  rep:       screen-login, screen-home, screen-contacts, screen-contact, screen-contact-new, screen-pipeline, screen-deal, screen-today, screen-task-new, screen-quiet
  viewonly:  screen-login, screen-home, screen-contacts, screen-contact, screen-pipeline, screen-deal, screen-today, screen-quiet
  qc:        screen-login, screen-home, screen-content
  writer:    screen-login, screen-home, screen-content

---

## Notes on specific screens

**screen-home** is a dashboard, not a menu. It shows three counts — due today, gone
quiet, unread WhatsApp — each one tappable. A menu that only navigates is a wasted first
screen on a phone.

**screen-bin** is the 30-day recycle bin. It must be reachable from `screen-contacts`
directly and not only through Settings, because the moment a user needs it is the moment
they just deleted something from the contact list. Undo that is only findable from
Settings is undo that does not exist.

**screen-whatsapp** is where Embedded Signup runs (FEAT-0014). Until that feature is
unblocked it exists and explains what connecting will do — an honest empty state, not a
hidden screen.

**screen-content** is the text editor for Writers and Quality Control. A Writer can edit
and submit; only QC or the Owner sees the Publish control. That separation is enforced
in the database by a `SECURITY DEFINER` function, not by hiding a button.

---

## Every screen also needs four states

The checker cannot see these. You check them by clicking. They are the states that get
forgotten when the happy path is built first, and every one is a state a real user hits.

| State | The question |
|---|---|
| **empty** | first-ever use, nothing here yet — does it explain what to do? |
| **loading** | is something visibly happening, or does it look frozen? |
| **error** | when it fails, is there a visible message? Not silence, not a raw error |
| **no permission** | wrong role — does it explain, or just look broken? |

The four that matter most in this product, from the pre-mortem:

- **screen-contacts, empty** — a brand new user with zero contacts is the single most
  common first experience. It must offer Import and Add, not a blank list.
- **screen-quiet, empty** — must say "you are on top of it," not look broken.
- **screen-contact, no permission** — a Rep opening another Rep's contact by URL must be
  told why, not shown a blank page.
- **screen-whatsapp, error** — Meta returns specific failures (display name not approved,
  window closed, number not on WhatsApp). Each must be translated into plain language.
