#!/usr/bin/env node
// Test een wand in WebKit (Safari-engine) of Chrome.
//
//   node scripts/test.mjs <slug> [opties]
//
//   --engine webkit|chrome   standaard webkit
//   --phone                  390x844 met touch (telefoon)
//   --shot                   screenshot van ?still naar --out (standaard .cache/test)
//   --prof                   meet ms per frame via ?prof (leest window.__prof of telt rAF)
//   --scroll <px>            scroll voor de screenshot
//   --url <url>              andere basis dan file://httpdocs, bijv. https://nunkichannels.test
//                            (via file:// faalt alleen /nav.js, dat is geen echte fout)
//
// Eenmalig: npm install && npx playwright-core install webkit
import { webkit, chromium } from 'playwright-core';
import path from 'node:path';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const args = process.argv.slice(2);
const slug = args[0] && !args[0].startsWith('--') ? args[0] : null;
const opt = n => { const i = args.indexOf('--' + n); return i < 0 ? null : (args[i + 1]?.startsWith('--') || args[i + 1] === undefined ? true : args[i + 1]); };
if (!slug) { console.error('gebruik: node scripts/test.mjs <slug> [--shot] [--prof] [--phone] [--engine chrome] [--scroll px]'); process.exit(1); }

const engine = opt('engine') === 'chrome'
  ? chromium.launch({ executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' })
  : webkit.launch();
const browser = await engine;
const phone = !!opt('phone');
const ctx = await browser.newContext(phone
  ? { viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, deviceScaleFactor: 2 }
  : { viewport: { width: 1600, height: 1200 } });
const page = await ctx.newPage();
const errors = [];
page.on('pageerror', e => errors.push(String(e)));
page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });

const base = typeof opt('url') === 'string' ? opt('url').replace(/\/$/, '') : 'file://' + path.join(root, 'httpdocs');
const query = opt('prof') ? '?prof' : opt('shot') ? '?still' : '';
await page.goto(`${base}/${slug}/index.html${query}`);
await page.waitForTimeout(opt('shot') ? 1500 : 800);

if (typeof opt('scroll') === 'string') {
  await page.evaluate(y => window.scrollTo(0, +y), opt('scroll'));
  await page.waitForTimeout(500);
}
if (opt('shot')) {
  const out = typeof opt('out') === 'string' ? opt('out') : path.join(root, '.cache', 'test');
  fs.mkdirSync(out, { recursive: true });
  const file = path.join(out, `${slug}-${phone ? 'phone' : 'desktop'}-${opt('scroll') || 0}.png`);
  await page.screenshot({ path: file });
  console.log('screenshot:', file);
}
if (opt('prof')) {
  // ms per frame over 3 s, met een getImageData-aanroep om de GPU te dwingen klaar te zijn
  const ms = await page.evaluate(() => new Promise(res => {
    const c = document.querySelector('canvas'); const g = c && c.getContext('2d');
    let n = 0, t0 = performance.now();
    (function f() { if (g) g.getImageData(0, 0, 1, 1); if (++n < 180 && performance.now() - t0 < 3000) requestAnimationFrame(f); else res((performance.now() - t0) / n); })();
  }));
  console.log(`ms per frame: ${ms.toFixed(1)} (Low Power Mode houdt WebKit op ~33 ms)`);
}
console.log(errors.length ? 'fouten:\n' + errors.join('\n') : 'geen console-fouten');
await browser.close();
