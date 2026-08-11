# PLAIN ENGLISH — every word the tools use, and what it actually means

You do not need to learn these to use the system. This is here for the moment a
message uses a word you don't know, so you never have to guess or ask.

| The word you'll see | What it actually means |
|---|---|
| **commit** | Saving a snapshot of the whole project into its history, with a note about what changed. Claude does this for you. It is what makes "prove nothing was removed" possible. |
| **uncommitted changes** | Edits that haven't been saved into the history yet. If you deploy now, there'd be no record of what went live. |
| **SHA / build number** | The ID of one exact version of your code, like `a71c0d3b`. If the live site shows a different one, you're testing something other than what you just built. |
| **repo / repository** | The project folder plus its full history. One per product. |
| **exit code** | How a command says "worked" or "didn't" without words. Green = worked. Red = didn't. That's all it means. |
| **the gate** | `just check` — the one command that says green or red. |
| **ledger / inventory** | The automatic list of everything in your product: every function, screen, link and database table. Generated from the code, never typed. |
| **vertical slice** | One whole feature, finished all the way through — screen, saving, reading it back, deployed — before starting the next. The opposite is building all the screens first and wiring up saving later, which is how you get a beautiful app that doesn't save. |
| **blockout / greybox** | Every screen built as an ugly grey box with the buttons actually working, so you can walk the whole product before anything is designed. |
| **orphan** | A screen or piece of code nothing links to. It exists, and nobody can reach it. |
| **dead end** | A screen with no way forward and no way back. The user is stuck. |
| **persistence / the save list** | The list of things the app actually saves to the server. Anything missing from it works until you reload, then vanishes — and never appears on anyone else's device. |
| **fresh browser context / second device** | Opening the product as if you were a completely different person on a different phone. The single most important test there is. |
| **migration** | A file describing one change to the database's shape ("add a column for colour"). They run in order, so the database can be rebuilt from nothing. |
| **backfill** | Filling in the new column for rows that already existed before it was added. |
| **RLS (row-level security)** | The lock that stops one customer reading another customer's data. Off by default in a new table — which is why it gets checked. |
| **policy** | One rule about who can read or change what. A policy set to "true" means *anyone*, which is almost always a mistake. |
| **placeholder** | Fake text left in by accident, like `PAY-LINK-HERE` or `<token>`. Every one of these has shipped to a real customer before. |
| **escaping** | Making sure something a customer typed is shown as text, not run as code. Without it, someone can type a script into your form and have it run on your staff's screens. |
| **outbox** | A list of messages that must be sent, saved at the same moment as the thing that triggered them — so "we forgot to tell anyone" becomes impossible. |
| **heartbeat** | A scheduled job checking in to say "I ran". If it stops checking in, an alarm fires. It's the only way to notice something that *isn't* happening. |
| **silent failure** | Something broke and nobody was told. The most expensive failure type you've had. |
| **linting** | An automatic check for sloppy or risky code patterns, like spellcheck for code. |
| **rollback** | Putting the previous version back. Restores code only — not the database, not passwords, not settings. |
| **staging** | A private copy of the product for testing, so you're not experimenting on customers. |
| **CI** | The checks running automatically on a server every time something changes, whether or not anyone remembered to run them. |
| **waiver** | A written, dated note saying you deliberately skipped a check and why. The only legitimate way to skip one. |
| **golden path** | A flow that must never break — paying, signing in, the main action. Re-tested after every change, forever. |
| **proof card** | The four minutes only you can do: click it, reload it, open it on another phone, tick three boxes. |
| **evidence pack** | The live link, the build number and a 60-second recipe for you to re-check a claim yourself. |
