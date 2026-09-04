import os
import time
from playwright.sync_api import sync_playwright

def capture_screens():
    os.makedirs("static/screenshots", exist_ok=True)
    os.makedirs("MyntraStyleProof/static/screenshots", exist_ok=True)
    os.makedirs("deck_images", exist_ok=True)
    target_url = "http://localhost:8080"
    
    print(f"[*] Starting high-DPI mobile UI capture on {target_url}...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 390, "height": 844},
            device_scale_factor=2,
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1"
        )
        page = context.new_page()
        
        # ----------------------------------------------------------------------
        # 1. As-Is Baseline (Authentic Consumer Wishlist Screen without Debug Controls)
        # ----------------------------------------------------------------------
        page.goto(target_url, wait_until="networkidle")
        page.wait_for_timeout(1000)
        
        page.evaluate("""() => {
            // Remove QA/debug harness completely
            document.querySelectorAll('.pm-harness-bar').forEach(el => el.remove());
            document.querySelectorAll('.inspector-explainer-banner').forEach(el => el.remove());
            document.querySelectorAll('.pm-card-diagnostic-overlay').forEach(el => el.remove());
            document.querySelectorAll('.styleproof-badge').forEach(el => el.remove());
            document.querySelectorAll('.styleproof-pill').forEach(el => el.remove());
            document.querySelectorAll('.toast').forEach(el => el.remove());
            
            // Remove any debug toast container
            const toasts = document.querySelectorAll('div');
            toasts.forEach(t => {
                if (t.innerText && (t.innerText.includes('PM Inspector') || t.innerText.includes('Diagnostics'))) {
                    t.remove();
                }
            });

            // Set authentic customer context header with clean flex layout
            const bar = document.getElementById('persona-context-bar');
            if (bar) {
                bar.style.cssText = 'display:flex; align-items:center; justify-content:space-between; padding:10px 14px; background:#ffffff; border-bottom:1px solid #e2e8f0;';
                bar.innerHTML = `
                  <div style="display:flex; align-items:center; gap:10px;">
                    <div style="width:36px; height:36px; border-radius:50%; background:#ff3f6c; color:#fff; font-weight:800; display:flex; align-items:center; justify-content:center; font-size:13px;">AS</div>
                    <div>
                      <div style="display:flex; align-items:center; gap:6px;">
                        <strong style="font-size:13px; color:#282c3f;">Arjun Sharma</strong>
                        <span style="font-size:10px; font-weight:700; color:#0f766e; background:#f0fdfa; border:1px solid #ccfbf1; padding:1px 6px; border-radius:10px;">Returning Customer</span>
                      </div>
                      <div style="font-size:11px; color:#64748b; margin-top:2px;">
                        <span>📏 5'9"</span> • <span>⚖️ 68kg</span> • <span>🏷️ Zara: M | Levi's: 32</span>
                      </div>
                    </div>
                  </div>
                  <div style="font-size:10px; font-weight:700; color:#0f766e; background:#f0fdfa; border:1px solid #ccfbf1; padding:4px 8px; border-radius:12px; text-align:right;">
                    3 Orders/Quarter
                  </div>
                `;
            }

            // Populate wishlist grid with 4 authentic items to eliminate dead bottom whitespace
            const grid = document.getElementById('wishlist-grid');
            if (grid) {
                grid.innerHTML = `
                  <div class="wishlist-card" style="border:1px solid #e2e8f0; border-radius:8px; overflow:hidden; background:#fff;">
                    <div style="position:relative;">
                      <img src="https://images.unsplash.com/photo-1521223890158-f9f7c3d5d504?w=500&q=80" style="width:100%; height:180px; object-fit:cover; display:block;">
                      <div style="position:absolute; bottom:6px; left:6px; background:rgba(255,255,255,0.9); padding:2px 6px; border-radius:4px; font-size:10px; font-weight:700;">4.3 ★ | 1.3k</div>
                    </div>
                    <div style="padding:8px 10px;">
                      <div style="font-size:13px; font-weight:700; color:#282c3f;">ROADSTER</div>
                      <div style="font-size:11px; color:#535766; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">Men Brown Suede Jacket</div>
                      <div style="display:flex; align-items:center; gap:6px; margin:4px 0 6px;">
                        <span style="font-size:14px; font-weight:700; color:#282c3f;">₹2,499</span>
                        <span style="font-size:9px; color:#0f766e; background:#f0fdfa; border:1px solid #ccfbf1; padding:1px 4px; border-radius:3px; font-weight:700;">Full Catalog Price</span>
                      </div>
                      <div style="border:1px solid #d4d5d9; border-radius:4px; padding:5px 8px; font-size:11px; font-weight:600; color:#282c3f; display:flex; justify-content:space-between; margin-bottom:8px;">
                        <span>Size: <strong>Select Size ▾</strong></span>
                        <span style="color:#ff3f6c; font-size:10px; font-weight:700;">Size Chart</span>
                      </div>
                      <button style="width:100%; border:1px solid #d4d5d9; background:#fff; color:#282c3f; font-weight:700; font-size:12px; padding:8px; border-radius:4px; text-align:center;">MOVE TO BAG</button>
                    </div>
                  </div>

                  <div class="wishlist-card" style="border:1px solid #e2e8f0; border-radius:8px; overflow:hidden; background:#fff;">
                    <div style="position:relative;">
                      <img src="https://images.unsplash.com/photo-1551028719-00167b16eac5?w=500&q=80" style="width:100%; height:180px; object-fit:cover; display:block;">
                      <div style="position:absolute; bottom:6px; left:6px; background:rgba(255,255,255,0.9); padding:2px 6px; border-radius:4px; font-size:10px; font-weight:700;">4.1 ★ | 870</div>
                    </div>
                    <div style="padding:8px 10px;">
                      <div style="font-size:13px; font-weight:700; color:#282c3f;">HIGHLANDER</div>
                      <div style="font-size:11px; color:#535766; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">Tan Faux Suede Bomber</div>
                      <div style="display:flex; align-items:center; gap:6px; margin:4px 0 6px;">
                        <span style="font-size:14px; font-weight:700; color:#282c3f;">₹1,999</span>
                        <span style="font-size:9px; color:#0f766e; background:#f0fdfa; border:1px solid #ccfbf1; padding:1px 4px; border-radius:3px; font-weight:700;">Full Catalog Price</span>
                      </div>
                      <div style="border:1px solid #d4d5d9; border-radius:4px; padding:5px 8px; font-size:11px; font-weight:600; color:#282c3f; display:flex; justify-content:space-between; margin-bottom:8px;">
                        <span>Size: <strong>Select Size ▾</strong></span>
                        <span style="color:#ff3f6c; font-size:10px; font-weight:700;">Size Chart</span>
                      </div>
                      <button style="width:100%; border:1px solid #d4d5d9; background:#fff; color:#282c3f; font-weight:700; font-size:12px; padding:8px; border-radius:4px; text-align:center;">MOVE TO BAG</button>
                    </div>
                  </div>

                  <div class="wishlist-card" style="border:1px solid #e2e8f0; border-radius:8px; overflow:hidden; background:#fff;">
                    <div style="position:relative;">
                      <img src="https://images.unsplash.com/photo-1542272604-787c3835535d?w=500&q=80" style="width:100%; height:170px; object-fit:cover; display:block;">
                      <div style="position:absolute; bottom:6px; left:6px; background:rgba(255,255,255,0.9); padding:2px 6px; border-radius:4px; font-size:10px; font-weight:700;">4.5 ★ | 2.1k</div>
                    </div>
                    <div style="padding:8px 10px;">
                      <div style="font-size:13px; font-weight:700; color:#282c3f;">LEVI'S</div>
                      <div style="font-size:11px; color:#535766; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">511 Slim Fit Dark Jeans</div>
                      <div style="display:flex; align-items:center; gap:6px; margin:4px 0 6px;">
                        <span style="font-size:14px; font-weight:700; color:#282c3f;">₹2,899</span>
                        <span style="font-size:9px; color:#0f766e; background:#f0fdfa; border:1px solid #ccfbf1; padding:1px 4px; border-radius:3px; font-weight:700;">Full Catalog Price</span>
                      </div>
                      <div style="border:1px solid #d4d5d9; border-radius:4px; padding:5px 8px; font-size:11px; font-weight:600; color:#282c3f; display:flex; justify-content:space-between; margin-bottom:8px;">
                        <span>Size: <strong>Select Size ▾</strong></span>
                        <span style="color:#ff3f6c; font-size:10px; font-weight:700;">Size Chart</span>
                      </div>
                      <button style="width:100%; border:1px solid #d4d5d9; background:#fff; color:#282c3f; font-weight:700; font-size:12px; padding:8px; border-radius:4px; text-align:center;">MOVE TO BAG</button>
                    </div>
                  </div>

                  <div class="wishlist-card" style="border:1px solid #e2e8f0; border-radius:8px; overflow:hidden; background:#fff;">
                    <div style="position:relative;">
                      <img src="https://images.unsplash.com/photo-1560769629-975ec94e6a86?w=500&q=80" style="width:100%; height:170px; object-fit:cover; display:block;">
                      <div style="position:absolute; bottom:6px; left:6px; background:rgba(255,255,255,0.9); padding:2px 6px; border-radius:4px; font-size:10px; font-weight:700;">4.4 ★ | 1.8k</div>
                    </div>
                    <div style="padding:8px 10px;">
                      <div style="font-size:13px; font-weight:700; color:#282c3f;">HRX</div>
                      <div style="font-size:11px; color:#535766; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">Off-White Street Sneakers</div>
                      <div style="display:flex; align-items:center; gap:6px; margin:4px 0 6px;">
                        <span style="font-size:14px; font-weight:700; color:#282c3f;">₹2,199</span>
                        <span style="font-size:9px; color:#0f766e; background:#f0fdfa; border:1px solid #ccfbf1; padding:1px 4px; border-radius:3px; font-weight:700;">Full Catalog Price</span>
                      </div>
                      <div style="border:1px solid #d4d5d9; border-radius:4px; padding:5px 8px; font-size:11px; font-weight:600; color:#282c3f; display:flex; justify-content:space-between; margin-bottom:8px;">
                        <span>Size: <strong>Select Size ▾</strong></span>
                        <span style="color:#ff3f6c; font-size:10px; font-weight:700;">Size Chart</span>
                      </div>
                      <button style="width:100%; border:1px solid #d4d5d9; background:#fff; color:#282c3f; font-weight:700; font-size:12px; padding:8px; border-radius:4px; text-align:center;">MOVE TO BAG</button>
                    </div>
                  </div>
                `;
            }

            const wishlistMain = document.querySelector('.wishlist-main');
            if (wishlistMain) wishlistMain.style.paddingBottom = '20px';
        }""")
        page.wait_for_timeout(400)
        
        p1 = "static/screenshots/screen_1_as_is.png"
        page.screenshot(path=p1)
        page.screenshot(path="MyntraStyleProof/static/screenshots/screen_1_as_is.png")
        page.screenshot(path="deck_images/screen_1_as_is.png")
        print(f"[✓] Screen 1: Sanitized As-Is Wishlist captured -> {p1}")

        # ----------------------------------------------------------------------
        # 2. To-Be Flat-Lay Wardrobe Lookbook Canvas (Full Screen, Zero Top Deadspace)
        # ----------------------------------------------------------------------
        page.goto(target_url, wait_until="networkidle")
        page.wait_for_timeout(1000)
        
        page.evaluate("() => { if (window.openLookbook) window.openLookbook('SKU_ROADSTER_JACKET'); }")
        page.wait_for_selector("#styleproof-content", state="visible", timeout=10000)
        page.wait_for_timeout(600)
        
        page.evaluate("""() => {
            const overlay = document.getElementById('styleproof-modal-overlay');
            if (overlay) {
                overlay.style.background = '#f8f9fa';
                overlay.style.alignItems = 'stretch';
            }
            const sheet = document.querySelector('.modal-bottom-sheet');
            if (sheet) {
                sheet.style.maxHeight = '100vh';
                sheet.style.height = '100%';
                sheet.style.borderRadius = '0';
                sheet.style.boxShadow = 'none';
                sheet.style.position = 'relative';
            }
            const handle = document.querySelector('.modal-handle-bar');
            if (handle) handle.style.display = 'none';

            const cal = document.querySelector('.brand-calibration-section');
            if (cal) cal.style.display = 'none';
            const dedup = document.getElementById('deduplication-section');
            if (dedup) dedup.style.display = 'none';

            const lookbookSection = document.querySelector('.lookbook-section');
            if (lookbookSection) {
                lookbookSection.style.padding = '16px 14px 20px';
                
                // Enhance canvas container
                const canvasContainer = document.querySelector('.outfit-canvas-container');
                if (canvasContainer) {
                    canvasContainer.style.padding = '16px 10px';
                    canvasContainer.style.margin = '10px 0 14px';
                }

                // Make canvas item images taller and more premium
                document.querySelectorAll('.canvas-img-box').forEach(box => {
                    box.style.height = '120px';
                });
                
                if (!document.getElementById('palette-harmony-row')) {
                    const paletteRow = document.createElement('div');
                    paletteRow.id = 'palette-harmony-row';
                    paletteRow.style.cssText = 'margin-top:14px; background:#ffffff; border:1px solid #e2e8f0; border-radius:8px; padding:14px;';
                    paletteRow.innerHTML = `
                      <div style="font-size:11px; font-weight:700; color:#1e293b; margin-bottom:10px; display:flex; justify-content:space-between; align-items:center;">
                        <span>🎨 WARDROBE COLOR PALETTE HARMONY</span>
                        <span style="color:#0f766e; font-weight:800; background:#f0fdfa; border:1px solid #ccfbf1; padding:2px 8px; border-radius:10px;">High Affinity (0.94)</span>
                      </div>
                      <div style="display:flex; gap:8px; margin-bottom:10px;">
                        <div style="flex:1; background:#8B5A2B; color:#fff; font-size:10px; font-weight:700; padding:8px 4px; border-radius:4px; text-align:center;">Caramel Suede</div>
                        <div style="flex:1; background:#1C2333; color:#fff; font-size:10px; font-weight:700; padding:8px 4px; border-radius:4px; text-align:center;">Dark Indigo</div>
                        <div style="flex:1; background:#F4F4F5; color:#18181b; border:1px solid #d4d4d8; font-size:10px; font-weight:700; padding:8px 4px; border-radius:4px; text-align:center;">Off-White Lows</div>
                      </div>
                      <div style="font-size:11px; color:#64748b; line-height:1.5;">
                        <strong>Occasion Versatility:</strong> Smart Casual • Evening Dinners • Weekend Travel (₹0 Added Cart Spend)
                      </div>
                    `;
                    lookbookSection.appendChild(paletteRow);
                }
            }

            const cta = document.querySelector('.modal-cta-sticky');
            if (cta) {
                cta.style.position = 'absolute';
                cta.style.bottom = '0';
                cta.style.left = '0';
                cta.style.right = '0';
                cta.style.background = '#ffffff';
                cta.style.borderTop = '1px solid #e2e8f0';
                cta.style.padding = '10px 14px 14px';
                cta.style.zIndex = '50';
            }

            const body = document.getElementById('modal-body-content');
            if (body) {
                body.scrollTop = 0;
                body.style.paddingBottom = '110px';
            }
        }""")
        page.wait_for_timeout(400)
        
        p2 = "static/screenshots/screen_2_lookbook.png"
        page.screenshot(path=p2)
        page.screenshot(path="MyntraStyleProof/static/screenshots/screen_2_lookbook.png")
        page.screenshot(path="static/screenshots/screen_2_trigger.png")
        page.screenshot(path="deck_images/screen_2_lookbook.png")
        print(f"[✓] Screen 2: Full-screen Lookbook Canvas captured -> {p2}")

        # ----------------------------------------------------------------------
        # 3. To-Be Brand Size Calibration Delta & Deduplication Tray (Full Screen)
        # ----------------------------------------------------------------------
        page.goto(target_url, wait_until="networkidle")
        page.wait_for_timeout(1000)
        
        page.evaluate("() => { if (window.openLookbook) window.openLookbook('SKU_ROADSTER_JACKET'); }")
        page.wait_for_selector("#styleproof-content", state="visible", timeout=10000)
        page.wait_for_timeout(600)
        
        page.evaluate("""() => {
            const overlay = document.getElementById('styleproof-modal-overlay');
            if (overlay) {
                overlay.style.background = '#f8f9fa';
                overlay.style.alignItems = 'stretch';
            }
            const sheet = document.querySelector('.modal-bottom-sheet');
            if (sheet) {
                sheet.style.maxHeight = '100vh';
                sheet.style.height = '100%';
                sheet.style.borderRadius = '0';
                sheet.style.boxShadow = 'none';
                sheet.style.position = 'relative';
            }
            const handle = document.querySelector('.modal-handle-bar');
            if (handle) handle.style.display = 'none';

            const lookbook = document.querySelector('.lookbook-section');
            if (lookbook) lookbook.style.display = 'none';
            
            const cal = document.querySelector('.brand-calibration-section');
            if (cal) {
                cal.style.display = 'block';
                cal.style.padding = '10px 14px 8px';
                cal.style.marginBottom = '6px';
            }
            const calCard = document.querySelector('.calibration-card');
            if (calCard) {
                calCard.style.padding = '12px 14px';
            }
            
            const dedup = document.getElementById('deduplication-section');
            if (dedup) {
                dedup.style.display = 'block';
                dedup.style.padding = '8px 14px 8px';
                dedup.style.marginBottom = '6px';
            }
            const dedupGrid = document.getElementById('dedup-comparison-grid');
            if (dedupGrid) {
                dedupGrid.style.marginTop = '6px';
                dedupGrid.querySelectorAll('.dedup-card').forEach(card => {
                    card.style.padding = '10px 12px';
                });
                dedupGrid.querySelectorAll('.dedup-item-price').forEach(dip => {
                    const priceText = dip.innerText.split(' ')[0] || '₹2,499';
                    dip.innerHTML = `
                      <div style="display:flex; flex-direction:column; gap:2px; margin:2px 0 6px;">
                        <span style="font-size:14px; font-weight:800; color:#282c3f;">${priceText}</span>
                        <span style="font-size:8.5px; font-weight:700; color:#0f766e; background:#f0fdfa; border:1px solid #ccfbf1; padding:1px 4px; border-radius:3px; width:fit-content;">Full Catalog Price • ₹0 Discount Spend</span>
                      </div>
                    `;
                });
            }
            
            const cta = document.querySelector('.modal-cta-sticky');
            if (cta) {
                cta.style.position = 'absolute';
                cta.style.bottom = '0';
                cta.style.left = '0';
                cta.style.right = '0';
                cta.style.background = '#ffffff';
                cta.style.borderTop = '1px solid #e2e8f0';
                cta.style.padding = '10px 14px 14px';
                cta.style.zIndex = '50';
            }
            
            const body = document.getElementById('modal-body-content');
            if (body) {
                body.scrollTop = 0;
                body.style.paddingBottom = '110px';
            }
        }""")
        page.wait_for_timeout(400)
        
        p3 = "static/screenshots/screen_3_tray.png"
        page.screenshot(path=p3)
        page.screenshot(path="MyntraStyleProof/static/screenshots/screen_3_tray.png")
        page.screenshot(path="deck_images/screen_3_tray.png")
        print(f"[✓] Screen 3: Sanitized Full-screen Calibration & Deduplication Tray captured -> {p3}")

        browser.close()
        print("[✓] All 3 screens successfully captured and saved!")

if __name__ == "__main__":
    capture_screens()
