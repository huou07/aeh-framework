#!/usr/bin/env node
// Read-only inspection of one DSH Web workspace's session list.
//
// Opens the GUI, selects a workspace by its sidebar title, and prints each
// visible session row (title, status text, relative time) plus the controls the
// row exposes. It never clicks a session, types, or stops anything.
//
// Usage: node scripts/dsh_gui_sessions.cjs <Workspace title> [--html]
// Exit codes: 0 read ok, 1 workspace not found, 2 environment problem.

const fs = require('fs');
const os = require('os');
const path = require('path');

const TOKEN_FILE = process.env.DSH_URL_FILE || '/run/huou07-dsh-link/url';
const HOST = process.env.DSH_WEB_HOST || 'http://127.0.0.1:3080';

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

async function main() {
  const args = process.argv.slice(2);
  const title = args.find(a => !a.startsWith('--'));
  const wantHtml = args.includes('--html');
  if (!title) { console.error('usage: dsh_gui_sessions.cjs <Workspace title> [--html]'); return 1; }
  if (!fs.existsSync(TOKEN_FILE)) { console.error('missing login link:', TOKEN_FILE); return 2; }
  const token = fs.readFileSync(TOKEN_FILE, 'utf8').trim();

  const { chromium } = playwright();
  const browser = await chromium.launch({ headless: true, executablePath: chromiumPath() });
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 950 } });
    await page.goto(HOST + token, { waitUntil: 'load', timeout: 60000 });
    await page.waitForTimeout(8000);

    // Select the workspace by clicking its sidebar entry (exact text match).
    const clicked = await page.evaluate(t => {
      const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
      while (walker.nextNode()) {
        const node = walker.currentNode;
        if ((node.textContent || '').trim() !== t) continue;
        let el = node.parentElement;
        for (let i = 0; i < 4 && el; i++, el = el.parentElement) {
          if (el.getAttribute && (el.getAttribute('role') === 'button' || el.tagName === 'BUTTON' ||
              el.getAttribute('role') === 'option' || el.getAttribute('role') === 'tab' || el.getAttribute('role') === 'treeitem')) {
            el.click();
            return true;
          }
        }
        if (node.parentElement) { node.parentElement.click(); return true; }
      }
      return false;
    }, title);
    if (!clicked) { console.error(`no sidebar entry with text ${JSON.stringify(title)}`); return 1; }
    await page.waitForTimeout(4000);

    const rows = await page.evaluate(() => {
      const out = [];
      const seen = new Set();
      for (const el of document.querySelectorAll('[role="listitem"],[role="option"],li,button,a')) {
        const t = (el.innerText || '').trim().replace(/\s+/g, ' ');
        if (!t || t.length > 400) continue;
        if (seen.has(el)) continue;
        const aria = el.getAttribute('aria-label');
        const label = aria || el.getAttribute('title') || '';
        if (!/^session-|Running|\bmin\b|\bh\b|\b\d{1,2}:\d{2}\b/.test(t + ' ' + label)) continue;
        seen.add(el);
        out.push({ tag: el.tagName, role: el.getAttribute('role'), aria: label, text: t.slice(0, 200) });
      }
      return out;
    });

    console.log(`== workspace ${title} ==`);
    for (const r of rows) console.log(JSON.stringify(r));
    const text = await page.evaluate(() => document.body.innerText || '');
    console.log('== body text (first 4000 chars) ==');
    console.log(text.slice(0, 4000));

    if (wantHtml) {
      const html = await page.evaluate(() => {
        const main = document.querySelector('aside, nav, [class*="sidebar"]') || document.body;
        return main.outerHTML;
      });
      console.log('== sidebar html (first 20000 chars) ==');
      console.log(html.slice(0, 20000));
    }
    return 0;
  } finally {
    await browser.close();
  }
}

main().then(c => process.exit(c)).catch(e => { console.error('ERR', e.message); process.exit(2); });
