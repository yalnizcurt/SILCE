const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    geolocation: { latitude: 28.6139, longitude: 77.2090 },
    permissions: ['geolocation']
  });

  const queries = [
    { key: 'pedigree', query: 'pedigree dog food' },
    { key: 'bournville', query: 'bournville dark chocolate' },
    { key: 'whisper', query: 'whisper sanitary pads' },
    { key: 'soda', query: 'club soda mixer' }
  ];

  const results = {};

  for (const q of queries) {
    const page = await context.newPage();
    await page.goto(`https://blinkit.com/s/?q=${encodeURIComponent(q.query)}`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(2000);

    const img = await page.evaluate(() => {
      const imgs = Array.from(document.querySelectorAll('img'));
      const valid = imgs.map(i => i.src || i.getAttribute('src') || '')
        .filter(src => (src.includes('cdn.grofers.com') || src.includes('cdn.blinkit.com'))
          && !src.includes('eta-icons') && !src.includes('icon') && !src.includes('logo')
        );
      return valid[0] || null;
    });

    results[q.key] = img;
    await page.close();
  }

  console.log('NEW_PRODUCT_IMAGES:', JSON.stringify(results, null, 2));
  await browser.close();
})();
