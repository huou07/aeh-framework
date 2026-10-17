#!/usr/bin/env node
// Steer an instruction into an existing DSH Web session.
//
// Why: a running project agent should stop by being told to stop, at its own step
// boundary, and to leave a clean, committed-or-recorded work state. Clicking the
// GUI stop control is a hard interrupt; this tool delivers a message the agent
// acts on instead.
//
// Usage:
//   node scripts/dsh_gui_steer.cjs --send --id <sessionId> --row "<row text>" --message <file>
//   node scripts/dsh_gui_steer.cjs --check --id <sessionId>
//
// Safety: the tool expands the product workspace groups, opens the row, and reads
// [data-conversation-session] from the DOM. It refuses to type unless that value
// equals the requested session id, so a steer cannot land in another session. It
// never touches the AEH workspace.
//
// Exit codes: 0 delivered and verified, 1 not verified, 2 environment problem.

const fs = require('fs');
const os = require('os');
const path = require('path');
const { execFileSync } = require('child_process');

const TOKEN_FILE = process.env.DSH_URL_FILE || '/run/huou07-dsh-link/url';
const HOST = process.env.DSH_WEB_HOST || 'http://127.0.0.1:3080';
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

function transcriptText(sessionId) {
  const f = transcriptPath(sessionId);
  if (!f) return null;
  try {
    return execFileSync('zstd', ['-dc', f], { maxBuffer: 1024 * 1024 * 1024 }).toString();
  } catch { return null; }
}

function sizeOf(sessionId) {
  const f = transcriptPath(sessionId);
  try { return fs.statSync(f).size; } catch { return -1; }
}

async function expandGroups(page) {
  for (const name of GROUPS) {
    await page.evaluate(n => {
      const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
      while (walker.nextNode()) {
        const node = walker.currentNode;
        if ((node.textContent || '').trim() !== n) continue;
        let el = node.parentElement;
        for (let i = 0; i < 5 && el; i++, el = el.parentElement) {
          if (el.getAttribute?.('role') === 'button' || el.tagName === 'BUTTON' ||
              el.getAttribute?.('role') === 'treeitem') { el.click(); return true; }
        }
        node.parentElement?.click();
        return true;
      }
      return false;
    }, name);
    await page.waitForTimeout(1200);
  }
}

async function main() {
  const args = process.argv.slice(2);
  const send = args.includes('--send');
  const check = args.includes('--check');
  const get = (k) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : null; };
  const sessionId = get('--id');
  const rowText = get('--row');
  const messageFile = get('--message');
  if (!sessionId) { console.error('--id <sessionId> is required'); return 1; }
  if (send && !messageFile) { console.error('--send needs --message'); return 1; }
  if (!send && !check) { console.error('usage: dsh_gui_steer.cjs --send|--check ...'); return 1; }
  if (sessionId === 'session-e84d8747-14ff-4ad9-b686-1c6c739f7343' || rowText === 'AEH') {
    console.error('refusing to steer the session running this tool');
    return 1;
  }

  if (check) {
    console.log(`transcript bytes: ${sizeOf(sessionId)}`);
    const raw = transcriptText(sessionId);
    if (raw) {
      const lines = raw.trim().split('\n');
      for (const line of lines.slice(-5)) {
        try { const ev = JSON.parse(line); console.log(`${ev.type} ${JSON.stringify(ev.data || {}).slice(0, 160)}`); }
        catch { /* skip */ }
      }
      console.log(`turn/end events: ${lines.filter(l => l.includes('"turn/end"')).length}`);
    }
    return 0;
  }

  const text = fs.readFileSync(messageFile, 'utf8');
  const marker = text.split('\n').map(l => l.replace(/^#+\s*/, '').trim()).find(l => l.length >= 20) || text.trim().slice(0, 60);
  if (!fs.existsSync(TOKEN_FILE)) { console.error('missing login link:', TOKEN_FILE); return 2; }
  const token = fs.readFileSync(TOKEN_FILE, 'utf8').trim();

  const { chromium } = playwright();
  const browser = await chromium.launch({ headless: true, executablePath: chromiumPath() });
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 950 } });
    await page.goto(HOST + token, { waitUntil: 'load', timeout: 60000 });
    await page.waitForTimeout(9000);

    // Deterministic addressing: expand the owning workspace row, then click the
    // session row by its id. No text matching, so a click cannot land elsewhere.
    const store = JSON.parse(fs.readFileSync(path.join(os.homedir(), '.dsh', 'storages', 'workspace.json'), 'utf8'));
    let workspaceId = null;
    for (const [id, w] of Object.entries(store.tables.workspaces)) {
      if ((w.sessionIds || []).includes(sessionId)) workspaceId = id;
    }
    if (!workspaceId) { console.error(`session ${sessionId} is not in any workspace store`); return 1; }
    await page.evaluate(id => {
      const el = document.querySelector(`[data-row-key="workspace:${id}"]`);
      if (el && el.getAttribute('aria-expanded') === 'false') el.click();
    }, workspaceId);
    await page.waitForTimeout(2000);

    const row = page.locator(`[data-row-key="session:${sessionId}"]`);
    if (!(await row.count())) { console.error('session row not present in the tree'); return 1; }
    await row.click({ timeout: 15000 });
    await page.waitForTimeout(7000);

    const openId = await page.evaluate(() => {
      const el = document.querySelector('[data-conversation-session]');
      return el ? el.getAttribute('data-conversation-session') : null;
    });
    console.log(`open conversation: ${openId}`);
    if (openId !== sessionId) {
      console.error(`refusing to send: open conversation ${openId} != requested ${sessionId}`);
      return 1;
    }

    const before = sizeOf(sessionId);
    const editor = page.locator('textarea, [contenteditable="true"], [role="textbox"]').first();
    await editor.waitFor({ state: 'visible', timeout: 20000 });
    await editor.click();
    await editor.fill(text);
    await page.waitForTimeout(1500);

    const primaryAria = await page.evaluate(() => {
      for (const b of document.querySelectorAll('button')) {
        const a = b.getAttribute('aria-label') || '';
        if (/steer|queue|send message|stop generating/i.test(a)) {
          const r = b.getBoundingClientRect();
          if (r.width && r.height) return a;
        }
      }
      return null;
    });
    console.log(`primary action: ${JSON.stringify(primaryAria)}`);
    if (!primaryAria) { console.error('no primary composer action found'); return 1; }
    if (/stop generating/i.test(primaryAria)) {
      console.error('the composer still only offers a hard stop; steering is unavailable, nothing was sent');
      return 1;
    }
    if (args.includes('--accelerate')) {
      // The plain button follows the session's busy-Enter preference (usually
      // queue). The accelerated chord flips it, which is how a running turn is
      // interrupted at its next step boundary.
      await editor.press('Control+Enter');
    } else {
      await page.getByLabel(primaryAria).first().click();
    }
    await page.waitForTimeout(4000);

    let received = false;
    let delivery = null;
    for (let i = 0; i < 15 && !received; i++) {
      await page.waitForTimeout(2000);
      const raw = transcriptText(sessionId);
      if (!raw) continue;
      received = raw.includes(marker);
      if (received) {
        for (const line of raw.trim().split('\n')) {
          if (!line.includes(marker) || !line.includes('inbox')) continue;
          try {
            const ev = JSON.parse(line);
            delivery = ev.data?.target || ev.type;
          } catch { /* skip */ }
        }
      }
    }
    console.log(`marker: ${JSON.stringify(marker)}`);
    console.log(`message received in transcript: ${received}`);
    console.log(`delivery: ${delivery || 'unknown (not an inbox event)'}`);
    console.log(`transcript bytes: ${before} -> ${sizeOf(sessionId)}`);
    if (!received) { console.error('NOT VERIFIED: the steer message is not in the target transcript'); return 1; }
    console.log('STEERED (verified)');
    return 0;
  } finally {
    await browser.close();
  }
}

main().then(c => process.exit(c)).catch(e => { console.error('ERR', e.message); process.exit(2); });
