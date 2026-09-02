import os
import sys
from playwright.sync_api import sync_playwright

def generate_pdf():
    html_file = os.path.abspath("slides.html")
    output_pdf = os.path.abspath("Myntra_StyleProof_Graduation_Project.pdf")
    
    print(f"[*] Rendering {html_file} to {output_pdf} (1920x1080 per slide, High-DPI)...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(
            viewport={"width": 1920, "height": 1080},
            device_scale_factor=2  # High-DPI crisp rendering
        )
        page.goto(f"file://{html_file}", wait_until="networkidle")
        
        # Ensure fonts and images are fully rendered
        page.wait_for_timeout(2000)
        
        page.pdf(
            path=output_pdf,
            width="1920px",
            height="1080px",
            print_background=True,
            margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
            page_ranges="1-10"
        )
        browser.close()
        print(f"[✓] Successfully compiled 10-slide deck: {output_pdf}")

if __name__ == "__main__":
    generate_pdf()
