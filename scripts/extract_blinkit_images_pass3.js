const { chromium } = require('playwright');
const fs = require('fs');

const REMAINING_8 = [
  { id: 'prod_403', query: 'lighter' },
  { id: 'prod_601', query: 'crocin' },
  { id: 'prod_604', query: 'tissue box' },
  { id: 'prod_703', query: 'pril' },
  { id: 'prod_802', query: 'kissan jam' },
  { id: 'prod_805', query: 'colin' },
  { id: 'prod_808', query: 'odonil' },
  { id: 'prod_811', query: 'cards deck' }
];

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    geolocation: { latitude: 28.6139, longitude: 77.2090 },
    permissions: ['geolocation'],
  });

  const page = await context.newPage();
  const results = {};

  for (const item of REMAINING_8) {
    try {
      await page.goto(`https://blinkit.com/s/?q=${encodeURIComponent(item.query)}`, { waitUntil: 'domcontentloaded', timeout: 15000 });
      await page.waitForTimeout(2500);

      const imageUrl = await page.evaluate(() => {
        const imgs = Array.from(document.querySelectorAll('img'));
        const valid = imgs.map(img => img.src || img.getAttribute('src') || '')
          .filter(src => (src.includes('cdn.grofers.com') || src.includes('cdn.blinkit.com'))
            && !src.includes('eta-icons')
            && !src.includes('assets/eta')
            && !src.includes('icon')
            && !src.includes('logo')
            && !src.includes('banner')
            && (src.includes('product') || src.includes('cms-assets') || src.includes('rc-upload'))
          );
        return valid[0] || null;
      });

      if (imageUrl) {
        results[item.id] = imageUrl;
        console.log(`✅ ${item.id}: ${imageUrl.substring(0, 70)}`);
      } else {
        console.log(`❌ ${item.id}: None`);
      }
    } catch (e) {
      console.log(`⚠️ ${item.id}: ${e.message}`);
    }
  }

  await browser.close();

  const jsonPath = '/Users/srikarvuyyuru/SILCE/scripts/blinkit_images.json';
  let existing = JSON.parse(fs.readFileSync(jsonPath, 'utf8'));
  for (const [id, url] of Object.entries(results)) {
    if (url) existing[id] = url;
  }
  fs.writeFileSync(jsonPath, JSON.stringify(existing, null, 2));
})();
