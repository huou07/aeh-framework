#!/usr/bin/env node
// Read-only probe of the live DSH Web GUI.
//
// Purpose: before any session is stopped, find out what the GUI currently shows:
// which sessions are running, their titles and ids, and the exact control labels
// a stop operation would have to use. It never clicks, types or mutates; it only
// opens the GUI and reads the DOM.
//
// Usage: node scripts/dsh_gui_probe.cjs [--json]
// Exit codes: 0 read ok, 1 nothing usable found, 2 environment problem.

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
  if (!fs.existsSync(TOKEN_FILE)) { console.error('missing login link:', TOKEN_FILE); return 2; }
  const token = fs.readFileSync(TOKEN_FILE, 'utf8').trim();
  const { chromium } = playwright();
  const browser = await chromium.launch({ headless: true, executablePath: chromiumPath() });
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 950 } });
    await page.goto(HOST + token, { waitUntil: 'load', timeout: 60000 });
    await page.waitForTimeout(8000);

    const labels = await page.evaluate(() => {
      const out = [];
      for (const el of document.querySelectorAll('[aria-label]')) {
        const l = el.getAttribute('aria-label');
        if (l && /stop|run|cancel|new session|interrupt/i.test(l)) out.push(l);
      }
      return [...new Set(out)];
    });

    const text = await page.evaluate(() => document.body.innerText || '');

    const report = { url_host: HOST, control_labels: labels, body_text: text };
    if (process.argv.includes('--json')) {
      console.log(JSON.stringify(report, null, 2));
    } else {
      console.log('== labels matching stop/run/cancel/new session ==');
      for (const l of labels) console.log('  ', JSON.stringify(l));
      console.log('== body text (first 6000 chars) ==');
      console.log(text.slice(0, 6000));
    }
    return 0;
  } finally {
    await browser.close();
  }
}

main().then(c => process.exit(c)).catch(e => { console.error('ERR', e.message); process.exit(2); });
