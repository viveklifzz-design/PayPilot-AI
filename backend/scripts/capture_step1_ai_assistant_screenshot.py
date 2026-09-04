import asyncio
import os
from playwright.async_api import async_playwright

async def capture_screenshot():
    artifact_dir = r"C:\Users\Vivek\.gemini\antigravity\brain\9e53baba-9703-4da1-8f21-da612bf2f973"
    output_path = os.path.join(artifact_dir, "step1_ai_recovery_assistant.png")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 1080})
        page = await context.new_page()

        print("Navigating to http://localhost:3000/cases...")
        await page.goto("http://localhost:3000/cases", wait_until="networkidle")
        await asyncio.sleep(2)

        print("Locating real recovery case d669dce3...")
        # Click row or Inspect button for case d669dce3
        case_row = page.locator("tr").filter(has_text="d669dce3")
        if await case_row.count() > 0:
            inspect_btn = case_row.locator("button", has_text="Inspect").first
            if await inspect_btn.count() > 0:
                await inspect_btn.click()
            else:
                await case_row.first.click()
        else:
            print("Case d669dce3 row not found directly, clicking first row...")
            await page.locator("tr").first.click()

        await asyncio.sleep(3) # Wait for AI Assessment API to load inside drawer

        print(f"Saving screenshot to {output_path}...")
        await page.screenshot(path=output_path, full_page=True)
        await browser.close()
        print("Screenshot captured successfully!")

if __name__ == "__main__":
    asyncio.run(capture_screenshot())
