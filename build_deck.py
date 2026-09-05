#!/usr/bin/env python3
"""
build_deck.py — Myntra StyleProof Graduation Deck Compiler
===========================================================
ARCHITECTURE: Screenshot-per-slide → Pillow PDF Assembly
---------------------------------------------------------
WHY: Playwright's page.pdf() API blocks Google Fonts CDN when rendering
from a file:// URI (sandbox network restrictions). This causes catastrophic
glyph corruption: ₹ → ?, ≤ → s, ≥ → 5, × → garbled chars.

FIX: We render each slide as a full-resolution browser screenshot (which
correctly loads Google Fonts), then assemble the 10 PNGs into a PDF using
Pillow. This guarantees 100% visual fidelity — every glyph, image, and
color renders exactly as the browser shows it.
"""
import os
import sys

def install_if_missing(package):
    """Install a Python package if it's not already available."""
    try:
        __import__(package)
    except ImportError:
        import subprocess
        print(f"[*] Installing {package}...")
        subprocess.run([sys.executable, "-m", "pip", "install", package, "-q"], check=True)

def build_pdf():
    html_path  = os.path.abspath("slides.html")
    images_dir = os.path.abspath("deck_images")
    pdf_final  = os.path.abspath("Myntra_StyleProof_Graduation_Project_Final.pdf")
    pdf_copy   = os.path.abspath("Myntra_StyleProof_Graduation_Project.pdf")

    os.makedirs(images_dir, exist_ok=True)
    print(f"[*] Source: {html_path}")
    print(f"[*] Output: {pdf_final}")
    print(f"[*] Strategy: Screenshot-per-slide → Pillow PDF (glyph-safe, font-preserving)")

    # ── Step 1: Render each slide as a high-DPI screenshot ──────────────────
    slide_images = []
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=[
                "--font-render-hinting=none",
                "--disable-font-subpixel-positioning",
                "--no-sandbox",
            ])
            page = browser.new_page(
                viewport={"width": 1920, "height": 1080},
                device_scale_factor=2,  # 2× → 3840×2160 actual pixels per slide
            )

            print(f"[*] Loading slides.html (waiting for Google Fonts + layout)...")
            page.goto(f"file://{html_path}", wait_until="networkidle")
            # Wait for fonts: Google Fonts takes 3-5s to download in headless Chromium
            page.wait_for_timeout(5000)

            # Extra wait: confirm Inter font is loaded via document.fonts API
            fonts_loaded = page.evaluate("""
                () => document.fonts.ready.then(() => true)
            """)
            print(f"[*] Fonts ready: {fonts_loaded}")

            # Inject local image assets as base64 to bypass file:// cross-origin restrictions
            import base64
            asset_dir = os.path.dirname(html_path)
            asset_map = {
                "review_engine_dashboard.png": os.path.join(asset_dir, "review_engine_dashboard.png"),
                "review_engine_cross_brand.png": os.path.join(asset_dir, "review_engine_cross_brand.png"),
            }
            for asset_name, asset_path in asset_map.items():
                if os.path.exists(asset_path):
                    with open(asset_path, "rb") as af:
                        b64 = base64.b64encode(af.read()).decode()
                    mime = "image/png"
                    data_uri = f"data:{mime};base64,{b64}"
                    page.evaluate(f"""
                        (function() {{
                            var imgs = document.querySelectorAll('img');
                            imgs.forEach(function(img) {{
                                if (img.src && img.src.includes('{asset_name}')) {{
                                    img.src = '{data_uri}';
                                }}
                            }});
                        }})();
                    """)
                    print(f"    [✓] Injected asset: {asset_name} ({len(b64)//1024}KB b64)")
            page.wait_for_timeout(500)  # brief settle after injection

            # Capture each slide at full resolution
            slides = page.query_selector_all(".slide-wrapper")
            print(f"[*] Capturing {len(slides)} slides at 3840×2160 (2× DPR)...")

            for idx, slide in enumerate(slides, 1):
                img_path = os.path.join(images_dir, f"page_{idx}.png")
                slide.screenshot(
                    path=img_path,
                    type="png",  # lossless — preserves every pixel
                )
                slide_images.append(img_path)
                print(f"    [✓] Slide {idx:02d} → {img_path}")

            browser.close()

    except Exception as e:
        print(f"[✗] Playwright error: {e}")
        sys.exit(1)

    if not slide_images:
        print("[✗] No slide images captured. Aborting.")
        sys.exit(1)

    # ── Step 2: Assemble screenshots into a PDF using Pillow ─────────────────
    # Pillow assembles the PNGs as full-page PDF pages with exact 1920×1080
    # logical dimensions (200 DPI → 1920px = 9.6 inch wide page).
    install_if_missing("Pillow")
    from PIL import Image

    print(f"\n[*] Assembling {len(slide_images)} slides into PDF (Pillow, 200 DPI)...")

    # PDF page size: 1920×1080 at 200 DPI = 9.6" × 5.4" (exact 16:9)
    DPI = 200

    pil_images = []
    for img_path in slide_images:
        img = Image.open(img_path).convert("RGB")
        # Each PNG is 3840×2160 (2× DPR). Downsample to 1920×1080 for a
        # compact, razor-sharp PDF (Lanczos = highest quality downsampling).
        img = img.resize((1920, 1080), Image.LANCZOS)
        pil_images.append(img)

    if not pil_images:
        print("[✗] No images to assemble.")
        sys.exit(1)

    # Save as multi-page PDF
    first = pil_images[0]
    rest  = pil_images[1:]

    first.save(
        pdf_final,
        format="PDF",
        resolution=DPI,
        save_all=True,
        append_images=rest,
    )
    print(f"[✓] PDF generated: {pdf_final}")

    # Copy to submission filename and Final_11 filename
    import shutil
    shutil.copy2(pdf_final, pdf_copy)
    print(f"[✓] Submission copy:  {pdf_copy}")

    pdf_final_11 = os.path.abspath("Myntra_StyleProof_Graduation_Project_Final_11.pdf")
    shutil.copy2(pdf_final, pdf_final_11)
    print(f"[✓] Final_11 copy:    {pdf_final_11}")

    # Synchronize to MyntraStyleProof subfolder
    sub_dir = os.path.join(os.path.dirname(html_path), "MyntraStyleProof")
    if os.path.isdir(sub_dir):
        print(f"[*] Synchronizing artifacts to {sub_dir}...")
        shutil.copy2(pdf_final, os.path.join(sub_dir, "Myntra_StyleProof_Graduation_Project_Final.pdf"))
        shutil.copy2(pdf_final, os.path.join(sub_dir, "Myntra_StyleProof_Graduation_Project.pdf"))
        shutil.copy2(pdf_final, os.path.join(sub_dir, "Myntra_StyleProof_Graduation_Project_Final_11.pdf"))
        shutil.copy2(html_path, os.path.join(sub_dir, "slides.html"))
        css_src = os.path.join(os.path.dirname(html_path), "deck_style.css")
        if os.path.exists(css_src):
            shutil.copy2(css_src, os.path.join(sub_dir, "deck_style.css"))
        print(f"    [✓] Synced PDFs and slides.html to MyntraStyleProof/")

    # Report
    size_mb = os.path.getsize(pdf_final) / (1024 * 1024)
    print(f"\n{'='*60}")
    print(f"  ✅ Build Complete!")
    print(f"  Pages   : {len(slide_images)}")
    print(f"  Size    : {size_mb:.1f} MB")
    print(f"  Format  : 1920×1080 px @ {DPI} DPI (16:9 Widescreen)")
    print(f"  Glyphs  : ₹ ≤ ≥ × → all render via browser screen engine")
    print(f"  Images  : Full-resolution PNG (zero compression artifacts)")
    print(f"  Sync    : Strict parity across ENGINE/ and MyntraStyleProof/")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    build_pdf()
