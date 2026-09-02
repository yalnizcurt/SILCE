#!/usr/bin/env python3
import os
import sys
import subprocess

def build_pdf():
    html_path = os.path.abspath("slides.html")
    pdf_path = os.path.abspath("Myntra_StyleProof_Graduation_Project.pdf")
    
    print(f"[*] Rendering {html_path} to {pdf_path} (1920x1080 Widescreen)...")

    # Method 1: Playwright (Crisp High-DPI 1920x1080 PDF)
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(
                viewport={"width": 1920, "height": 1080},
                device_scale_factor=2
            )
            page.goto(f"file://{html_path}", wait_until="networkidle")
            page.wait_for_timeout(2000)
            page.pdf(
                path=pdf_path,
                width="1920px",
                height="1080px",
                print_background=True,
                margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
                page_ranges="1-10"
            )
            browser.close()
            print(f"[✓] Success! Generated 10-slide deck PDF via Playwright: {pdf_path}")
            return
    except Exception as e:
        print(f"[!] Playwright note: {e}. Trying Chrome headless...")

    # Method 2: Google Chrome headless CLI
    chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    if os.path.exists(chrome_path):
        cmd = [
            chrome_path,
            "--headless",
            "--disable-gpu",
            "--print-to-pdf-no-header",
            f"--print-to-pdf={pdf_path}",
            f"file://{html_path}"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            print(f"[✓] Success! Generated deck PDF via Chrome CLI: {pdf_path}")
            return
        else:
            print(f"[!] Chrome CLI error: {res.stderr}")

    print("[✗] Error: Unable to compile PDF.")
    sys.exit(1)

if __name__ == "__main__":
    build_pdf()
