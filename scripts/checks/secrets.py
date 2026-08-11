"""
secrets.py — "is a password or key sitting in the code?"

THE FAILURE THIS PREVENTS
-------------------------
Live in the estate at the time of the audit:
  - An admin password that sat in a product document in plaintext (must now be
    treated as leaked).
  - Plaintext rep passwords syncing into a shared document readable by every
    authenticated tenant.
  - Logins hard-coded in page source, including 'zzz' and 'sample'/'sample'.

Anything in front-end source is public. There is no such thing as a secret in a
page a customer can view-source.
"""

from __future__ import annotations

import re

from ._common import FAIL, PASS, Result, code_lines, is_exempt, iter_source_files, read, rel

NAME = "secrets"
PLAIN = "No passwords, keys or service credentials sitting in the code"

PATTERNS = [
    # No \b before the word: ADMIN_PASSWORD has no word boundary before "PASSWORD"
    # because '_' counts as a word character. That gap is how 'zzz' shipped live.
    (re.compile(r"\w*(?:password|passwd|pwd|passcode)\s*[:=]\s*['\"][^'\"]{2,}['\"]", re.I), "a literal password"),
    (re.compile(r"\bservice_role\b", re.I), "a Supabase SERVICE ROLE key (full database access — never in front-end code)"),
    (re.compile(r"\bsk_live_[A-Za-z0-9]{8,}"), "a live secret payment key"),
    (re.compile(r"\bsk-[A-Za-z0-9]{20,}"), "an API secret key"),
    (re.compile(r"\bghp_[A-Za-z0-9]{20,}"), "a GitHub token"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "an AWS access key"),
    (re.compile(r"eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}"), "a JWT token"),
    (re.compile(r"\b(api_?key|secret|token)\s*[:=]\s*['\"][A-Za-z0-9_\-]{16,}['\"]", re.I), "an API key or secret"),
]

# Lines that legitimately mention these words without holding a secret.
ALLOW = re.compile(
    r"(process\.env|Deno\.env|import\.meta\.env|os\.environ|getenv|"
    r"type\s*=\s*[\"']password|placeholder|\bPATTERNS\b|example|\*\*\*|xxxx|redacted)",
    re.I,
)


def _inside_string_literal(line: str, pos: int) -> bool:
    """Is this match a LABEL inside a string rather than a real value?

    Real code frequently builds credential-handoff messages:

        var text = 'Password: ' + r.password;

    The word 'Password' there sits inside a string literal, followed by a colon
    and the closing quote — which matches the naive pattern exactly. Three such
    lines in a real codebase were reported as hardcoded credentials, which is a
    false positive, which is the one failure mode that gets a gate deleted.

    An odd number of unescaped quotes before the match means we are inside a
    string, so the word is a label, not an assignment target.
    """
    prefix = line[:pos]
    for q in ("'", '"', "`"):
        if prefix.count(q) - prefix.count("\\" + q) % 2 != 0:
            pass
    singles = prefix.count("'") - prefix.count("\\'")
    doubles = prefix.count('"') - prefix.count('\\"')
    return (singles % 2 == 1) or (doubles % 2 == 1)


def run(cfg: dict) -> Result:
    problems = []
    for path in iter_source_files(cfg):
        if is_exempt(cfg, path) or "secrets.py" in str(path):
            continue
        for lineno, line in code_lines(read(path)):
            if ALLOW.search(line):
                continue
            for pat, what in PATTERNS:
                m = pat.search(line)
                if m:
                    if what == "a literal password" and _inside_string_literal(line, m.start()):
                        continue   # a label in a message, not a stored secret
                    problems.append(
                        f"{rel(cfg, path)}:{lineno}  →  {what}\n      {line.strip()[:120]}"
                    )
                    break

    if not problems:
        return Result(NAME, PASS, "No credentials found in the code.")

    return Result(
        NAME,
        FAIL,
        f"{len(problems)} credential(s) are sitting in the code where anyone can read them. "
        f"Fix: move each one to an environment variable, then TREAT THE OLD VALUE AS LEAKED "
        f"and change it — removing it from the file does not un-leak it.",
        problems[:30],
    )
