/**
 * Blinkit Image Extractor v2 — Network Interception
 * Intercepts Blinkit's own search API JSON response instead of scraping DOM.
 * This is far more reliable than waiting for img tags to render.
 */

const { chromium } = require('playwright');
const fs = require('fs');

const PRODUCTS = [
  { id: 'prod_104', query: 'Amul Taaza Milk 1L' },
  { id: 'prod_112', query: 'English Cucumber 500g' },
  { id: 'prod_113', query: 'Fresh Tomatoes 500g' },
  { id: 'prod_210', query: 'Fresho Farm Fresh Eggs 6 pcs' },
  { id: 'prod_211', query: 'Mother Dairy Curd 400g' },
  { id: 'prod_213', query: 'Harvest Gold Bread' },
  { id: 'prod_214', query: 'Amul Butter 100g' },
  { id: 'prod_105', query: 'Society Masala Tea 250g' },
  { id: 'prod_106', query: 'Parle G Gold Biscuits' },
  { id: 'prod_108', query: 'Daawat Basmati Rice 1kg' },
  { id: 'prod_109', query: 'Aashirvaad Atta 5kg' },
  { id: 'prod_114', query: 'Fresh Onion 1kg' },
  { id: 'prod_115', query: 'Fresh Spinach Palak 250g' },
  { id: 'prod_301', query: 'Coca Cola 1.25L' },
  { id: 'prod_302', query: 'Lays Classic Salted Chips 50g' },
  { id: 'prod_303', query: 'Kwality Walls Vanilla Ice Cream' },
  { id: 'prod_401', query: 'Gold Flake Kings Cigarettes 10' },
  { id: 'prod_402', query: 'Doublemint Peppermint Mints' },
  { id: 'prod_501', query: 'Nescafe Classic Instant Coffee 50g' },
  { id: 'prod_503', query: 'Maggi Masala Noodles 4 pack' },
  { id: 'prod_504', query: 'Paper Tea Coffee Cups disposable 20pcs' },
  { id: 'prod_601', query: 'Crocin Pain Relief Tablets' },
  { id: 'prod_602', query: 'Electral ORS Apple drink' },
  { id: 'prod_603', query: 'Digital Body Thermometer' },
  { id: 'prod_604', query: 'Face Tissues Origami 100 sheets' },
  { id: 'prod_701', query: 'Black Garbage Bags 30 pcs' },
  { id: 'prod_702', query: 'Lizol Disinfectant Floor Cleaner 500ml' },
  { id: 'prod_703', query: 'Pril Dishwash Liquid Gel 425ml' },
  { id: 'prod_704', query: 'Scotch Brite Sponge Wipes 3pcs' },
  { id: 'prod_801', query: 'Roasted Salted Almonds 50g' },
  { id: 'prod_802', query: 'Kissan Mixed Fruit Jam 200g' },
  { id: 'prod_803', query: 'Solo Paper Plates 10pcs' },
  { id: 'prod_804', query: 'Vicks Action 500 Tablets' },
  { id: 'prod_805', query: 'Colin Multi Surface Cleaner Spray 250ml' },
  { id: 'prod_806', query: 'Bisleri Mineral Water 1L' },
  { id: 'prod_807', query: 'Rin Detergent Bar 150g' },
  { id: 'prod_808', query: 'Odonil Solid Air Freshener' },
  { id: 'prod_809', query: 'Colgate Strong Teeth Toothpaste 50g' },
  { id: 'prod_810', query: 'Limcee Vitamin C Chewable Tablets' },
  { id: 'prod_811', query: 'Bicycle Playing Cards deck' },
  { id: 'prod_812', query: 'Vim Dishwash Bar 250g' },
];

// Extract image URL from Blinkit API JSON response
function extractFromApiJson(json) {
  const urls = [];
  const str = JSON.stringify(json);
  // Match cdn.grofers.com or cdn.blinkit.com URLs in JSON
  const matches = str.match(/https:\/\/cdn\.(?:grofers|blinkit)\.com\/[^"\\]+\.(?:png|jpg|jpeg|webp)[^"\\]*/g);
  if (matches) urls.push(...matches);
  return urls;
}

// Recursively search for image fields in nested JSON
function deepFindImages(obj, depth = 0) {
  if (depth > 10 || !obj) return [];
  const results = [];
  if (typeof obj === 'string' && (obj.includes('cdn.grofers.com') || obj.includes('cdn.blinkit.com'))) {
    if (obj.match(/\.(png|jpg|jpeg|webp)/i)) results.push(obj);
  } else if (Array.isArray(obj)) {
    for (const item of obj) results.push(...deepFindImages(item, depth + 1));
  } else if (typeof obj === 'object') {
    for (const val of Object.values(obj)) results.push(...deepFindImages(val, depth + 1));
  }
  return results;
}

async function fetchWithInterception(page, query) {
  const captured = [];

  // Intercept API responses
  const handler = async (response) => {
    const url = response.url();
    // Blinkit's search/listing API endpoints
    if (
      url.includes('/v2/search') ||
      url.includes('/v1/search') ||
      url.includes('/listing') ||
      url.includes('/products') ||
      url.includes('/search?') ||
      url.includes('blinkit.com/v')
    ) {
      try {
        const ct = response.headers()['content-type'] || '';
        if (ct.includes('json')) {
          const json = await response.json();
          const imgs = deepFindImages(json);
          captured.push(...imgs);
        }
      } catch (_) {}
    }
  };

  page.on('response', handler);

  try {
    const searchUrl = `https://blinkit.com/s/?q=${encodeURIComponent(query)}`;
    await page.goto(searchUrl, { waitUntil: 'networkidle', timeout: 20000 });
    await page.waitForTimeout(1500);
  } catch (_) {
    // timeout ok — we may have caught what we need
  }

  page.off('response', handler);

  // Also try DOM fallback after page load
  const domImgs = await page.evaluate(() => {
    return Array.from(document.querySelectorAll('img'))
      .map(img => img.src || img.getAttribute('src') || '')
      .filter(src => src.includes('cdn.grofers.com') || src.includes('cdn.blinkit.com'));
  }).catch(() => []);

  captured.push(...domImgs);
  return [...new Set(captured)]; // deduplicate
}

(async () => {
  console.log('🚀 Starting Blinkit Image Extractor v2 (Network Interception)\n');

  const browser = await chromium.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-blink-features=AutomationControlled'],
  });

  const context = await browser.newContext({
    userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    geolocation: { latitude: 28.6139, longitude: 77.2090 }, // Delhi
    permissions: ['geolocation'],
    locale: 'en-IN',
    viewport: { width: 1280, height: 800 },
  });

  // Mask automation
  await context.addInitScript(() => {
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
  });

  const page = await context.newPage();

  // Warm up — visit homepage and set location
  console.log('🌍 Warming up on Blinkit homepage...');
  try {
    await page.goto('https://blinkit.com', { waitUntil: 'domcontentloaded', timeout: 20000 });
    await page.waitForTimeout(3000);
  } catch (_) {}

  const results = {};
  let found = 0;

  for (const product of PRODUCTS) {
    process.stdout.write(`  [${product.id}] ${product.query.substring(0, 40).padEnd(40)} `);

    const imgs = await fetchWithInterception(page, product.query);

    // Filter: prefer product images (not icons/logos/banners)
    const productImgs = imgs.filter(url =>
      !url.includes('icon') &&
      !url.includes('logo') &&
      !url.includes('banner') &&
      !url.includes('category') &&
      (url.includes('product') || url.includes('cms-assets') || url.includes('app/images'))
    );

    const best = productImgs[0] || imgs[0] || null;
    results[product.id] = best;

    if (best) {
      found++;
      console.log(`✅ ${best.substring(0, 60)}...`);
    } else {
      console.log(`❌ not found`);
    }

    await page.waitForTimeout(800);
  }

  await browser.close();

  console.log(`\n📊 ${found}/${PRODUCTS.length} images found`);

  // Save JSON
  const outPath = '/Users/srikarvuyyuru/SILCE/scripts/blinkit_images.json';
  fs.writeFileSync(outPath, JSON.stringify(results, null, 2));
  console.log(`✅ Saved to ${outPath}\n`);

  // Print summary of found URLs
  console.log('Found URLs:');
  for (const [id, url] of Object.entries(results)) {
    if (url) console.log(`  ${id}: ${url}`);
  }
})();
