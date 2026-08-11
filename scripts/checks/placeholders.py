"""
placeholders.py — "did we ship a fake value to a real customer?"

THE FAILURE THIS PREVENTS
-------------------------
Every Subscribe button in a live OGGI product once pointed at the literal URL
`https://whish.money/PAY-LINK-HERE`. A portfolio link rendered on screen as the
literal text `[Portfolio Builder file]?p=<token>`. Both were shipped, both were
customer-facing, and neither was noticed because nothing ever looked.

This check looks. It runs on the source, and (via live_scan) on the actual bytes
the live server serves — because those two are not always the same thing.

WHY THE LIST IS FIXED AND SHORT
-------------------------------
One false alarm and the owner learns the gate lies, then routes around it
forever. So every token here is a string that has NO legitimate reason to reach
a customer. Anything ambiguous belongs in extra_placeholders, not here.
"""

from __future__ import annotations

import re

from ._common import FAIL, PASS, Result, code_lines, is_exempt, iter_source_files, read, rel

NAME = "placeholders"
PLAIN = "No fake / leftover values (PAY-LINK-HERE, TODO, lorem ipsum) reaching a customer"

# Tokens that must never appear in a value a customer can see or click.
#
# CASE-INSENSITIVE tokens: unambiguous in any casing.
BANNED = [
    "PAY-LINK-HERE",
    "CHANGEME",
    "CHANGE_ME",
    "REPLACE_ME",
    "lorem ipsum",
    "sk_test_",           # a test payment key in production is a live incident
    "pk_test_",
    "test@test",
    "foo@bar",
]

# CASE-SENSITIVE tokens: only shouty, all-caps forms are placeholders.
# "-HERE" as a plain substring matched class="drop-here"; "YOUR_" matched
# your_account; "example.com" matched legitimate documentation links. Each of
# those was a false alarm, and false alarms are what get the gate deleted.
BANNED_EXACT = [
    "-HERE",
    "YOUR_API",
    "YOUR_URL",
    "YOUR_KEY",
    "YOUR_TOKEN",
    "PLACEHOLDER",
    "INSERT_YOUR",
    "John Doe",
    "XXXXXX",
]

# Bracketed placeholders that got rendered literally on screen, e.g.
#   [Portfolio Builder file]?p=<token>
#
# CAREFUL — the angle-bracket rule is the highest false-positive risk in the whole
# gate: <div>, <span>, <section> and every other bare HTML tag match the naive
# pattern. On a real HTML file that is hundreds of bogus failures, which teaches
# the owner that the gate lies — the one failure mode that kills adoption outright.
# So every real HTML and SVG tag name is excluded by name.
HTML_TAGS = {
    "html", "head", "body", "title", "base", "link", "meta", "style", "script", "noscript",
    "div", "span", "p", "a", "em", "strong", "small", "s", "cite", "q", "dfn", "abbr", "data",
    "time", "code", "var", "samp", "kbd", "sub", "sup", "i", "b", "u", "mark", "ruby", "rt",
    "rp", "bdi", "bdo", "br", "wbr", "ins", "del", "picture", "source", "img", "iframe",
    "embed", "object", "param", "video", "audio", "track", "map", "area", "table", "caption",
    "colgroup", "col", "tbody", "thead", "tfoot", "tr", "td", "th", "form", "label", "input",
    "button", "select", "datalist", "optgroup", "option", "textarea", "output", "progress",
    "meter", "fieldset", "legend", "details", "summary", "dialog", "slot", "template",
    "canvas", "main", "nav", "header", "footer", "section", "article", "aside", "address",
    "hgroup", "hr", "pre", "blockquote", "ol", "ul", "li", "dl", "dt", "dd", "figure",
    "figcaption", "svg", "path", "circle", "ellipse", "rect", "line", "polyline", "polygon",
    "text", "tspan", "defs", "clippath", "mask", "pattern", "marker", "symbol", "use", "g",
    "font", "center", "big", "tt", "strike", "frame", "frameset", "noframes", "applet",
}
_ANGLE = re.compile(r"</?([a-z_][a-z_-]{1,19})>")
DOUBLE_BRACE = re.compile(r"\{\{\s*[a-z_. ]+\s*\}\}")        # {{ price }} left unrendered
SQUARE_FILE = re.compile(r"\[[A-Z][A-Za-z ]{4,40}\]\s*\?")   # [Portfolio Builder file]?

# Files where {{ ... }} is the templating language, not an unrendered value.
TEMPLATE_EXTS = {".vue", ".svelte", ".hbs", ".mustache", ".liquid", ".html", ".twig", ".jinja"}

# TypeScript generics are the biggest remaining false-positive source:
# Promise<void>, Array<string>, useState<boolean>, Record<string, x>.
# Any angle token immediately preceded by an identifier character is a generic
# or a comparison, never a placeholder.
_GENERIC_CONTEXT = re.compile(r"[A-Za-z0-9_$\]\)]\s*<")


def _angle_placeholder(line: str):
    """Return the first <token> that is genuinely an unfilled placeholder.

    Excluded, because each of these produced a false alarm on real code:
      * every real HTML and SVG tag name  (<div>, <span>, <section>, <path>)
      * TypeScript generics               (Promise<void>, Array<string>)
      * lowercase single words that are also valid custom elements
    A placeholder that survives all three looks like <token>, <your_url>, <id>.
    """
    for m in _ANGLE.finditer(line):
        name = m.group(1).lower()
        if name in HTML_TAGS:
            continue
        # A generic/comparison: something identifier-ish sits just before the '<'.
        before = line[: m.start()]
        if _GENERIC_CONTEXT.search(before[-3:] + "<"):
            continue
        # Custom elements always contain a hyphen and are legitimate markup.
        if "-" in name:
            continue
        return m.group(0)
    return None

# Lines that are legitimately allowed to contain a banned token.
ALLOW_LINE = re.compile(
    r"(placeholder=|aria-placeholder|\.placeholder|BANNED|scan_placeholders|"
    r"eslint-disable|@example|/\*\s*sample)",
    re.I,
)


def _hits_in_text(text: str, suffix: str = "", extra: tuple = ()):
    """Yield (line_no, token, line) for every banned pattern in real code.

    At most ONE finding per line: PAY-LINK-HERE also matches -HERE, and the same
    line reported twice makes a small problem look like a big one.
    """
    is_template = suffix.lower() in TEMPLATE_EXTS

    for lineno, line in code_lines(text):
        if ALLOW_LINE.search(line):
            continue
        stripped = line.strip()[:160]
        upper = line.upper()

        hit = next((t for t in list(BANNED) + list(extra) if t.upper() in upper), None)
        if hit:
            yield lineno, hit, stripped
            continue

        hit = next((t for t in BANNED_EXACT if t in line), None)
        if hit:
            yield lineno, hit, stripped
            continue

        angle = _angle_placeholder(line)
        if angle:
            yield lineno, f"unfilled placeholder {angle}", stripped
            continue

        # {{ ... }} is the templating language in .vue/.html/.hbs — not a bug.
        if not is_template:
            m = DOUBLE_BRACE.search(line)
            if m:
                yield lineno, f"unrendered template value {m.group(0)}", stripped
                continue

        m = SQUARE_FILE.search(line)
        if m:
            yield lineno, f"bracketed file name rendered literally {m.group(0)}", stripped


def run(cfg: dict) -> Result:
    # Local, not appended to the module global — extending BANNED accumulated
    # duplicates across repeated in-process runs.
    extra = tuple(t for t in cfg.get("extra_placeholders", []) if t)

    problems: list[str] = []
    for path in iter_source_files(cfg):
        if is_exempt(cfg, path):
            continue
        for lineno, token, line in _hits_in_text(read(path), path.suffix, extra):
            problems.append(f"{rel(cfg, path)}:{lineno}  →  {token}\n      {line}")

    if not problems:
        return Result(NAME, PASS, "No placeholder or leftover fake values found.")

    first = problems[0].split("\n")[0]
    return Result(
        NAME,
        FAIL,
        f"{len(problems)} fake/leftover value(s) would reach a customer. "
        f"First one: {first}. Replace it with the real value, or move the file "
        f"into templates/ if it is genuinely an example.",
        problems[:40],
    )


def scan_text(body: str, source_label: str) -> list[str]:
    """Used by verify_live: scan already-fetched live bytes for the same tokens."""
    return [
        f"{source_label}:{lineno}  →  {token}\n      {line}"
        for lineno, token, line in _hits_in_text(body)
    ]
