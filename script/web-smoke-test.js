// Loads the built site in a real browser, feeds it a ROM and screenshots the result.
// The ROM URL is a repository secret so the address never lands in the repository.
const { chromium } = require('playwright');
const fs = require('fs');

const SITE = process.env.SITE_URL;
const ROM = process.env.ROM_PATH;
const OUT = process.env.SHOT_DIR;
async function main() {
  const browser = await chromium.launch({
    args: [
      '--use-gl=angle',
      '--use-angle=swiftshader',
      '--enable-unsafe-swiftshader',
      '--no-sandbox',
    ],
  });
  const context = await browser.newContext({ viewport: { width: 1280, height: 800 } });
  const page = await context.newPage();

  const lines = [];
  page.on('console', (m) => lines.push(`[${m.type()}] ${m.text()}`));
  page.on('pageerror', (e) => lines.push(`[pageerror] ${e.message}`));
  // The game asks before it extracts anything, and headless dismisses dialogs by default.
  page.on('dialog', (d) => {
    lines.push(`[dialog] ${d.message()}`);
    d.accept().catch(() => {});
  });

  const say = (m) => {
    process.stdout.write(m + '\n');
  };

  await page.goto(SITE, { waitUntil: 'domcontentloaded', timeout: 120000 });

  await page.waitForSelector('#start-button', { state: 'visible', timeout: 180000 });
  say('shell loaded, clicking Start');
  await page.click('#start-button');
  await page.screenshot({ path: `${OUT}/01-started.png` });

  // The first run extracts the ROM in the tab, which asks for a file in a prompt
  // the game draws itself.
  const input = page.waitForSelector('input[type=file]', { state: 'attached', timeout: 180000 });
  await input;
  await page.setInputFiles('input[type=file]', ROM);
  say('ROM handed to the page');

  // Extraction takes a few minutes, then the game menu comes up on the canvas.
  let booted = false;
  for (let i = 0; i < 120; i++) {
    await page.waitForTimeout(10000);
    const shot = `${OUT}/0${Math.min(2 + Math.floor(i / 12), 9)}-wait-${i * 10}s.png`;
    await page.screenshot({ path: shot });
    if (i % 3 === 0) {
      const status = await page.evaluate(() => {
        const el = document.getElementById('status');
        return el ? el.textContent : '(gone)';
      });
      say(`t=${(i + 1) * 10}s status: ${status}`);
    }
    const canvas = await page.evaluate(() => {
      const c = document.getElementById('canvas');
      if (!c || !c.width) return 0;
      const gl = c.getContext('webgl2', { preserveDrawingBuffer: true });
      return gl ? 1 : 0;
    });
    if (canvas && i > 2) {
      booted = true;
      break;
    }
  }

  await page.screenshot({ path: `${OUT}/99-final.png` });
  fs.writeFileSync(`${OUT}/console.log`, lines.join('\n'));
  say(booted ? 'PASS: the canvas has a webgl2 context' : 'FAIL: no webgl2 canvas');
  await browser.close();
  process.exit(booted ? 0 : 1);
}

main().catch((e) => {
  process.stdout.write(`FAIL: ${e.stack}\n`);
  process.exit(1);
});
