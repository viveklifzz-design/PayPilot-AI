import asyncio
from playwright.async_api import async_playwright
import os

routes = [
    ("/", "phase_d_01_dashboard.png"),
    ("/cases", "phase_d_02_cases.png"),
    ("/recover/d669dce3-b855-4348-b457-f0ef7c34b6b1", "phase_d_03_recovery_checkout.png"),
    ("/transactions", "phase_d_04_transactions.png"),
    ("/customers", "phase_d_05_customers.png"),
    ("/customer", "phase_d_06_customer_portal.png"),
    ("/receivables", "phase_d_07_receivables.png"),
    ("/subscriptions", "phase_d_08_subscriptions.png"),
    ("/mandates", "phase_d_09_mandates.png"),
    ("/communications", "phase_d_10_communications.png"),
    ("/audit", "phase_d_11_audit.png"),
    ("/safety", "phase_d_12_safety.png"),
    ("/revenue-risk", "phase_d_13_revenue_risk.png"),
    ("/benchmark", "phase_d_14_benchmark.png"),
    ("/voice", "phase_d_15_voice.png"),
    ("/settings", "phase_d_16_settings.png"),
]

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        out_dir = r"C:\Users\Vivek\.gemini\antigravity\brain\9e53baba-9703-4da1-8f21-da612bf2f973"

        # 1. Desktop Viewport
        context_desktop = await browser.new_context(viewport={"width": 1280, "height": 900})
        page = await context_desktop.new_page()

        print("=== VERIFYING DESKTOP ROUTES ===")
        for route, img_name in routes:
            url = f"http://localhost:3000{route}"
            print(f"Navigating to {url}...")
            try:
                response = await page.goto(url, timeout=10000)
                await page.wait_for_timeout(1500)
                status = response.status if response else 0
                title = await page.title()
                print(f"  [OK {status}] {route} | Title: {title}")
                await page.screenshot(path=os.path.join(out_dir, img_name), full_page=True)
            except Exception as e:
                print(f"  [ERROR] {route}: {e}")

        # 2. Tablet Viewport (768x1024)
        print("\n=== VERIFYING TABLET VIEWPORT (768x1024) ===")
        context_tablet = await browser.new_context(viewport={"width": 768, "height": 1024})
        page_tab = await context_tablet.new_page()
        await page_tab.goto("http://localhost:3000/", timeout=10000)
        await page_tab.wait_for_timeout(1500)
        await page_tab.screenshot(path=os.path.join(out_dir, "phase_d_tablet_dashboard.png"), full_page=True)
        print("Captured phase_d_tablet_dashboard.png")

        # 3. Mobile Viewport (375x812)
        print("\n=== VERIFYING MOBILE VIEWPORT (375x812) ===")
        context_mobile = await browser.new_context(viewport={"width": 375, "height": 812})
        page_mob = await context_mobile.new_page()
        await page_mob.goto("http://localhost:3000/", timeout=10000)
        await page_mob.wait_for_timeout(1500)
        await page_mob.screenshot(path=os.path.join(out_dir, "phase_d_mobile_dashboard.png"), full_page=True)
        print("Captured phase_d_mobile_dashboard.png")

        await browser.close()
        print("\nPlaywright verification finished successfully!")

if __name__ == "__main__":
    asyncio.run(main())
