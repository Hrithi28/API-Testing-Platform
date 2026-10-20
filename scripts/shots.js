// Capture fresh dashboard screenshots against the regenerated artifacts/dashboard.html
const { chromium } = require('playwright');
const path = require('path');

(async () => {
  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  const errors = [];
  page.on('pageerror', e => errors.push(String(e)));
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });

  const dashPath = 'file://' + path.resolve(__dirname, '../artifacts/dashboard.html');
  await page.goto(dashPath);
  await page.waitForTimeout(300);

  // Overview tab (default)
  await page.screenshot({ path: path.resolve(__dirname, '../artifacts/shot_dash_top.png') });

  // Findings tab -- click, then expand the top row for evidence detail
  await page.click('[data-tab="findings"]');
  await page.waitForTimeout(200);
  const firstRow = await page.$('#findings-table tbody tr');
  if (firstRow) await firstRow.click();
  await page.waitForTimeout(200);
  await page.screenshot({ path: path.resolve(__dirname, '../artifacts/shot_findings.png') });

  // Defect register tab
  await page.click('[data-tab="defects"]');
  await page.waitForTimeout(200);
  await page.screenshot({ path: path.resolve(__dirname, '../artifacts/shot_defects.png') });

  console.log('console/page errors:', JSON.stringify(errors));
  await browser.close();
})();
