# GOTCHAS — environment facts that defy reasonable assumption

**Read this at the start of every build session. Append to it every single time Hadi has to correct
something.** This file is the compounding memory of the estate. Each line here cost real time to learn
once; none of them should cost it twice.

Format: **the fact** — why it bites — what to do instead.

---

## Hosting and deploys

- **`*.pages.dev` does not load on Hadi's network. Confirmed repeatedly.** Never hand him a pages.dev
  link and never verify against one. Use **`*.workers.dev`** (`oggi-teamz.workers.dev` works fine).

- **"Deployed" in a dashboard is not proof.** Cloudflare needs meaningfully longer than ~7 seconds to
  propagate, so a verification that runs too early looks exactly like a failed deploy. Always poll
  `/__version` with `Cache-Control: no-store` until it returns the expected build id. `verify_live.mjs`
  does this — polling up to 200 seconds.

- **The Cloudflare Deploy button often needs a second click.** Confirm by fetching the live bytes, not
  by looking at the screen.

- **Deploy the SUBFOLDER, never the parent.** Dragging the whole parent folder to Cloudflare broke the
  wholesale apps repeatedly. The correct upload is the app subfolder only. A build that is a PWA needs
  ALL its files (`sw.js`, every `manifest-*.json`, every icon) — uploading only `index.html` and the
  logos silently strips install, icons and offline support while appearing to succeed.

## Editing files

- **The Edit tool truncates the tail of very large HTML files on save.** This silently killed every
  login and button in the wholesale app five separate times. For any file over a few hundred KB, write
  via Python and then **verify the file still ends with `</html>`** and that `<script>`/`</script>`
  counts match.

- **On the connected-folder mount, `Write` does NOT truncate on overwrite** — but prefer writing a new
  file or using `cp`/`>` anyway.

- **Where a codebase redefines things, the LAST definition wins.** Editing an earlier copy changes
  nothing while appearing to succeed. `scripts/inventory.py` recomputes which copy is active on every
  run — trust that, never a table of line numbers written by hand (every row of the previous
  hand-written table was wrong).

## Supabase

- **ONE Supabase project. A new app is a new SCHEMA, never a new project.** Pro billing is ~$25/month
  per organisation plus ~$10/month per project, a Pro project cannot be paused, and compute is not
  covered by the spend cap. Fifteen apps as fifteen projects is $165/month; as fifteen schemas it is $25.

- **Keep the Spend Cap ON.** It restricts service instead of billing. It does NOT cover: compute,
  branching compute, read-replica compute, PITR, custom domains, IPv4, extra disk IOPS, Log Drains,
  MFA Phone.

- **The sandbox cannot reach Supabase.** Run SQL by driving Hadi's logged-in browser (the SQL editor;
  `insertText` works, no auto-close problems).

- **`net._http_response` retains only about 6 hours and has no documented retry.** A failed webhook is
  invisible within a day. This is why the outbox pattern is mandatory, not optional, on this stack.

- **A service-role write logs a NULL actor.** "Who changed the price?" becomes unanswerable for exactly
  the admin actions most worth tracing. Any server function acting on a user's behalf must set
  `app.actor_id` at the top of the transaction.

- **Live estate security debt, still open:** a permissive `demo_all` anon-full-access policy (the
  CVE-2025-48757 pattern that exposed 170+ AI-built apps), plaintext rep passwords syncing to a shared
  document readable by every authenticated tenant, and an admin password that sat in a document in
  plaintext — **treat it as leaked and rotate it.**

## Shopify

- **Live-theme API writes are blocked.** Use themeDuplicate → themeFilesUpsert → publish.
- **The browser admin themes iframe is slow and the Publish click is unreliable via automation.**
  Hadi publishes himself.

## The estate itself

- **The 540-function single-file wholesale app cannot be gated meaningfully as it stands.** Duplicate
  detection, edit-in-place and the file-size cap all assume files small enough to hold whole, and it
  already carries 21 dead duplicate definitions. It needs a one-time split into modules, run as its
  own project, with the generated ledger as the checklist.

- **`flashSaved` is monkey-patched to call `persist()`.** Any audit that misses this will falsely
  conclude the app never saves.

- **Hadi's skill library is ~212 skills and ~130,000 characters of always-loaded descriptions**, against
  a listing budget of roughly 1% of the context window. The platform silently drops descriptions for
  least-used skills. This is the mechanical reason skills do not reliably auto-fire for him. Pruning it
  is a real prerequisite, not housekeeping.

---

## How to add to this file

One line, same format, appended at the bottom of the right section, **the same session the lesson is
learned.** A gotcha written down a week later is a gotcha that has already cost a second time.

## GitHub Desktop on this machine (learned 2026-08-11)

- **Typing only works when the GitHub Desktop window is genuinely frontmost.** Four attempts failed
  while File Explorer held focus — clicks registered, the field even showed a focus ring, but no text
  landed. Fix: click the app's taskbar icon first (needs the File Explorer grant), confirm with a
  screenshot that it is on top, then type.
- **Two separate grants are needed:** the launcher `githubdesktop.exe` AND the versioned
  `app-3.6.3\githubdesktop.exe` that actually owns the window. Granting only the first shows a masked
  window.
- **Git cannot run inside the connected folder via device_bash** — the mount cannot delete files, so
  the second commit fails on a leftover `HEAD.lock`. Repos must be created by GitHub Desktop on
  Windows, which does not go through the mount.
- **The cloud container cannot push to GitHub** — the proxy only allows repos in the session's
  authorized set.
