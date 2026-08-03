const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    geolocation: { latitude: 28.6139, longitude: 77.2090 },
    permissions: ['geolocation']
  });
  const page = await context.newPage();
  await page.goto('https://blinkit.com/s/?q=saridon', { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(2500);

  const img = await page.evaluate(() => {
    const imgs = Array.from(document.querySelectorAll('img'));
    const valid = imgs.map(i => i.src || i.getAttribute('src') || '')
      .filter(src => (src.includes('cdn.grofers.com') || src.includes('cdn.blinkit.com'))
        && !src.includes('eta-icons') && !src.includes('icon') && !src.includes('logo')
      );
    return valid[0] || null;
  });

  console.log('SARIDON_IMAGE:', img);
  await browser.close();
})();
