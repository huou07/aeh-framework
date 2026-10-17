#!/usr/bin/env node
// Answer a pending ask_user_question in an existing DSH Web session.
//
// Why: a paused agent that is holding at a boundary can be blocked on its own
// question. Answering it is part of an orderly pause; leaving it waiting is not.
//
// Addressing is deterministic: the workspace tree exposes
// [data-row-key="workspace:<uuid>"] and [data-row-key="session:<id>"], so the row
// is clicked by id and the open conversation is confirmed through
// [data-conversation-session] before anything is clicked.
//
// Usage: node scripts/dsh_gui_answer.cjs --id <sessionId> --option "<label text>"
// Exit codes: 0 answered and verified, 1 not verified, 2 environment problem.

const fs = require('fs');
const os = require('os');
const path = require('path');
const { execFileSync } = require('child_process');

const TOKEN_FILE = process.env.DSH_URL_FILE || '/run/huou07-dsh-link/url';
const HOST = process.env.DSH_WEB_HOST || 'http://127.0.0.1:3080';
const STORE = path.join(os.homedir(), '.dsh', 'storages', 'workspace.json');
const SESSIONS = path.join(os.homedir(), '.dsh', 'sessions');

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

function workspaceIdFor(sessionId) {
  const s = JSON.parse(fs.readFileSync(STORE, 'utf8'));
  for (const [id, w] of Object.entries(s.tables.workspaces)) {
    if ((w.sessionIds || []).includes(sessionId)) return { workspaceId: id, title: w.title };
  }
  return null;
}

function transcriptText(sessionId) {
  for (const dir of fs.readdirSync(SESSIONS)) {
    const f = path.join(SESSIONS, dir, sessionId, 'session.v4.jsonl.zstd');
    if (!fs.existsSync(f)) continue;
    try { return execFileSync('zstd', ['-dc', f], { maxBuffer: 1024 * 1024 * 1024 }).toString(); }
    catch { return null; }
  }
  return null;
}

async function main() {
  const args = process.argv.slice(2);
  const get = (k) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : null; };
  const sessionId = get('--id');
  const option = get('--option');
  if (!sessionId || !option) { console.error('usage: dsh_gui_answer.cjs --id <sessionId> --option "<label>"'); return 1; }
  const where = workspaceIdFor(sessionId);
  if (!where) { console.error(`session ${sessionId} is not in any workspace`); return 1; }
  if (where.title === 'AEH') { console.error('refusing to answer a question in the AEH workspace'); return 1; }
  if (!fs.existsSync(TOKEN_FILE)) { console.error('missing login link:', TOKEN_FILE); return 2; }
  const token = fs.readFileSync(TOKEN_FILE, 'utf8').trim();

  const before = transcriptText(sessionId) || '';
  const { chromium } = playwright();
  const browser = await chromium.launch({ headless: true, executablePath: chromiumPath() });
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 950 } });
    await page.goto(HOST + token, { waitUntil: 'load', timeout: 60000 });
    await page.waitForTimeout(9000);

    await page.evaluate(id => {
      const el = document.querySelector(`[data-row-key="workspace:${id}"]`);
      if (el && el.getAttribute('aria-expanded') === 'false') el.click();
    }, where.workspaceId);
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
    if (openId !== sessionId) { console.error(`refusing: open conversation ${openId} != ${sessionId}`); return 1; }

    const target = page.getByText(option, { exact: false }).first();
    if (!(await target.count())) { console.error(`no visible option matching ${JSON.stringify(option)}`); return 1; }
    await target.click({ timeout: 15000 });
    await page.waitForTimeout(1500);

    // Submit the answer if the question UI exposes a submit control.
    const submit = await page.evaluate(() => {
      for (const b of document.querySelectorAll('button')) {
        const t = ((b.innerText || '') + ' ' + (b.getAttribute('aria-label') || '')).toLowerCase();
        const r = b.getBoundingClientRect();
        if (r.width && r.height && /submit|answer|send|confirm|continue/.test(t)) return b.getAttribute('aria-label') || (b.innerText || '').trim();
      }
      return null;
    });
    if (submit) {
      await page.getByLabel(submit).first().click().catch(async () => {
        await page.getByRole('button', { name: submit }).first().click().catch(() => {});
      });
      console.log(`submitted via ${JSON.stringify(submit)}`);
    } else {
      console.log('no submit control found; the option click may submit directly');
    }
    await page.waitForTimeout(4000);

    let answered = false;
    for (let i = 0; i < 12 && !answered; i++) {
      await page.waitForTimeout(2500);
      const now = transcriptText(sessionId) || '';
      answered = now.length > before.length;
    }
    const after = transcriptText(sessionId) || '';
    const rowText = await page.evaluate(id => {
      const el = document.querySelector(`[data-row-key="session:${id}"]`);
      return el ? (el.innerText || '').replace(/\n/g, '|') : null;
    }, sessionId);
    console.log(`transcript bytes: ${before.length} -> ${after.length}`);
    console.log(`row state now: ${JSON.stringify(rowText)}`);
    if (after.length > before.length) { console.log('ANSWERED (verified)'); return 0; }
    console.error('NOT VERIFIED: no transcript change after answering');
    return 1;
  } finally {
    await browser.close();
  }
}

main().then(c => process.exit(c)).catch(e => { console.error('ERR', e.message); process.exit(2); });
