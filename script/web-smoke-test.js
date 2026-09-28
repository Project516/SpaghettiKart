// Loads the built site in a real browser, feeds it a ROM and screenshots the result.
const { chromium } = require('playwright');
const crypto = require('crypto');
const fs = require('fs');

const SITE = process.env.SITE_URL;
const ROM = process.env.ROM_PATH;
const OUT = process.env.SHOT_DIR;
const EXPECTED_SHA1 = '579c48e211ae952530ffc8738709f078d5dd215e';

function say(m) {
  process.stdout.write(m + '\n');
}

async function main() {
  const sha1 = crypto.createHash('sha1').update(fs.readFileSync(ROM)).digest('hex');
  if (sha1 !== EXPECTED_SHA1) {
    throw new Error(`ROM hash ${sha1} is not the Mario Kart 64 (US) the port expects`);
  }
  say(`ROM sha1 ${sha1}`);

  const browser = await chromium.launch({
    args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--no-sandbox'],
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

  await page.goto(SITE, { waitUntil: 'domcontentloaded', timeout: 120000 });
  await page.waitForSelector('#start-button', { state: 'visible', timeout: 300000 });
  say('shell loaded, clicking Start');
  await page.click('#start-button');
  await page.screenshot({ path: `${OUT}/01-started.png` });

  // The first run extracts the ROM in the tab, which asks for a file in a prompt
  // the game draws itself.
  await page.waitForSelector('input[type=file]', { state: 'attached', timeout: 300000 });
  await page.setInputFiles('input[type=file]', ROM);
  say('ROM handed to the page');

  // Extraction runs in the tab and takes a while, then the game menu is drawn on the canvas.
  for (let i = 0; i < 90; i++) {
    await page.waitForTimeout(10000);
    const state = await page.evaluate(() => {
      const status = document.getElementById('status');
      const canvas = document.getElementById('canvas');
      const visible = document.getElementById('canvas-container');
      return {
        status: status ? status.textContent : '',
        canvasWidth: canvas ? canvas.width : 0,
        showing: visible ? getComputedStyle(visible).display !== 'none' : false,
      };
    });
    if (i % 3 === 0 || i < 3) say(`t=${(i + 1) * 10}s ${JSON.stringify(state)}`);
    await page.screenshot({ path: `${OUT}/wait-${String((i + 1) * 10).padStart(4, '0')}s.png` });

    if (/not supported|No ROM|Exiting|stopped unexpectedly/i.test(state.status)) {
      throw new Error(`the page reported: ${state.status}`);
    }
    if (state.showing && state.canvasWidth > 0) {
      // The canvas only appears once the game has the archive and is drawing.
      await page.waitForTimeout(15000);
      await page.screenshot({ path: `${OUT}/99-menu.png` });
      fs.writeFileSync(`${OUT}/console.log`, lines.join('\n'));
      say('PASS: the game is drawing on the canvas');
      await browser.close();
      return;
    }
  }

  fs.writeFileSync(`${OUT}/console.log`, lines.join('\n'));
  throw new Error('the game never showed its canvas');
}

main().catch((e) => {
  say(`FAIL: ${e.message}`);
  process.exit(1);
});
