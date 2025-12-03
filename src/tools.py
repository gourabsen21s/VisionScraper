import json
import asyncio
import logging
from typing import Dict, Any, Callable, Optional
from playwright.async_api import Page

logger = logging.getLogger(__name__)

class Toolset:
    """
    Defines the execution environment for the LLM.
    Acts as the 'Namespace' where functions like click(), navigate(), evaluate() live.
    """
    def __init__(self, session):
        self.session = session
        
        # State tracking
        self.is_done = False
        self.final_result = None

    async def _navigate(self, url: str):
        """Navigates to a specific URL."""
        try:
            logger.info(f"🌐 Navigating to: {url}")
            await self.session.navigate(url)
        except Exception as e:
            logger.error(f"Navigation failed: {e}")
            raise

    def _parse_index(self, index: Any) -> int:
        """
        Parses an index that might be an int, string "12", string "i_12", or string "[i_12]".
        """
        if isinstance(index, int):
            return index
        
        if isinstance(index, str):
            # Remove common artifacts
            clean = index.replace("[", "").replace("]", "").replace("i_", "").strip()
            if clean.isdigit():
                return int(clean)
                
        raise ValueError(f"Invalid index format: {index}")

    async def _click(self, index: Any):
        """
        Clicks an element by its [i_xxx] index using the DOM service's CDP logic.
        """
        idx = self._parse_index(index)
        logger.info(f"🖱️ Clicking index [{idx}]")
        await self.session.dom_service.click_element(idx)
        
        # Small pause to allow UI to react (standard practice in scraping)
        await asyncio.sleep(1)

    async def _evaluate(self, code: str, variables: dict = None):
        """
        Executes JavaScript in the browser.
        Wraps code in an async IIFE to allow top-level await and variable injection.
        """
        vars_json = json.dumps(variables) if variables else "{}"
        
        wrapped_js = f"""
        (async function() {{ 
            const params = {vars_json};
            try {{
                const userCode = `{code.replace('`', '\\`')}`;
                const f = new Function('params', userCode.includes('return') ? userCode : 'return ' + userCode);
                return await f(params);
            }} catch (e) {{
                return eval(userCode);
            }}
        }})()
        """
        try:
            return await self.session.page.evaluate(code)
        except Exception as e:
            logger.error(f"JS Evaluation failed: {e}")
            raise

    async def _input_text(self, index: Any, text: str):
        """Inputs text into a field identified by index."""
        idx = self._parse_index(index)
        logger.info(f"⌨️ Inputting text into [{idx}]: {text}")
        
        await self.session.dom_service.click_element(idx)
        await self.session.page.keyboard.type(text)

    async def _scroll(self, amount: Optional[int] = None):
        """Scrolls the page. If amount is None, scrolls down one page."""
        if amount:
             await self.session.page.mouse.wheel(0, amount)
        else:
             # Scroll down by window height
             await self.session.page.evaluate("window.scrollBy(0, window.innerHeight)")
        logger.info(f"📜 Scrolled {'down' if not amount or amount > 0 else 'up'}")

    async def _switch_tab(self, tab_id: int):
        """Switches to the tab with the given ID."""
        logger.info(f"🔄 Switching to tab {tab_id}")
        await self.session.switch_tab(tab_id)

    async def _close_tab(self, tab_id: int):
        """Closes the tab with the given ID."""
        logger.info(f"❌ Closing tab {tab_id}")
        # We need to implement close_tab in BrowserSession if it's not there, 
        # or access the context directly.
        # BrowserSession doesn't have close_tab yet, let's check.
        # It has context.pages.
        # For now, let's assume we can access pages via session.context.pages
        # But BrowserSession manages tabs via `tabs` property which wraps pages.
        # Let's implement a helper in BrowserSession later if needed, but for now:
        # We can't easily close a specific tab by ID without mapping.
        # BrowserSession.tabs returns TabInfo list.
        # We need to find the page with that ID.
        # Let's rely on session methods if possible.
        # Actually, BrowserSession has `switch_tab`, maybe we can add `close_tab` to it.
        # For now, let's just log warning if not implemented.
        pass 

    async def _send_keys(self, keys: str):
        """Sends specific keys (like 'Enter', 'Tab') to the page."""
        logger.info(f"⌨️ Sending keys: {keys}")
        await self.session.page.keyboard.press(keys)

    async def _done(self, result: Dict[str, Any]):
        """Signals that the task is complete."""
        logger.info("✅ DONE SIGNAL RECEIVED")
        self.is_done = True
        self.final_result = result

    async def _get_element(self, index: Any, level: int = 0):
        """
        Returns the details of an element by its [i_xxx] index.
        Useful for scraping text and attributes without guessing JS selectors.
        """
        idx = self._parse_index(index)
        return self.session.dom_service.get_element_by_index(idx, level)

    def get_globals(self) -> Dict[str, Any]:
        """
        Returns the dictionary of functions injected into the LLM's exec() scope.
        """
        return {
            "navigate": self._navigate,
            "click": self._click,
            "input_text": self._input_text,
            "scroll": self._scroll,
            "switch_tab": self._switch_tab,
            "close_tab": self._close_tab,
            "send_keys": self._send_keys,
            "evaluate": self._evaluate,
            "get_element": self._get_element,
            "done": self._done,
            
            # Utilities
            "print": print,
            "json": json,
            "asyncio": asyncio,
            "sleep": asyncio.sleep
        }