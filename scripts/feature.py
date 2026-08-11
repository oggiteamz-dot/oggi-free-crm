#!/usr/bin/env python3
"""
feature.py — the build loop. One feature at a time, and you decide when it's done.

THE GAP THIS FILLS
------------------
The rule "build one feature at a time" existed as a written instruction. A written
instruction is a request. Nothing stopped Claude building four features and handing
over a pile — which is exactly what the owner said he did not want:

    "there's no way for me to look at one feature, make sure it works,
     then we move to the next, then the next, then the next."

So the loop is now a state machine with a hard limit, and only the OWNER can move a
feature into 'approved'.

THE STATES

    planned        agreed, not started
    building       being worked on right now          <- only ONE at a time
    awaiting-test  built and live, waiting for YOU    <- only ONE at a time
    approved       you tested it, all three ticks     <- locked, never breaks again
    blocked        you tested it and it failed

THE HARD RULE

    Nothing new can start while something is waiting for you.

    `feature.py start` refuses. The `wip` check in the gate fails. So "I'll just
    build the next one while he's busy" is not available, and the pile cannot form.

ON APPROVAL, the feature is appended to GOLDEN-PATHS.csv automatically — the list
that gets re-tested after every future change, forever. That is what makes approval
mean something permanent rather than a moment.

USAGE
    python3 scripts/feature.py board                     # where are we?
    python3 scripts/feature.py start   FEAT-0007
    python3 scripts/feature.py built   FEAT-0007 --url https://x/orders
    python3 scripts/feature.py approve FEAT-0007 --by Hadi
    python3 scripts/feature.py reject  FEAT-0007 --why "the total is wrong on mobile"
"""

from __future__ import annotations

import html
import re
import signal
import sys
from datetime import date
from pathlib import Path

# Piping into `head` closes the pipe early. Without this, Python prints a
# BrokenPipeError traceback that looks exactly like the tool crashing — and a tool
# that appears to crash is a tool that stops being trusted.
try:
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)
except (AttributeError, ValueError):
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent))
from checks._common import load_config, read  # noqa: E402

STATES = ["planned", "building", "awaiting-test", "approved", "blocked"]
IN_FLIGHT = ("building", "awaiting-test")

LABEL = {
    "planned": "not started",
    "building": "I'm building it now",
    "awaiting-test": "WAITING FOR YOU TO TEST",
    "approved": "approved by you — locked",
    "blocked": "failed your test — I'm fixing it",
}

# Same states, phrased to read correctly mid-sentence ("... is still being built").
MID_SENTENCE = {
    "planned": "not started yet",
    "building": "still being built",
    "awaiting-test": "still waiting for you to test it",
    "approved": "already approved",
    "blocked": "still failing your test",
}


# ---------------------------------------------------------------------------
# Reading and writing the feature files
# ---------------------------------------------------------------------------

def feat_dir(cfg) -> Path:
    return Path(cfg["_root"]) / "features"


def _scalar(text: str, key: str, default: str = "") -> str:
    m = re.search(rf"^{key}:\s*(.*)$", text, re.M)
    if not m:
        return default
    v = re.sub(r"\s+#\s.*$", "", m.group(1)).strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        v = v[1:-1]
    return v


def load_all(cfg) -> list[dict]:
    d = feat_dir(cfg)
    if not d.exists():
        return []
    out = []
    for p in sorted(d.glob("FEAT-*.yml")):
        text = read(p)
        out.append({
            "id": p.stem,
            "path": p,
            "title": _scalar(text, "title", "(untitled)"),
            "status": _scalar(text, "status", "planned"),
            "url": _scalar(text, "live_url"),
            "verified_by": _scalar(text, "verified_by"),
            "proven": _scalar(text, "last_proven_at"),
            "note": _scalar(text, "review_note"),
        })
    return out


def set_fields(path: Path, **fields) -> None:
    """Update or append top-level scalars, preserving everything else."""
    text = read(path)
    for key, value in fields.items():
        line = f"{key}: {value}"
        if re.search(rf"^{key}:", text, re.M):
            text = re.sub(rf"^{key}:.*$", line, text, count=1, flags=re.M)
        else:
            text = text.rstrip() + "\n" + line + "\n"
    path.write_text(text, encoding="utf-8")


def find(cfg, fid: str) -> dict:
    for f in load_all(cfg):
        if f["id"].lower() == fid.lower():
            return f
    print(f"\n  No feature called {fid}. Features that exist:")
    for f in load_all(cfg):
        print(f"    {f['id']}  {f['title']}")
    raise SystemExit(2)


# ---------------------------------------------------------------------------
# The board
# ---------------------------------------------------------------------------

def board(cfg, quiet: bool = False) -> int:
    feats = load_all(cfg)
    if not feats:
        print("\n  No features yet. They come out of the spec — ask Claude to"
              "\n  \"turn the spec into the feature list\" and you'll get a numbered list to approve.\n")
        return 0

    by = {s: [f for f in feats if f["status"] == s] for s in STATES}
    unknown = [f for f in feats if f["status"] not in STATES]
    done, total = len(by["approved"]), len(feats)

    if not quiet:
        W = 72
        print("\n" + "=" * W)
        print("  FEATURE BOARD")
        print("=" * W)
        bar_len = 40
        filled = int(bar_len * done / total) if total else 0
        print(f"  [{'#' * filled}{'.' * (bar_len - filled)}]  {done} of {total} approved")
        print()

        waiting = by["awaiting-test"]
        if waiting:
            f = waiting[0]
            print("  " + "-" * (W - 4))
            print("  >>> WAITING FOR YOU")
            print(f"      {f['id']} — {f['title']}")
            if f["url"]:
                print(f"      Open: {f['url']}")
            print("      Open proof-cards.html, do the three ticks, then tell me")
            print("      \"approve " + f["id"] + "\" or \"" + f["id"] + " failed — <what went wrong>\"")
            print("  " + "-" * (W - 4))
            print()

        for state in STATES:
            rows = by[state]
            if not rows:
                continue
            print(f"  {LABEL[state].upper()}  ({len(rows)})")
            for f in rows:
                extra = ""
                if state == "approved" and f["proven"]:
                    extra = f"   [tested {f['proven']}]"
                if state == "blocked" and f["note"]:
                    extra = f"   [{f['note'][:50]}]"
                print(f"     {f['id']}  {f['title']}{extra}")
            print()

        if unknown:
            print("  UNKNOWN STATUS — fix these:")
            for f in unknown:
                print(f"     {f['id']}  status: {f['status']!r}  (must be one of: {', '.join(STATES)})")
            print()

        nxt = by["blocked"] or by["building"] or by["awaiting-test"] or by["planned"]
        print(f"  NEXT: {nxt[0]['id']} — {nxt[0]['title']}" if nxt else "  NEXT: everything is approved.")
        print("=" * W + "\n")

    write_html(cfg, feats, by, done, total)
    return 0


HTML_TOP = """<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Feature Board</title><style>
:root{--ink:#0E2230;--mint:#54E5A0;--em:#00845F;--bg:#f6f8f8;--amber:#F0A532;--red:#D9534F}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);padding:16px;
font:16px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
h1{font-size:20px;margin:0 0 2px}.sub{color:#5a6b78;font-size:14px;margin:0 0 16px}
.bar{height:10px;border-radius:6px;background:#dde5e8;overflow:hidden;margin:0 0 20px}
.bar i{display:block;height:100%;background:var(--mint)}
.grp{font:600 11px/1 system-ui;letter-spacing:.1em;text-transform:uppercase;color:#7b8b96;margin:22px 0 8px}
.f{background:#fff;border-radius:12px;padding:13px 15px;margin:0 0 9px;
box-shadow:0 1px 3px rgba(14,34,48,.09);border-left:4px solid #dde5e8}
.f.awaiting{border-left-color:var(--amber);background:#fffaf1}
.f.approved{border-left-color:var(--em)}
.f.blocked{border-left-color:var(--red);background:#fdf3f3}
.f.building{border-left-color:#4A9FD8}
.id{font:600 11px ui-monospace,monospace;color:var(--em)}
.t{font-weight:650;margin:1px 0 0}
.m{font-size:13px;color:#5a6b78;margin-top:5px}
.cta{background:#0E2230;color:#fff;border-radius:12px;padding:16px;margin:0 0 18px}
.cta b{color:var(--mint)}.cta a{color:var(--mint)}
code{background:#0E2230;color:#8ff0c0;padding:2px 7px;border-radius:5px;font-size:13px}
</style></head><body>
<h1>Feature Board</h1>"""


def write_html(cfg, feats, by, done, total) -> None:
    pct = int(100 * done / total) if total else 0
    parts = [HTML_TOP,
             f'<p class="sub">{done} of {total} features approved by you.</p>',
             f'<div class="bar"><i style="width:{pct}%"></i></div>']

    waiting = by["awaiting-test"]
    if waiting:
        f = waiting[0]
        link = f'<a href="{html.escape(f["url"])}">{html.escape(f["url"])}</a>' if f["url"] else "(no link yet)"
        parts.append(
            f'<div class="cta"><b>WAITING FOR YOU</b><div style="margin-top:6px">'
            f'{html.escape(f["id"])} — {html.escape(f["title"])}</div>'
            f'<div style="margin-top:8px;font-size:14px">Open {link}, do the three ticks in '
            f'proof-cards.html, then tell me <code>approve {html.escape(f["id"])}</code> '
            f'or what went wrong.</div></div>'
        )

    for state in STATES:
        rows = by[state]
        if not rows:
            continue
        parts.append(f'<div class="grp">{html.escape(LABEL[state])} ({len(rows)})</div>')
        for f in rows:
            meta = ""
            if state == "approved" and f["proven"]:
                meta = f'<div class="m">You tested it on {html.escape(f["proven"])}. It is now on the never-break list.</div>'
            if state == "blocked" and f["note"]:
                meta = f'<div class="m">You reported: {html.escape(f["note"])}</div>'
            parts.append(
                f'<div class="f {state.replace("-", "")}"><div class="id">{html.escape(f["id"])}</div>'
                f'<div class="t">{html.escape(f["title"])}</div>{meta}</div>'
            )
    parts.append("</body></html>")
    (Path(cfg["_root"]) / "feature-board.html").write_text("\n".join(parts), encoding="utf-8")


# ---------------------------------------------------------------------------
# Transitions
# ---------------------------------------------------------------------------

def in_flight(cfg, exclude: str = "") -> list[dict]:
    return [f for f in load_all(cfg)
            if f["status"] in IN_FLIGHT and f["id"].lower() != exclude.lower()]


def start(cfg, fid: str) -> int:
    blockers = in_flight(cfg, exclude=fid)
    if blockers:
        b = blockers[0]
        print(f"""
  CANNOT START {fid.upper()}.

  {b['id']} — {b['title']}
  is {MID_SENTENCE[b['status']]}.

  One thing at a time is the whole point. Finish that one first: if it is waiting
  for you, test it and say approve; if it failed, tell me what went wrong.
""")
        return 1
    f = find(cfg, fid)
    set_fields(f["path"], status="building")
    print(f"\n  Started {f['id']} — {f['title']}\n  Nothing else can start until you have tested this one.\n")
    return board(cfg)


def built(cfg, fid: str, url: str = "") -> int:
    f = find(cfg, fid)
    if f["status"] != "building":
        print(f"\n  {f['id']} is '{f['status']}', not 'building'. Start it first.\n")
        return 1
    fields = {"status": "awaiting-test"}
    if url:
        fields["live_url"] = url
    set_fields(f["path"], **fields)
    print(f"""
  {f['id']} is built and live. It is now YOUR turn.

    1. Open {url or '(the live URL)'}
    2. Open proof-cards.html and do the three ticks:
         works · survives reload · survives another device
    3. Tell me "approve {f['id']}" — or what went wrong.

  I cannot start anything else until you do.
""")
    return board(cfg, quiet=True)


def approve(cfg, fid: str, by_who: str = "Hadi") -> int:
    f = find(cfg, fid)
    if f["status"] != "awaiting-test":
        print(f"\n  {f['id']} is '{f['status']}'. Only something waiting for your test can be approved.\n")
        return 1
    set_fields(f["path"], status="approved", verified_by=by_who,
               last_proven_at=str(date.today()), review_note='""')
    add_golden_path(cfg, f)
    print(f"""
  {f['id']} APPROVED — {f['title']}

  Locked. It has been added to the never-break list, so it gets re-tested after
  every future change from now on, forever.
""")
    return board(cfg)


def reject(cfg, fid: str, why: str) -> int:
    f = find(cfg, fid)
    if not why.strip():
        print("\n  Say what went wrong. 'It doesn't work' cannot be acted on.\n")
        return 2
    set_fields(f["path"], status="blocked", review_note=f'"{why.strip()}"')
    print(f"""
  {f['id']} marked as failed your test.

  You reported: {why.strip()}

  I will reproduce it before changing anything — a fix for a problem I cannot
  reproduce is a guess, and a guess adds a second problem on top of the first.
""")
    return board(cfg, quiet=True)


def add_golden_path(cfg, f: dict) -> None:
    """An approved feature must never silently break again."""
    p = Path(cfg["_root"]) / "regression" / "GOLDEN-PATHS.csv"
    p.parent.mkdir(exist_ok=True)
    if not p.exists():
        p.write_text("id,order,flow,why_it_must_never_break,how_to_test,last_run,result\n", encoding="utf-8")
    body = p.read_text(encoding="utf-8")
    if f["id"] in body:
        return
    order = body.count("\n")
    title = f["title"].replace(",", ";")
    with p.open("a", encoding="utf-8") as fh:
        fh.write(f'{f["id"]},{order},{title},"Approved by you on {date.today()}",'
                 f'"See proof-cards.html for {f["id"]}",,\n')


# ---------------------------------------------------------------------------

USAGE = """
  python3 scripts/feature.py board
  python3 scripts/feature.py start   FEAT-0007
  python3 scripts/feature.py built   FEAT-0007 --url https://...
  python3 scripts/feature.py approve FEAT-0007 [--by Hadi]
  python3 scripts/feature.py reject  FEAT-0007 --why "what went wrong"
"""


def main() -> int:
    args = sys.argv[1:]
    if not args:
        print(USAGE)
        return 2
    cfg = load_config()
    cmd = args[0]

    def opt(name, default=""):
        return args[args.index(name) + 1] if name in args and args.index(name) + 1 < len(args) else default

    if cmd == "board":
        return board(cfg)
    if len(args) < 2:
        print(USAGE)
        return 2
    fid = args[1]

    if cmd == "start":
        return start(cfg, fid)
    if cmd == "built":
        return built(cfg, fid, opt("--url"))
    if cmd == "approve":
        return approve(cfg, fid, opt("--by", "Hadi"))
    if cmd == "reject":
        return reject(cfg, fid, opt("--why"))
    print(USAGE)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
