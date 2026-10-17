#!/usr/bin/env node
// Pause running DSH Web sessions through the GUI's own stop control.
//
// Why: a project agent that is mid-task must be stopped the way the GUI stops it,
// so the session stays persisted and resumable. Killing the web server would lose
// that guarantee.
//
// Usage:
//   node scripts/dsh_gui_pause.cjs --survey
//   node scripts/dsh_gui_pause.cjs --pause "<row text substring>"
//
// The GUI keeps workspace groups collapsed; this tool expands OR/VCE/H07P,
// matches the session row by visible text (never by position), opens it, clicks
// "[aria-label='Stop generating']" while it is present, then waits for the durable
// transcript to stop growing. A session is reported PAUSED only when both the stop
// control is gone and the transcript has been static for 15s.
//
// It refuses to touch the AEH workspace, which holds the session running this tool.
//
// Exit codes: 0 paused and verified, 1 not verified, 2 environment problem.

const fs = require('fs');
const os = require('os');
const path = require('path');

const TOKEN_FILE = process.env.DSH_URL_FILE || '/run/huou07-dsh-link/url';
const HOST = process.env.DSH_WEB_HOST || 'http://127.0.0.1:3080';
const STORE = path.join(os.homedir(), '.dsh', 'storages', 'workspace.json');
const SESSIONS = path.join(os.homedir(), '.dsh', 'sessions');
const GROUPS = ['OR', 'VCE', 'H07P'];

function playwright() {
  const candidates = [
    path.join(os.homedir(), '.local/share/playwright-cli/node_modules/playwright'),
    'playwright',
  ];
  for (const c of candidates) {
    try { return require(c); } catch { /* try next */ }
  }
  console.error('no playwright module found');
  process.exit(2);
}

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

function transcriptPath(sessionId) {
  for (const dir of fs.readdirSync(SESSIONS)) {
    const f = path.join(SESSIONS, dir, sessionId, 'session.v4.jsonl.zstd');
    if (fs.existsSync(f)) return f;
  }
  return null;
}

function transcriptSize(sessionId) {
  const f = transcriptPath(sessionId);
  try { return fs.statSync(f).size; } catch { return -1; }
}

// The durable proof that a turn was stopped is its own settlement event.
function turnAborted(sessionId) {
  const f = transcriptPath(sessionId);
  if (!f) return false;
  try {
    const raw = require('child_process').execFileSync('zstd', ['-dc', f],
      { maxBuffer: 512 * 1024 * 1024 }).toString();
    const lines = raw.trim().split('\n').slice(-6);
    for (const line of lines) {
      let ev;
      try { ev = JSON.parse(line); } catch { continue; }
      if (ev.type === 'turn/end' && JSON.stringify(ev.data || {}).includes('aborted')) return true;
    }
  } catch { /* not readable */ }
  return false;
}

function storeSessions() {
  const s = JSON.parse(fs.readFileSync(STORE, 'utf8'));
  const rows = [];
  for (const w of Object.values(s.tables.workspaces)) {
    for (const id of w.sessionIds || []) rows.push({ id, workspace: w.title });
  }
  return rows;
}

async function main() {
  const args = process.argv.slice(2);
  const survey = args.includes('--survey');
  const pause = args.includes('--pause');
  const needle = args.find(a => !a.startsWith('--'));
  if (!survey && !pause) { console.error('usage: dsh_gui_pause.cjs --survey | --pause "<row text>"'); return 1; }
  if (pause && !needle) { console.error('--pause needs the row text substring'); return 1; }
  if (pause && (needle === 'AEH' || /hiện tại|dự án tới|hello/.test(needle))) {
    console.error('refusing to touch an AEH session');
    return 1;
  }

  if (!fs.existsSync(TOKEN_FILE)) { console.error('missing login link:', TOKEN_FILE); return 2; }
  const token = fs.readFileSync(TOKEN_FILE, 'utf8').trim();
  const { chromium } = playwright();
  const browser = await chromium.launch({ headless: true, executablePath: chromiumPath() });
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 950 } });
    await page.goto(HOST + token, { waitUntil: 'load', timeout: 60000 });
    await page.waitForTimeout(9000);

    // Expand every product workspace group. The row is revealed only when its
    // group is expanded, and the toggle is hidden until the row is hovered, so
    // dispatch the click through the DOM as the launcher does.
    const expand = async (name) => page.evaluate(n => {
      const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
      while (walker.nextNode()) {
        const node = walker.currentNode;
        if ((node.textContent || '').trim() !== n) continue;
        let el = node.parentElement;
        for (let i = 0; i < 5 && el; i++, el = el.parentElement) {
          if (el.getAttribute?.('role') === 'button' || el.tagName === 'BUTTON' ||
              el.getAttribute?.('role') === 'treeitem' || el.getAttribute?.('role') === 'option') {
            el.click();
            return true;
          }
        }
        node.parentElement?.click();
        return true;
      }
      return false;
    }, name);

    for (const g of GROUPS) { await expand(g); await page.waitForTimeout(1500); }

    const groupText = async (name) => page.evaluate(n => {
      for (const g of document.querySelectorAll('[class*="groupSection"]')) {
        const t = (g.innerText || '').trim();
        if (t.startsWith(n)) return t.replace(/\n/g, ' | ');
      }
      return null;
    }, name);

    if (survey) {
      for (const r of storeSessions()) console.log(`  ${r.workspace}\t${r.id}\t${transcriptSize(r.id)}B`);
      console.log('== sidebar groups ==');
      for (const g of [...GROUPS, 'AEH']) console.log(`  ${g}: ${JSON.stringify(await groupText(g))}`);
      return 0;
    }

    // Open the target row. The row is matched by visible text, never by position.
    const sessionId = (() => {
      const i = args.indexOf('--id');
      return i >= 0 ? args[i + 1] : null;
    })();
    if (!sessionId) { console.error('--pause requires --id <session-id> so verification addresses one transcript'); return 1; }

    const row = page.getByText(needle, { exact: false }).first();
    if (!(await row.count())) { console.error(`no sidebar row matches ${JSON.stringify(needle)}`); return 1; }
    await row.click({ timeout: 15000 });
    await page.waitForTimeout(6000);

    const stop = page.locator('[aria-label="Stop generating"]').first();
    const present = await stop.count();
    console.log(`stop control: ${present ? 'present' : 'absent'}`);
    if (!present) {
      console.error('this session exposes no stop control: it is not running, or the GUI has not attached to it');
      return 1;
    }

    const before = transcriptSize(sessionId);
    await stop.click();
    let staticRounds = 0;
    let aborted = false;
    for (let i = 0; i < 12; i++) {
      await page.waitForTimeout(5000);
      const now = transcriptSize(sessionId);
      staticRounds = now === before ? staticRounds + 1 : 0;
      aborted = turnAborted(sessionId);
      if (aborted && staticRounds >= 2) break;
    }
    const after = transcriptSize(sessionId);
    const gone = (await page.locator('[aria-label="Stop generating"]').count()) === 0;
    console.log(`target transcript: ${sessionId} ${before}B -> ${after}B`);
    console.log(`stop control gone: ${gone}`);
    console.log(`turn/end aborted recorded: ${aborted}`);
    console.log(`transcript static for 10s: ${staticRounds >= 2}`);
    if (gone && aborted && staticRounds >= 2) { console.log(`PAUSED ${sessionId} (verified)`); return 0; }
    console.error('NOT VERIFIED as paused');
    return 1;
  } finally {
    await browser.close();
  }
}

main().then(c => process.exit(c)).catch(e => { console.error('ERR', e.message); process.exit(2); });
