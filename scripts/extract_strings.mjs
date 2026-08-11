#!/usr/bin/env node
/**
 * =============================================================================
 * extract_strings.mjs — pull every hard-coded piece of text out of the code and
 * into the content table, so it becomes editable without a developer.
 * =============================================================================
 *
 * WHAT IT IS FOR
 * --------------
 * Run this ONCE per existing product, right after installing
 * sql/01_content_and_roles.sql. It finds every user-facing string sitting inside
 * the code, proposes a key for each, and writes two files:
 *
 *   content-import.sql   the INSERT statements — review, then run
 *   content-replace.md   the exact find/replace list to turn each string into t('key')
 *
 * WHY IT MATTERS
 * --------------
 * Until a string is a row in a table, changing it requires a code edit and a
 * deploy. That is how every payment link in a live product came to read
 * PAY-LINK-HERE with no way to fix it in the app — two runbooks said to paste the
 * real link "in the Control Room", and the Control Room had no editor.
 *
 * IT DELIBERATELY DOES NOT EDIT YOUR CODE
 * ---------------------------------------
 * It proposes. You (or Claude, with you watching) apply. An automated rewrite of
 * every string in a codebase is exactly the kind of large blind edit this whole
 * system exists to prevent.
 *
 * USAGE:  node scripts/extract_strings.mjs
 * =============================================================================
 */

import fs from 'node:fs';
import path from 'node:path';

const ROOT = process.cwd();
const cfg = JSON.parse(fs.readFileSync(path.join(ROOT, 'oggi-build.config.json'), 'utf8'));
const IGNORE = new Set(cfg.ignore_dirs || ['node_modules', '.git', 'dist', 'build']);
const EXTS = new Set(['.html', '.js', '.mjs', '.jsx', '.ts', '.tsx', '.vue', '.svelte']);

// ---------------------------------------------------------------------------
// What counts as user-facing text
// ---------------------------------------------------------------------------
// Deliberately conservative. A false positive here creates noise in the import
// file, which makes the review tedious, which means the review does not happen.
const LOOKS_LIKE_PROSE = (s) =>
  s.length >= 3 &&
  s.length <= 400 &&
  /[a-zA-Z]/.test(s) &&
  /\s|[.!?,:]/.test(s) === (s.split(' ').length > 1) &&  // single words allowed too
  !/^[a-z0-9_-]+$/.test(s) &&                            // not an identifier / css class
  !/^(https?:|\/|\.|#|data:|[a-z-]+\/[a-z-]+$)/i.test(s) && // not a url / path / mime
  !/^[{[<]/.test(s) &&                                   // not json / markup
  !/^\d+(px|rem|em|%|vh|vw|ms|s)?$/.test(s) &&           // not a measurement
  !/^[A-Z_]+$/.test(s);                                  // not a CONSTANT

// Where strings live
const JSX_TEXT      = />([^<>{}\n]{3,200})</g;                    // >Place order<
const ATTR_TEXT     = /\b(?:placeholder|title|alt|aria-label|value)\s*=\s*"([^"]{3,200})"/g;
const JS_STRING     = /(?:^|[=(,:[\s])(['"])((?:(?!\1)[^\\\n]|\\.){3,200})\1/g;

// Money and links get a different `kind`, which locks them to admin+ forever.
const kindOf = (s) =>
  /^\$?\d+([.,]\d+)?$/.test(s.trim())                    ? 'price'
  : /^(https?:\/\/|mailto:|tel:|whatsapp:)/i.test(s)     ? 'link'
  : s.length > 120                                        ? 'longtext'
  : 'text';

const namespaceOf = (file) =>
  /market|land|home|pricing|hero|cta/i.test(file) ? 'marketing'
  : /help|onboard|tooltip|faq/i.test(file)        ? 'help'
  : /legal|terms|privacy|policy/i.test(file)      ? 'legal'
  : /email|mail|whatsapp|notif/i.test(file)       ? 'email'
  : 'product';

// ---------------------------------------------------------------------------
function walk(dir, out = []) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (entry.name.startsWith('.') || IGNORE.has(entry.name)) continue;
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) walk(full, out);
    else if (EXTS.has(path.extname(entry.name))) out.push(full);
  }
  return out;
}

const slug = (file, s) => {
  const area = path.basename(file, path.extname(file)).replace(/[^a-z0-9]+/gi, '_').toLowerCase();
  const word = s.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '').split('_').slice(0, 4).join('_');
  return `${area}.${word || 'text'}`.slice(0, 60);
};

const found = new Map();   // key -> { value, file, kind, namespace, occurrences }

for (const file of walk(ROOT)) {
  const rel = path.relative(ROOT, file);
  const text = fs.readFileSync(file, 'utf8');
  const hits = new Set();

  for (const re of [JSX_TEXT, ATTR_TEXT, JS_STRING]) {
    re.lastIndex = 0;
    let m;
    while ((m = re.exec(text))) {
      const s = (m[2] ?? m[1] ?? '').trim();
      if (s && LOOKS_LIKE_PROSE(s)) hits.add(s);
    }
  }

  for (const s of hits) {
    let key = slug(rel, s);
    let n = 1;
    while (found.has(key) && found.get(key).value !== s) key = `${slug(rel, s)}_${++n}`;
    const existing = found.get(key);
    if (existing) { existing.occurrences++; continue; }
    found.set(key, { value: s, file: rel, kind: kindOf(s), namespace: namespaceOf(rel), occurrences: 1 });
  }
}

// ---------------------------------------------------------------------------
// Write the two output files
// ---------------------------------------------------------------------------
const esc = (s) => s.replace(/'/g, "''");

const sql = [
  '-- content-import.sql — GENERATED by scripts/extract_strings.mjs',
  '-- REVIEW BEFORE RUNNING. Two things to check:',
  '--   1. Key names are how you will find things in the editor later.',
  '--      checkout.subscribe_button beats page_47.text_3. Rename freely.',
  '--   2. Anything marked kind=price or kind=link is locked to admin+ forever.',
  '--      That is deliberate — those are the two field types where a mistake',
  '--      costs money directly.',
  '',
  'insert into content_string (key, namespace, kind, label, hint, draft_value, published_value, status) values',
];
const rows = [...found.entries()].map(([key, d]) =>
  `  ('${esc(key)}', '${d.namespace}', '${d.kind}', '${esc(d.value.slice(0, 60))}', ` +
  `'appears in ${esc(d.file)}${d.occurrences > 1 ? ` (${d.occurrences} places)` : ''}', ` +
  `'${esc(d.value)}', '${esc(d.value)}', 'published')`
);
sql.push(rows.join(',\n') + '\non conflict (key) do nothing;');
fs.writeFileSync(path.join(ROOT, 'content-import.sql'), sql.join('\n'), 'utf8');

const md = [
  '# Replace these in the code with t(\'key\')',
  '',
  'Do this **file by file**, checking the site still looks identical after each one.',
  'Do NOT do all of them in one pass — a single large blind edit across every file is',
  'exactly the kind of change this system exists to prevent.',
  '',
  '| File | Find this text | Replace with |',
  '|---|---|---|',
  ...[...found.entries()].map(([key, d]) =>
    `| \`${d.file}\` | ${d.value.slice(0, 70).replace(/\|/g, '\\|')} | \`t('${key}')\` |`),
  '',
  '## After every file',
  '',
  '```',
  'just check',
  '```',
  '',
  '## When the last file is done',
  '',
  'Turn on the no-literal-string lint for UI files. From then on, a new hard-coded',
  'string fails the build — so this migration never has to be done twice.',
];
fs.writeFileSync(path.join(ROOT, 'content-replace.md'), md.join('\n'), 'utf8');

console.log(`
  Found ${found.size} pieces of user-facing text.

    content-import.sql   the database rows  — review the key names, then run
    content-replace.md   the find/replace list — do it one file at a time

  Nothing in your code was changed. That is deliberate.
`);
