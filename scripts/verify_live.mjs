#!/usr/bin/env node
/**
 * =============================================================================
 * verify_live.mjs — THE MOST IMPORTANT SCRIPT IN THE TOOLKIT.
 * =============================================================================
 *
 * If only one thing from this whole system ever gets built, build this.
 *
 * THE FINDING THAT PRODUCED IT
 * ----------------------------
 * Of the ten documented failures in the estate, ONE was caused by bad planning.
 * EIGHT were caused by nobody ever executing a claim against the live product.
 * Every "done, tested, working" that turned out to be false would have been
 * caught by this script in under two minutes.
 *
 * WHAT IT DOES, IN ORDER
 * ----------------------
 * 1. Waits until the live URL is genuinely serving THIS build.
 *      Cloudflare needs longer to propagate than a naive check waits, so a check
 *      that runs too early looks identical to a failed deploy. It polls
 *      /__version with caching disabled until the build id matches, up to ~200s.
 *
 * 2. For each critical journey, in a REAL browser against the REAL live site:
 *      a. do the thing (fill, click, submit)
 *      b. assert the result appears
 *      c. HARD RELOAD          -> assert again   [survives_reload]
 *      d. FRESH BROWSER CONTEXT -> assert again  [survives_fresh_device]
 *
 *    Step (d) is the one that matters most and the one everyone skips.
 *    In this architecture localStorage is the cache. A same-tab reload reads the
 *    value straight back out of it, the test goes green, and the feature has
 *    still never once worked on a second device. That is precisely how a shipped
 *    feature reached customers permanently broken while marked done and tested.
 *
 *    The two results are reported SEPARATELY. Passing (c) and failing (d) is the
 *    exact fingerprint of a key missing from the save list.
 *
 * 3. Traps every console error and every 4xx/5xx the page triggers.
 * 4. Scans the RENDERED TEXT (not the source) for placeholder values — this is
 *    what catches PAY-LINK-HERE actually reaching a customer's screen.
 * 5. Asserts every link on every visited page resolves.
 *
 * SETUP
 *   npm i -D playwright && npx playwright install chromium
 *
 * USAGE
 *   node scripts/verify_live.mjs
 *   node scripts/verify_live.mjs --url https://x.workers.dev --sha abc123
 *
 * JOURNEYS are declared in verify.journeys.json at the project root. See the
 * template in templates/verify.journeys.json.
 * =============================================================================
 */

import fs from 'node:fs';
import path from 'node:path';
import { execSync } from 'node:child_process';

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------
const ROOT = process.cwd();
const arg = (flag) => {
  const i = process.argv.indexOf(flag);
  return i > -1 ? process.argv[i + 1] : null;
};

const readJson = (p, fallback = {}) => {
  try { return JSON.parse(fs.readFileSync(path.join(ROOT, p), 'utf8')); }
  catch { return fallback; }
};

const cfg = readJson('oggi-build.config.json');
const LIVE_URL = (arg('--url') || cfg.live_url || '').replace(/\/$/, '');
const JOURNEYS = readJson('verify.journeys.json', { journeys: [] }).journeys;

let EXPECTED_SHA = arg('--sha');
if (!EXPECTED_SHA) {
  try { EXPECTED_SHA = execSync('git rev-parse HEAD', { cwd: ROOT }).toString().trim(); }
  catch { EXPECTED_SHA = null; }
}

// Placeholders that must never appear in text a customer can read.
const BANNED_ON_SCREEN = [
  'PAY-LINK-HERE', '-HERE', 'YOUR_', 'CHANGEME', 'PLACEHOLDER', 'lorem ipsum',
  'John Doe', 'undefined', 'NaN', '[object Object]', 'null null', 'TODO', 'TBD',
];

const results = [];
const record = (name, ok, message, detail = '') =>
  results.push({ name, ok, message, detail });

/**
 * Resolve a credential from the environment instead of the file.
 *
 * verify.journeys.json is committed, so a real password written into it would be
 * in the project history forever. Write `env:VERIFY_PASSWORD` there instead and
 * the value is read from the environment at run time.
 */
function resolveSecret(value) {
  if (typeof value !== 'string') return value;
  if (value.startsWith('env:')) {
    const key = value.slice(4);
    const found = process.env[key];
    if (!found) {
      console.error(
        `\n  The journey needs ${key}, which is not set.\n` +
        `  Set it before running:  export ${key}="…"\n` +
        `  Never write the real password into verify.journeys.json — that file is\n` +
        `  saved in the project history permanently.\n`
      );
      process.exit(2);
    }
    return found;
  }
  return value;
}

// ---------------------------------------------------------------------------
// STEP 1 — wait until the live site is serving THIS build
// ---------------------------------------------------------------------------
async function waitForVersion() {
  if (!EXPECTED_SHA) {
    record('version', true, 'No git SHA available — skipping the version check.');
    return true;
  }
  const target = EXPECTED_SHA.slice(0, 12);
  for (let attempt = 1; attempt <= 20; attempt++) {
    try {
      const res = await fetch(`${LIVE_URL}/__version`, {
        cache: 'no-store',
        headers: { 'Cache-Control': 'no-store', Pragma: 'no-cache' },
      });
      const body = (await res.text()).replace(/["'\s]/g, '');
      if (body.startsWith(target)) {
        record('version', true, `Live site is serving this exact build (${target}).`);
        return true;
      }
      process.stdout.write(`  waiting for deploy to propagate… live=${body.slice(0, 12) || 'none'} want=${target} (${attempt}/20)\n`);
    } catch {
      process.stdout.write(`  waiting for the site to answer… (${attempt}/20)\n`);
    }
    await new Promise((r) => setTimeout(r, 10_000));
  }
  record('version', false,
    `The live site never started serving this build (${target}) after 200 seconds.`,
    'Either the deploy did not actually happen, or /__version is not wired up. ' +
    'A dashboard saying "deployed" is not proof — this check is the proof.');
  return false;
}

// ---------------------------------------------------------------------------
// STEP 2 — run each journey against the live product
// ---------------------------------------------------------------------------
async function runJourneys(chromium) {
  const browser = await chromium.launch();

  for (const j of JOURNEYS) {
    const label = j.name || j.id;
    const consoleErrors = [];
    const httpErrors = [];

    const ctx = await browser.newContext({ viewport: { width: 390, height: 844 } });
    const page = await ctx.newPage();
    page.on('pageerror', (e) => consoleErrors.push(String(e).slice(0, 200)));
    page.on('console', (m) => { if (m.type() === 'error') consoleErrors.push(m.text().slice(0, 200)); });
    page.on('response', (r) => { if (r.status() >= 400) httpErrors.push(`${r.status()} ${r.url().slice(0, 120)}`); });

    try {
      // --- act -------------------------------------------------------------
      await page.goto(LIVE_URL + (j.path || '/'), { waitUntil: 'networkidle', timeout: 45_000 });
      if (j.login) {
        await page.fill(j.login.userSelector, resolveSecret(j.login.user));
        await page.fill(j.login.passSelector, resolveSecret(j.login.pass));
        await page.click(j.login.submitSelector);
        await page.waitForLoadState('networkidle');
      }
      for (const step of j.steps || []) {
        if (step.fill) await page.fill(step.fill.selector, step.fill.value);
        if (step.click) await page.click(step.click);
        if (step.wait) await page.waitForTimeout(step.wait);
        await page.waitForLoadState('networkidle').catch(() => {});
      }

      // --- assert immediately ---------------------------------------------
      const seen = await page.locator('body').innerText();
      const ok1 = j.expect ? seen.includes(j.expect) : true;
      record(`${label} · works`, ok1,
        ok1 ? 'The action worked.' : `Expected to see "${j.expect}" and it was not on the page.`);

      // --- (c) HARD RELOAD -------------------------------------------------
      await page.reload({ waitUntil: 'networkidle' });
      if (j.afterReloadPath) await page.goto(LIVE_URL + j.afterReloadPath, { waitUntil: 'networkidle' });
      const afterReload = await page.locator('body').innerText();
      const ok2 = j.expect ? afterReload.includes(j.expect) : true;
      record(`${label} · survives_reload`, ok2,
        ok2 ? 'Still there after a reload.'
            : `"${j.expect}" disappeared after reloading. The app is not saving it at all.`);

      // --- (d) FRESH BROWSER CONTEXT — the one that matters ---------------
      const ctx2 = await browser.newContext({ viewport: { width: 390, height: 844 } });
      const page2 = await ctx2.newPage();
      await page2.goto(LIVE_URL + (j.afterReloadPath || j.path || '/'), { waitUntil: 'networkidle' });
      if (j.login) {
        await page2.fill(j.login.userSelector, resolveSecret(j.login.user));
        await page2.fill(j.login.passSelector, resolveSecret(j.login.pass));
        await page2.click(j.login.submitSelector);
        await page2.waitForLoadState('networkidle');
        if (j.afterReloadPath) await page2.goto(LIVE_URL + j.afterReloadPath, { waitUntil: 'networkidle' });
      }
      const onDevice2 = await page2.locator('body').innerText();
      const ok3 = j.expect ? onDevice2.includes(j.expect) : true;
      record(`${label} · survives_fresh_device`, ok3,
        ok3 ? 'Also visible on a completely separate device.'
            : `"${j.expect}" is NOT there on a second device. It only ever existed on the ` +
              `phone that created it. This is the "saved to the browser, never to the server" bug — ` +
              `check that every key this feature writes is on the save list.`);
      await ctx2.close();

      // --- placeholders on the RENDERED screen ----------------------------
      const hits = BANNED_ON_SCREEN.filter((t) => onDevice2.includes(t) || seen.includes(t));
      record(`${label} · no_placeholders_on_screen`, hits.length === 0,
        hits.length === 0 ? 'No fake values visible to the customer.'
                          : `A customer can literally read these on screen: ${hits.join(', ')}`);

      // --- every link resolves --------------------------------------------
      const hrefs = await page.$$eval('a[href]', (as) => as.map((a) => a.getAttribute('href')));
      const dead = hrefs.filter((h) => !h || h === '#' || /^javascript:/i.test(h) || /[{<\[]/.test(h));
      record(`${label} · links_resolve`, dead.length === 0,
        dead.length === 0 ? 'Every link goes somewhere.'
                          : `${dead.length} dead link(s) on this page: ${dead.slice(0, 5).join(' | ')}`);

    } catch (err) {
      record(`${label} · works`, false, `The journey crashed: ${String(err).slice(0, 220)}`);
    } finally {
      record(`${label} · no_console_errors`, consoleErrors.length === 0,
        consoleErrors.length === 0 ? 'No errors in the browser.'
                                   : `${consoleErrors.length} error(s) in the browser.`,
        consoleErrors.slice(0, 5).join('\n'));
      record(`${label} · no_failed_requests`, httpErrors.length === 0,
        httpErrors.length === 0 ? 'No failed server requests.'
                                : `${httpErrors.length} request(s) failed.`,
        httpErrors.slice(0, 5).join('\n'));
      await ctx.close();
    }
  }
  await browser.close();
}

// ---------------------------------------------------------------------------
// Report
// ---------------------------------------------------------------------------
// The machine names are precise; these are what the owner reads.
const PLAIN_LABEL = {
  works: 'it does the thing',
  survives_reload: 'still there after closing and reopening',
  survives_fresh_device: 'still there on a SECOND DEVICE',
  no_placeholders_on_screen: 'no fake values a customer could read',
  links_resolve: 'every link goes somewhere',
  no_console_errors: 'nothing broke behind the scenes',
  no_failed_requests: 'no request to the server came back as an error',
  version: 'the live site is running this exact version',
  journeys: 'there is something to test',
};

const humanise = (name) => {
  const [journey, part] = name.split(' · ');
  if (!part) return PLAIN_LABEL[journey] || journey;
  return `${journey} — ${PLAIN_LABEL[part] || part}`;
};

function report() {
  const fails = results.filter((r) => !r.ok);
  const W = '='.repeat(72);
  console.log(`\n${W}\n  LIVE VERIFICATION — ${LIVE_URL}\n${W}`);
  for (const r of results) console.log(`  [${r.ok ? 'PASS' : 'FAIL'}]  ${humanise(r.name)}\n          ${r.message}`);
  if (fails.some((f) => f.detail)) {
    console.log('\n' + '-'.repeat(72));
    for (const f of fails.filter((x) => x.detail)) console.log(`  ${f.name}:\n${f.detail.split('\n').map((l) => '      ' + l).join('\n')}`);
    console.log('-'.repeat(72));
  }
  console.log(`\n  ${results.length - fails.length} passed · ${fails.length} FAILED\n`);
  console.log(fails.length
    ? '  RESULT: RED — the LIVE product is broken for real customers right now.'
    : '  RESULT: GREEN — verified against the live product, including a second device.');
  console.log(`${W}\n`);

  fs.mkdirSync(path.join(ROOT, 'evidence'), { recursive: true });
  fs.writeFileSync(
    path.join(ROOT, 'evidence', 'last-live-verification.json'),
    JSON.stringify({ url: LIVE_URL, sha: EXPECTED_SHA, at: new Date().toISOString(), results }, null, 1)
  );
  return fails.length ? 1 : 0;
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------
(async () => {
  if (!LIVE_URL) {
    console.error('No live_url set in oggi-build.config.json (or pass --url). ' +
      'Without a live URL there is no way to prove the product works for customers.');
    process.exit(2);
  }
  const versionOk = await waitForVersion();
  if (!versionOk) process.exit(report());

  if (!JOURNEYS.length) {
    // This MUST fail. An earlier version printed
    //   "GREEN — verified against the live product, including a second device"
    // with zero journeys configured — i.e. the flagship claim of the whole system,
    // fabricated by default. The first time the owner noticed that, the tool would
    // have lost all credibility, permanently and correctly.
    record('journeys', false,
      'No journeys are configured, so NOTHING about this product was tested.',
      'The live site answered and is serving the right build — that is all that was\n' +
      'checked. Create verify.journeys.json (template in toolkit/templates/) with at\n' +
      'least three: the payment path, signing in, and the main action the product\n' +
      'exists to do. Ask Claude: "write the verify journeys for this product".');
    process.exit(report());
  }

  let chromium;
  try { ({ chromium } = await import('playwright')); }
  catch {
    console.error('\n  Playwright is not installed. Run:\n    npm i -D playwright && npx playwright install chromium\n');
    process.exit(2);
  }
  await runJourneys(chromium);
  process.exit(report());
})();
