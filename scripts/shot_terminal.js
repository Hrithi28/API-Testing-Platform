const { chromium } = require('playwright');
const path = require('path');
(async () => {
  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
  const page = await browser.newPage({ viewport: { width: 980, height: 760 }, deviceScaleFactor: 2 });
  await page.goto('file://' + path.resolve(__dirname, '../artifacts/_terminal.html'));
  await page.waitForTimeout(150);
  const el = await page.$('.window');
  await el.screenshot({ path: path.resolve(__dirname, '../artifacts/shot_terminal.png') });
  await browser.close();
})();
