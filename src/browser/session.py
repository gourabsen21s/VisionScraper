import asyncio
import logging
import base64
from typing import Optional, List
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from src.browser.profile import BrowserProfile
from src.browser.views import BrowserState, BrowserStateSummary, TabInfo, PageInfo
from src.dom.service import CDPDomService

logger = logging.getLogger(__name__)

class BrowserSession:
    def __init__(self, profile: Optional[BrowserProfile] = None):
        self.profile = profile or BrowserProfile()
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.dom_service: Optional[CDPDomService] = None

    async def start(self):
        """Starts the browser session."""
        self.playwright = await async_playwright().start()
        
        args = self.profile.get_playwright_args()
        
        self.browser = await self.playwright.chromium.launch(
            headless=self.profile.headless,
            args=args,
            proxy=self.profile.proxy
        )
        
        self.context = await self.browser.new_context(
            viewport=self.profile.viewport.model_dump(),
            user_agent=self.profile.user_agent,
            accept_downloads=True
        )
        
        self.page = await self.context.new_page()
        self.dom_service = CDPDomService(self.page)
        logger.info("Browser session started")

    async def close(self):
        """Closes the browser session."""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        logger.info("Browser session closed")

    async def navigate(self, url: str):
        if not self.page:
            raise RuntimeError("Session not started")
        await self.page.goto(url)
        await self.page.wait_for_load_state("networkidle")

    async def get_state(self) -> BrowserState:
        """Legacy method for backward compatibility."""
        summary = await self.get_browser_state_summary()
        return BrowserState(
            url=summary.url,
            title=summary.title,
            tabs=summary.tabs,
            screenshot=summary.screenshot,
            dom_state=summary.dom_state,
            pixels_above=summary.pixels_above,
            pixels_below=summary.pixels_below
        )

    async def get_browser_state_summary(self, include_screenshot: bool = False, include_recent_events: bool = False) -> BrowserStateSummary:
        if not self.page or not self.dom_service:
            raise RuntimeError("Session not started")
        
        # Get DOM snapshot
        dom_state = await self.dom_service.get_snapshot()
        
        # Get screenshot if requested
        screenshot_b64 = None
        if include_screenshot:
            try:
                screenshot = await self.page.screenshot(type='jpeg', quality=50)
                screenshot_b64 = base64.b64encode(screenshot).decode('utf-8')
            except Exception as e:
                logger.warning(f"Failed to capture screenshot: {e}")

        # Get tabs
        tabs = []
        for i, p in enumerate(self.context.pages):
            tabs.append(TabInfo(page_id=i, url=p.url, title=await p.title()))

        # Get Page Info (Scroll/Viewport)
        # This is a simplified version. For full fidelity we'd need CDP layout metrics.
        # But we can get basic info from JS.
        page_info = await self._get_page_info()

        return BrowserStateSummary(
            dom_state=dom_state,
            url=self.page.url,
            title=await self.page.title(),
            tabs=tabs,
            screenshot=screenshot_b64,
            page_info=page_info,
            pixels_above=page_info.pixels_above,
            pixels_below=page_info.pixels_below
        )

    async def _get_page_info(self) -> PageInfo:
        """Retrieves page scroll and viewport info via JS."""
        info = await self.page.evaluate("""() => {
            const { innerWidth, innerHeight, scrollX, scrollY } = window;
            const { scrollWidth, scrollHeight } = document.documentElement;
            return {
                viewport_width: innerWidth,
                viewport_height: innerHeight,
                page_width: scrollWidth,
                page_height: scrollHeight,
                scroll_x: scrollX,
                scroll_y: scrollY,
            }
        }""")
        
        return PageInfo(
            viewport_width=info['viewport_width'],
            viewport_height=info['viewport_height'],
            page_width=info['page_width'],
            page_height=info['page_height'],
            scroll_x=info['scroll_x'],
            scroll_y=info['scroll_y'],
            pixels_above=info['scroll_y'],
            pixels_below=info['page_height'] - info['viewport_height'] - info['scroll_y'],
            pixels_left=info['scroll_x'],
            pixels_right=info['page_width'] - info['viewport_width'] - info['scroll_x']
        )

    async def create_tab(self, url: str = "about:blank"):
        if not self.context:
            raise RuntimeError("Session not started")
        new_page = await self.context.new_page()
        await new_page.goto(url)
        self.page = new_page
        self.dom_service = CDPDomService(self.page)

    async def switch_tab(self, page_id: int):
        if not self.context:
            raise RuntimeError("Session not started")
        if 0 <= page_id < len(self.context.pages):
            self.page = self.context.pages[page_id]
            await self.page.bring_to_front()
            self.dom_service = CDPDomService(self.page)
        else:
            raise ValueError(f"Invalid page_id: {page_id}")
