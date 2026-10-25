const { chromium } = require('@playwright/test');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 2,
    ignoreHTTPSErrors: true,
  });
  const page = await context.newPage();
  
  // Navigate to the ask view
  await page.goto('https://fourpi.local/ci/#t-ask', { waitUntil: 'networkidle', timeout: 30000 });
  await page.waitForTimeout(1000);
  
  // Fill in the form with rivet PR 511
  await page.fill('#ask-repo', 'rivet');
  await page.fill('#ask-pr', '511');
  
  // Click the ask button
  await page.click('button[type="submit"]');
  
  // Wait for the answer to load
  await page.waitForTimeout(3000);
  
  // Take screenshot
  await page.screenshot({ path: 'static/img/ci-dashboard-ask.png', fullPage: true });
  console.log('Screenshot saved to static/img/ci-dashboard-ask.png');
  
  await browser.close();
})().catch(err => { console.error(err.message); process.exit(1); });
