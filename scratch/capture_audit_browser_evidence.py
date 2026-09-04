import asyncio
from playwright.async_api import async_playwright
import os

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 900})
        page = await context.new_page()

        out_dir = r"C:\Users\Vivek\.gemini\antigravity\brain\9e53baba-9703-4da1-8f21-da612bf2f973"

        # Scenario 1 - Payment Recovery Link Page
        print("Navigating to Scenario 1 (/recover/d669dce3-b855-4348-b457-f0ef7c34b6b1)...")
        await page.goto("http://localhost:3000/recover/d669dce3-b855-4348-b457-f0ef7c34b6b1")
        await page.wait_for_timeout(2000)
        await page.screenshot(path=os.path.join(out_dir, "phase_c_audit_scenario_1.png"), full_page=True)
        print("Captured phase_c_audit_scenario_1.png")

        # Scenario 6 - Mandate Retry Sequencer Page
        print("Navigating to Scenario 6 (/mandates)...")
        await page.goto("http://localhost:3000/mandates")
        await page.wait_for_timeout(2000)
        await page.screenshot(path=os.path.join(out_dir, "phase_c_audit_scenario_6.png"), full_page=True)
        print("Captured phase_c_audit_scenario_6.png")

        # Overview Analytics Dashboard
        print("Navigating to Overview Dashboard (/)...")
        await page.goto("http://localhost:3000/")
        await page.wait_for_timeout(2000)
        await page.screenshot(path=os.path.join(out_dir, "phase_c_audit_dashboard.png"), full_page=True)
        print("Captured phase_c_audit_dashboard.png")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
