/**
 * Apply valid Blinkit CDN images to catalog.json.
 * Skips any URL that is an icon/logo/banner (not a real product image).
 * Keeps existing image for products where extraction returned a bad URL.
 */

const fs = require('fs');

const CATALOG_PATH = '/Users/srikarvuyyuru/SILCE/data/catalog.json';
const IMAGES_PATH  = '/Users/srikarvuyyuru/SILCE/scripts/blinkit_images.json';

const catalog = JSON.parse(fs.readFileSync(CATALOG_PATH, 'utf8'));
const images  = JSON.parse(fs.readFileSync(IMAGES_PATH, 'utf8'));

// URLs to reject — these are icon/delivery-time assets, not product images
const BAD_PATTERNS = [
  'eta-icons',
  'assets/eta',
  '15-mins',
  'icon',
  'logo',
  'banner',
];

const isGoodUrl = (url) => {
  if (!url) return false;
  return BAD_PATTERNS.every(p => !url.includes(p));
};

let updated = 0;
let skipped = 0;

for (const product of catalog) {
  const cdnUrl = images[product.id];
  if (cdnUrl && isGoodUrl(cdnUrl)) {
    product.image = cdnUrl;
    updated++;
    console.log(`✅ ${product.id}  ${product.name.substring(0,40)}`);
  } else {
    skipped++;
    console.log(`⏭  ${product.id}  (kept existing) — bad URL: ${cdnUrl?.substring(0,50) || 'null'}`);
  }
}

fs.writeFileSync(CATALOG_PATH, JSON.stringify(catalog, null, 2));
console.log(`\n✅ catalog.json updated — ${updated} Blinkit CDN images applied, ${skipped} kept existing.`);
