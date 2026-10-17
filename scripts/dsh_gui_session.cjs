#!/usr/bin/env node
// Send a prepared prompt into a DSH Web workspace as a new, observable session.
//
// Why this exists: a prompt written for a product project is easier to trust
// when it runs in the workspace the owner is already watching, instead of a
// detached CLI session. This drives the real GUI with Playwright, then verifies
// from the session store that a new session appeared and received the prompt, so
// a caller never has to claim success from a click alone.
//
// Usage:
//   node scripts/dsh_gui_session.cjs --list
//   node scripts/dsh_gui_session.cjs --dry-run <Workspace title>
//   node scripts/dsh_gui_session.cjs <Workspace title> <prompt file> [...]
//
// The GUI origin and login token come from /run/huou07-dsh-link/url, which the
// H07P launcher refreshes; the token is never printed. Workspace titles are the
// GUI's own names (OR, VCE, H07P, AEH).
//
// Exit codes: 0 verified, 1 usage or verification failure, 2 environment
// problem (no token, no browser, GUI unreachable).

const fs = require('fs');
const os = require('os');
const path = require('path');
const { execFileSync } = require('child_process');

const TOKEN_FILE = process.env.DSH_URL_FILE || '/run/huou07-dsh-link/url';
const STORE = path.join(os.homedir(), '.dsh', 'storages', 'workspace.json');
const SESSIONS = path.join(os.homedir(), '.dsh', 'sessions');
const HOST = process.env.DSH_WEB_HOST || 'http://127.0.0.1:3080';

function playwright() {
  const candidates = [
    path.join(os.homedir(), '.local/share/playwright-cli/node_modules/playwright'),
    'playwright',
  ];
  for (const c of candidates) {
    try { return require(c); } catch { /* try next */ }
  }
  console.error('no playwright module found; install it in ~/.local/share/playwright-cli');
  process.exit(2);
}

// The installed playwright may ask for a headless-shell build the cache does not
// have. Point it at a real chromium from the cache instead of failing.
function chromiumPath() {
  const root = process.env.PLAYWRIGHT_BROWSERS_PATH ||
    path.join(os.homedir(), '.cache/ms-playwright');
  let best = null;
  for (const entry of fs.readdirSync(root)) {
    const m = /^chromium-(\d+)$/.exec(entry);
    if (!m) continue;
    for (const rel of ['chrome-linux64/chrome', 'chrome-linux/chrome']) {
      const p = path.join(root, entry, rel);
      if (fs.existsSync(p) && (!best || Number(m[1]) > best.rev)) best = { rev: Number(m[1]), p };
    }
  }
  if (!best) { console.error('no chromium build under', root); process.exit(2); }
  return best.p;
}

function readStore() {
  try { return JSON.parse(fs.readFileSync(STORE, 'utf8')); } catch { return null; }
}

function workspaces() {
  const store = readStore();
  if (!store) return [];
  return Object.values(store.tables.workspaces)
    .map(w => ({ title: w.title, path: w.path, sessions: w.sessionIds.length }));
}

function sessionIdsFor(title) {
  const store = readStore();
  const w = Object.values(store.tables.workspaces).find(x => x.title === title);
  return w ? w.sessionIds : null;
}

function promptMarker(text) {
  for (const line of text.split('\n')) {
    const t = line.replace(/^#+\s*/, '').trim();
    if (t.length >= 20) return t.slice(0, 60);
  }
  return text.trim().slice(0, 60);
}

async function main() {
  const args = process.argv.slice(2);
  const listing = args.includes('--list');
  const dryRun = args.includes('--dry-run');
  const positional = args.filter(a => !a.startsWith('--'));

  if (listing) {
    for (const w of workspaces()) console.log(`${w.title}\t${w.path}\t${w.sessions} session(s)`);
    return 0;
  }
  if (positional.length < 1) {
    console.error('usage: dsh_gui_session.cjs [--list|--dry-run] <Workspace title> [prompt file ...]');
    return 1;
  }
  const title = positional[0];
  const files = positional.slice(1);
  if (!files.length && !dryRun) { console.error('no prompt file given'); return 1; }
  const text = files.map(f => fs.readFileSync(f, 'utf8')).join('\n\n');

  if (!fs.existsSync(TOKEN_FILE)) { console.error('missing login link:', TOKEN_FILE); return 2; }
  const token = fs.readFileSync(TOKEN_FILE, 'utf8').trim();
  const before = sessionIdsFor(title);
  if (!before) { console.error(`unknown workspace title "${title}"; try --list`); return 1; }

  const { chromium } = playwright();
  const browser = await chromium.launch({ headless: true, executablePath: chromiumPath() });
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 950 } });
    await page.goto(HOST + token, { waitUntil: 'load', timeout: 60000 });
    await page.waitForTimeout(6000);

    const label = `New session in ${title}`;
    const present = await page.evaluate(l => !!document.querySelector(`[aria-label="${l}"]`), label);
    if (!present) {
      console.error(`the GUI exposes no control labelled "${label}"; workspaces may have changed`);
      return 1;
    }
    if (dryRun) {
      console.log(`dry run ok: control "${label}" present; would send ${text.length} chars ` +
        `(marker "${promptMarker(text)}") into workspace ${title} (${before.length} session(s))`);
      return 0;
    }

    // The new-session button is revealed on row hover, so dispatch the click
    // directly; React still receives the event.
    await page.evaluate(l => document.querySelector(`[aria-label="${l}"]`).click(), label);

    // Wait for the store to hold the new session before typing. Without this a
    // slow view switch can leave the previous session's composer active and the
    // prompt lands there — measured on 2026-10-17 with H07P, where a new empty
    // session was created and the prompt still went into the older one.
    let created = null;
    for (let i = 0; i < 15 && !created; i++) {
      await page.waitForTimeout(2000);
      await page.waitForLoadState('domcontentloaded').catch(() => {});
      created = (sessionIdsFor(title) || []).find(id => !before.includes(id)) || null;
    }
    if (!created) {
      console.error(`FAIL: no new session appeared for "${title}"; nothing was typed. ` +
        'The GUI may have reopened an existing session instead.');
      return 1;
    }

    const editor = page.locator('textarea, [contenteditable="true"], [role="textbox"]').first();
    await editor.waitFor({ state: 'visible', timeout: 20000 });
    await editor.click();
    await editor.fill(text);
    await page.waitForTimeout(1200);
    const send = page.getByLabel(/send/i).first();
    if (await send.count() && await send.isVisible().catch(() => false)) await send.click();
    else await editor.press('Enter');

    // Verify against the session store and the new session's own transcript,
    // never against the click.
    const marker = promptMarker(text);
    let received = false;
    const dir = fs.readdirSync(SESSIONS).find(d => d.includes(title)) ||
      fs.readdirSync(SESSIONS).find(d => d.endsWith(title.replace(/[^\w]/g, '')));
    if (dir) {
      const file = path.join(SESSIONS, dir, created, 'session.v4.jsonl.zstd');
      for (let i = 0; i < 15 && !received; i++) {
        await page.waitForTimeout(2000);
        if (!fs.existsSync(file)) continue;
        try {
          const raw = execFileSync('zstd', ['-dc', file], { maxBuffer: 256 * 1024 * 1024 }).toString();
          received = raw.includes(marker);
        } catch { /* not readable yet */ }
      }
    }
    console.log(`session: ${created}`);
    console.log(`prompt received: ${received ? 'verified' : 'NOT VERIFIED'}`);
    console.log(`workspace: ${title} (${before.length} -> ${(sessionIdsFor(title) || []).length} sessions)`);
    if (!received) {
      console.error('the prompt is not in the new session. It may have landed in whichever ' +
        'session the GUI still had active; inspect the GUI before retrying.');
      return 1;
    }
    console.log('observe it in the DSH Web sidebar.');
    return 0;
  } finally {
    await browser.close();
  }
}

main().then(c => process.exit(c)).catch(e => { console.error('ERR', e.message); process.exit(2); });
