#!/usr/bin/env python3
"""
proof_cards.py — the four minutes of checking that only YOU can do.

WHY A HUMAN STILL HAS TO DO THIS
--------------------------------
From the adversarial review: an "independent verifier" sub-agent is not
independent. Same model, same priors, spawned and framed by the author. It will
report style nits and miss a record-shape change — exactly as a previous
automated sweep did, because it compared function NAMES while the bug was a
change in record SHAPE.

Everything a machine can check is already in `just check` and `verify_live`.
What remains is the one verification an agent cannot fake: a person, on their own
phone, clicking the thing and looking at the screen.

THE THREE TICKS — and why the third one is the whole point
----------------------------------------------------------
  [ ] Works                  — it did the thing
  [ ] Survives reload        — still there after closing and reopening
  [ ] Survives ANOTHER DEVICE — still there on a different phone/browser

A feature can pass the first two and be permanently broken for every customer.
That is not hypothetical: it is exactly what happened to the announcements
feature, which worked on the device that created it and never once arrived on
anyone else's. Both features involved were marked done and tested.

Ticking box 2 but not box 3 means: the app saved it to this browser only, never
to the server. Say that sentence to Claude and it will know exactly what to fix.

OUTPUT
  proof-cards.html   — open on your phone, tick as you go
  stdout             — the same cards as text
"""

from __future__ import annotations

import html
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from checks._common import load_config, read  # noqa: E402


def _clean(s: str) -> str:
    """Turn a raw YAML scalar into the text a human should read.

    Two things must happen here, and both were bugs:

    1. Strip a trailing ` # comment`. The shipped template writes
           role: buyer                # which signed-in role does this
       and without stripping, the Proof Card told the owner to sign in as
       "buyer                # which signed-in role does this".

    2. Strip surrounding quotes ONLY when they are a matched pair. Naively
       calling .strip('"') mangles   Tap "Place order"   into
       Tap "Place order   — which then tells him to look for the wrong words.
    """
    s = re.sub(r"\s+#\s.*$", "", s).strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        return s[1:-1]
    return s


def parse_feature(path: Path) -> dict:
    """Minimal YAML reader — enough for the flat FEAT file format, no dependency."""
    data: dict = {}
    key = None
    for raw in read(path).splitlines():
        if not raw.strip() or raw.strip().startswith("#"):
            continue
        if raw.strip().startswith("- ") and key:
            data.setdefault(key, [])
            if isinstance(data[key], list):
                data[key].append(_clean(raw.split("- ", 1)[1]))
            continue
        if ":" in raw and not raw.startswith(" "):
            key, _, val = raw.partition(":")
            key = key.strip()
            val = _clean(val)
            data[key] = val if val else []
    # The FILENAME is the identity, always. Taking the id from the file contents
    # meant a FEAT-0007.yml copied from the template and not edited produced a
    # card labelled FEAT-0000, silently colliding with every other copy.
    data["id"] = path.stem
    return data


CARD_TEXT = """
┌────────────────────────────────────────────────────────────────────┐
  {id} — {title}
└────────────────────────────────────────────────────────────────────┘
  WHERE   {url}
  SIGN IN AS  {role}

  DO
{steps}

  YOU SHOULD SEE
    {expect}

  NOW THE THREE TICKS
    [ ] 1. Works            — you saw what you expected
    [ ] 2. Survives reload  — fully close the page, open it again, still there
    [ ] 3. Survives ANOTHER DEVICE — open it on a different phone or a private
           window, sign in, and it is STILL there

  IF 1 AND 2 PASS BUT 3 FAILS, say this to Claude, word for word:
    "{id} passes reload but fails on a second device — the app is saving it to
     the browser only, not to the server. Check every key it writes is on the
     save list."
"""


def build(cfg: dict):
    root = Path(cfg["_root"])
    feat_dir = root / "features"
    base_url = cfg.get("live_url", "").rstrip("/") or "(set live_url in oggi-build.config.json)"

    if not feat_dir.exists() or not any(feat_dir.glob("FEAT-*.yml")):
        print(
            "\nNo features declared yet.\n"
            "Proof Cards are generated from features/FEAT-####.yml — one small file per\n"
            "feature. Without them there is no list of what is supposed to work, so\n"
            "'is anything missing?' cannot be answered by anyone, including you.\n"
            "\nAsk Claude: \"create the feature files from the spec\".\n"
        )
        return []

    cards = []
    for f in sorted(feat_dir.glob("FEAT-*.yml")):
        d = parse_feature(f)
        steps = d.get("steps") or ["(no steps written — ask Claude to fill these in)"]
        if isinstance(steps, str):
            steps = [steps]
        cards.append(
            {
                "id": d.get("id", f.stem),
                "title": d.get("title", "(untitled)"),
                "url": base_url + (d.get("path", "") or ""),
                "role": d.get("role", "any signed-in user"),
                "steps": steps,
                "expect": d.get("expect", "(not stated — ask Claude what you should see)"),
            }
        )
    return cards


HTML_HEAD = """<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Proof Cards</title><style>
:root{--ink:#0E2230;--mint:#54E5A0;--em:#00845F;--bg:#f6f8f8}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);
font:16px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;padding:16px}
h1{font-size:20px;margin:0 0 4px}.sub{color:#5a6b78;font-size:14px;margin:0 0 20px}
.card{background:#fff;border-radius:14px;padding:18px;margin:0 0 16px;
box-shadow:0 1px 3px rgba(14,34,48,.10)}
.id{font:600 12px ui-monospace,monospace;color:var(--em);letter-spacing:.06em}
.t{font-weight:700;font-size:17px;margin:2px 0 12px}
.k{font-size:11px;letter-spacing:.09em;color:#7b8b96;text-transform:uppercase;margin:14px 0 4px}
ol{margin:4px 0 0 18px;padding:0}li{margin:3px 0}
.expect{background:#eefaf3;border-left:3px solid var(--mint);padding:9px 12px;border-radius:0 8px 8px 0}
label{display:flex;gap:11px;align-items:flex-start;background:#f4f7f9;border-radius:10px;
padding:12px;margin:8px 0;cursor:pointer}
input{width:22px;height:22px;margin:0;flex:0 0 auto;accent-color:var(--em)}
.warn{background:#fff6e8;border-left:3px solid #f0a532;padding:11px 13px;border-radius:0 8px 8px 0;
font-size:14px;margin-top:12px}
code{background:#0E2230;color:#8ff0c0;padding:2px 6px;border-radius:5px;font-size:13px}
a{color:var(--em)}
</style></head><body>
<h1>Proof Cards</h1>
<p class="sub">Four minutes per feature. Tick all three boxes or it is not done.
Box 3 is the one that catches the bug that has burned you before.</p>
"""


def render_html(cards) -> str:
    parts = [HTML_HEAD]
    for c in cards:
        steps = "".join(f"<li>{html.escape(s)}</li>" for s in c["steps"])
        parts.append(f"""
<div class="card">
  <div class="id">{html.escape(c['id'])}</div>
  <div class="t">{html.escape(c['title'])}</div>
  <div class="k">Where</div><a href="{html.escape(c['url'])}">{html.escape(c['url'])}</a>
  <div class="k">Sign in as</div>{html.escape(c['role'])}
  <div class="k">Do</div><ol>{steps}</ol>
  <div class="k">You should see</div>
  <div class="expect">{html.escape(c['expect'])}</div>
  <div class="k">The three ticks</div>
  <label><input type="checkbox"><span><b>Works</b> — you saw what you expected.</span></label>
  <label><input type="checkbox"><span><b>Survives reload</b> — fully close the page, open it again, still there.</span></label>
  <label><input type="checkbox"><span><b>Survives another device</b> — different phone or a private window, sign in, still there.</span></label>
  <div class="warn"><b>If 1 and 2 pass but 3 fails</b>, tell Claude exactly this:<br>
  <code>{html.escape(c['id'])} passes reload but fails on a second device — it is saving to the browser only, not the server.</code></div>
</div>""")
    parts.append("</body></html>")
    return "\n".join(parts)


def main() -> int:
    cfg = load_config()
    cards = build(cfg)
    if not cards:
        return 1
    for c in cards:
        print(CARD_TEXT.format(
            id=c["id"], title=c["title"], url=c["url"], role=c["role"],
            steps="\n".join(f"    {i}. {s}" for i, s in enumerate(c["steps"], 1)),
            expect=c["expect"],
        ))
    out = Path(cfg["_root"]) / "proof-cards.html"
    out.write_text(render_html(cards), encoding="utf-8")
    print(f"\n  {len(cards)} card(s). Open proof-cards.html on your phone and tick as you go.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
