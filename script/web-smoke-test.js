// Loads the built site in a real browser and checks that the module boots far enough
// to ask for a ROM. The ROM itself is supplied by the player, so CI never has one.
const { chromium } = require('playwright');
const fs = require('fs');

const SITE = process.env.SITE_URL;
const OUT = process.env.SHOT_DIR;

function say(m) {
  process.stdout.write(m + '\n');
}

async function main() {
  const browser = await chromium.launch({
    args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--no-sandbox'],
  });
  const context = await browser.newContext({ viewport: { width: 1280, height: 800 } });
  const page = await context.newPage();

  const lines = [];
  page.on('console', (m) => lines.push(`[${m.type()}] ${m.text()}`));
  page.on('pageerror', (e) => lines.push(`[pageerror] ${e.message}`));
  page.on('dialog', (d) => {
    lines.push(`[dialog] ${d.message()}`);
    d.accept().catch(() => {});
  });

  await page.goto(SITE, { waitUntil: 'domcontentloaded', timeout: 120000 });
  await page.waitForSelector('#start-button', { state: 'visible', timeout: 300000 });
  say('shell loaded, clicking Start');
  await page.click('#start-button');
  await page.screenshot({ path: `${OUT}/01-started.png` });

  const env = await page.evaluate(() => ({
    isolated: window.crossOriginIsolated === true,
    sharedArrayBuffer: typeof SharedArrayBuffer === 'function',
  }));
  say(`crossOriginIsolated=${env.isolated} SharedArrayBuffer=${env.sharedArrayBuffer}`);
  if (!env.isolated || !env.sharedArrayBuffer) {
    throw new Error('the page is not cross-origin isolated, the pthreads build cannot run');
  }

  // A fresh browser has no extracted archive, so the game offers to make one.
  const yes = page.locator('.sk-prompt-panel button', { hasText: 'Yes' });
  await yes.waitFor({ state: 'visible', timeout: 300000 });
  say('the game offers to extract a ROM');
  await yes.click();

  // The game asks for the player's own ROM before it extracts anything.
  await page.waitForSelector('input[type=file]', { state: 'attached', timeout: 300000 });
  say('the game is asking for a ROM');
  await page.screenshot({ path: `${OUT}/02-rom-prompt.png` });

  const workers = lines.filter((l) => /thread|pthread|worker/i.test(l));
  say(`thread related log lines: ${workers.length}`);

  const failures = lines.filter((l) => /pageerror|stopped unexpectedly|Aborted/i.test(l));
  if (failures.length) {
    throw new Error(`the module reported a failure: ${failures[0]}`);
  }

  fs.writeFileSync(`${OUT}/console.log`, lines.join('\n'));
  say('PASS: the module boots and asks for a ROM');
  await browser.close();
}

main().catch((e) => {
  say(`FAIL: ${e.message}`);
  process.exit(1);
});
