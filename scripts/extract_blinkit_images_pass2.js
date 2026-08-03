const { chromium } = require('playwright');
const fs = require('fs');

const MISSING_PRODUCTS = [
  { id: 'prod_106', query: 'Parle-G Gold Biscuits' },
  { id: 'prod_107', query: 'Surf Excel Easy Wash Detergent Powder' },
  { id: 'prod_212', query: 'Vim Dishwash Gel' },
  { id: 'prod_115', query: 'Spinach Palak' },
  { id: 'prod_302', query: 'Lays Classic Salted Potato Chips' },
  { id: 'prod_304', query: 'Wingreens Farms Cheesy Jalapeno Dip' },
  { id: 'prod_401', query: 'Gold Flake Kings Cigarettes' },
  { id: 'prod_402', query: 'Doublemint Peppermint Chewing Gum' },
  { id: 'prod_403', query: 'Clipper Flame Lighter' },
  { id: 'prod_601', query: 'Crocin Pain Relief Tablet' },
  { id: 'prod_604', query: 'Origami Facial Tissues' },
  { id: 'prod_703', query: 'Pril Liquid Dishwash' },
  { id: 'prod_802', query: 'Kissan Mixed Fruit Jam' },
  { id: 'prod_805', query: 'Colin Glass Cleaner' },
  { id: 'prod_808', query: 'Odonil Bathroom Air Freshener' },
  { id: 'prod_811', query: 'Playing Cards Deck' }
];

(async () => {
  console.log('🚀 Running Pass 2 for remaining products...');

  const browser = await chromium.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });

  const context = await browser.newContext({
    userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    geolocation: { latitude: 28.6139, longitude: 77.2090 },
    permissions: ['geolocation'],
    locale: 'en-IN'
  });

  const page = await context.newPage();

  const results = {};

  for (const item of MISSING_PRODUCTS) {
    process.stdout.write(`Fetching ${item.id} (${item.query})... `);
    try {
      await page.goto(`https://blinkit.com/s/?q=${encodeURIComponent(item.query)}`, { waitUntil: 'domcontentloaded', timeout: 15000 });
      await page.waitForTimeout(2000);

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
        console.log(`✅ ${imageUrl.substring(0, 60)}...`);
      } else {
        console.log(`❌ None found`);
      }
    } catch (err) {
      console.log(`⚠️ Error: ${err.message}`);
    }
  }

  await browser.close();

  // Load existing blinkit_images.json and merge
  const jsonPath = '/Users/srikarvuyyuru/SILCE/scripts/blinkit_images.json';
  let existing = {};
  if (fs.existsSync(jsonPath)) {
    existing = JSON.parse(fs.readFileSync(jsonPath, 'utf8'));
  }

  for (const [id, url] of Object.entries(results)) {
    if (url) {
      existing[id] = url;
    }
  }

  fs.writeFileSync(jsonPath, JSON.stringify(existing, null, 2));
  console.log('Saved merged results to scripts/blinkit_images.json');
})();
