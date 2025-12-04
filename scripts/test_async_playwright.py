import asyncio
from playwright.async_api import async_playwright

async def main():
    print("Starting playwright...")
    async with async_playwright() as p:
        print("Launching browser...")
        browser = await p.firefox.launch(headless=True)
        print("Browser launched.")
        context = await browser.new_context(ignore_https_errors=True)
        page = await context.new_page()
        print("Page created.")
        await page.goto("https://example.com")
        print("Navigated to example.com")
        title = await page.title()
        print(f"Title: {title}")
        await browser.close()
        print("Browser closed.")

if __name__ == "__main__":
    asyncio.run(main())
