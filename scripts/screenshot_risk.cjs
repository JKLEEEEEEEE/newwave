const { chromium } = require('playwright-core');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({
    viewport: { width: 1920, height: 1080 },
    deviceScaleFactor: 2,
  });

  // 1. 메인 페이지 로드
  await page.goto('http://localhost:5173', { waitUntil: 'networkidle', timeout: 15000 });
  await page.waitForTimeout(2000);

  // 2. "실시간 리스크 관제" 버튼 클릭
  const riskBtn = page.locator('text=실시간 리스크 관제').first();
  if (await riskBtn.isVisible()) {
    await riskBtn.click();
    console.log('[OK] Clicked "실시간 리스크 관제"');
    await page.waitForTimeout(3000);
  }

  // 3. 특정 딜 클릭 (CLI 인자 또는 기본값)
  const dealName = process.argv[2] || '';
  if (dealName) {
    const dealBtn = page.locator(`text=${dealName}`).first();
    if (await dealBtn.isVisible()) {
      await dealBtn.click();
      console.log(`[OK] Clicked deal: "${dealName}"`);
      await page.waitForTimeout(3000);
    } else {
      console.log(`[WARN] Deal "${dealName}" not found`);
    }
  }

  await page.screenshot({ path: 'screenshot_risk.png', fullPage: false });
  console.log('[OK] screenshot_risk.png saved');

  await browser.close();
  console.log('Done.');
})();
