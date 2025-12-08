# runner/action_executor.py
import time
import uuid
import asyncio
from typing import Tuple, Optional, Dict, Any
from playwright.async_api import Page, TimeoutError as PWTimeoutError
from .logger import log
from .errors import ActionExecutionError, BrowserHealthError
from .retry import retry, exp_backoff_with_jitter

# Default config values; you can move to config.py if preferred
DEFAULT_ACTION_TIMEOUT = 8000  # ms
DEFAULT_RETRY_ATTEMPTS = 3

class ActionExecutor:
    """
    Wraps a Playwright Page and exposes production-quality action primitives
    with retries, backoff, and structured logging.
    Async version.
    """

    def __init__(self, page: Page, session_id: Optional[str] = None):
        self.page = page
        self.session_id = session_id or "unknown"
        self._action_prefix = "action"
        # Small guard: ensure page is valid
        if not hasattr(self.page, "evaluate"):
            raise BrowserHealthError("Invalid Playwright page object passed to ActionExecutor")

    # --------------------------
    # Helpers & logging
    # --------------------------
    def _new_action_id(self) -> str:
        return uuid.uuid4().hex

    def _log_start(self, aid: str, name: str, payload: Dict[str, Any]):
        log("INFO", f"{self._action_prefix}_start", f"Action {name} start", session_id=self.session_id, action_id=aid, **payload)

    def _log_success(self, aid: str, name: str, payload: Dict[str, Any], duration: float):
        log("INFO", f"{self._action_prefix}_success", f"Action {name} success", session_id=self.session_id, action_id=aid, duration_ms=int(duration*1000), **payload)

    def _log_failure(self, aid: str, name: str, payload: Dict[str, Any], error: str, attempt: int):
        log("ERROR", f"{self._action_prefix}_failed", f"Action {name} failed", session_id=self.session_id, action_id=aid, attempt=attempt, error=error, **payload)

    async def _ensure_page(self):
        # Basic validation that the page is usable
        if self.page is None:
            raise BrowserHealthError("Playwright page is None")
        # optionally we can try a lightweight eval to ensure the connection is alive
        try:
            await self.page.evaluate("1+1")
        except Exception as e:
            raise BrowserHealthError(f"Page health check failed: {e}")

    # --------------------------
    # Action primitives
    # --------------------------
    async def navigate(self, url: str, timeout_ms: Optional[int] = None, wait_until: str = "domcontentloaded") -> Dict[str, Any]:
        aid = self._new_action_id()
        payload = {"action": "navigate", "url": url}
        self._log_start(aid, "navigate", payload)
        start = time.time()
        try:
            await self._ensure_page()
            await self.page.goto(url, timeout=(timeout_ms or DEFAULT_ACTION_TIMEOUT), wait_until=wait_until)
            duration = time.time() - start
            self._log_success(aid, "navigate", payload, duration)
            return {"action_id": aid, "status": "success", "duration": duration}
        except Exception as e:
            duration = time.time() - start
            self._log_failure(aid, "navigate", payload, str(e), attempt=0)
            raise ActionExecutionError(f"navigate failed: {e}")

    async def wait_for_selector(self, selector: str, timeout_ms: Optional[int] = None) -> Dict[str, Any]:
        aid = self._new_action_id()
        payload = {"action": "wait_for_selector", "selector": selector}
        self._log_start(aid, "wait_for_selector", payload)
        start = time.time()
        try:
            await self._ensure_page()
            await self.page.wait_for_selector(selector, timeout=(timeout_ms or DEFAULT_ACTION_TIMEOUT))
            duration = time.time() - start
            self._log_success(aid, "wait_for_selector", payload, duration)
            return {"action_id": aid, "status": "success", "duration": duration}
        except PWTimeoutError as te:
            duration = time.time() - start
            self._log_failure(aid, "wait_for_selector", payload, str(te), attempt=0)
            raise ActionExecutionError(f"wait_for_selector timeout: {te}")
        except Exception as e:
            duration = time.time() - start
            self._log_failure(aid, "wait_for_selector", payload, str(e), attempt=0)
            raise ActionExecutionError(f"wait_for_selector failed: {e}")

    # Click by CSS selector with retries
    async def click_selector(self, selector: str, attempts: int = DEFAULT_RETRY_ATTEMPTS, timeout_ms: Optional[int] = None) -> Dict[str, Any]:
        aid = self._new_action_id()
        payload = {"action": "click_selector", "selector": selector}
        self._log_start(aid, "click_selector", payload)
        start = time.time()

        # Manual retry loop for async
        last_exc = None
        for attempt in range(attempts):
            try:
                if attempt > 0:
                    log("DEBUG","action_retry_wait", "Waiting before retry", session_id=self.session_id, action_id=aid, attempt=attempt)
                    await asyncio.sleep(0.5 * (2 ** attempt)) # simple backoff
                
                await self._ensure_page()
                await self.page.click(selector, timeout=(timeout_ms or DEFAULT_ACTION_TIMEOUT))
                
                duration = time.time() - start
                self._log_success(aid, "click_selector", payload, duration)
                return {"action_id": aid, "status": "success", "duration": duration}
            except Exception as e:
                last_exc = e
        
        duration = time.time() - start
        self._log_failure(aid, "click_selector", payload, str(last_exc), attempt=attempts)
        raise ActionExecutionError(f"click_selector failed: {last_exc}")

    # Click at absolute coordinates (x,y) with new tab detection
    async def click_xy(self, x: int, y: int, attempts: int = DEFAULT_RETRY_ATTEMPTS, handle_new_tab: bool = True) -> Dict[str, Any]:
        aid = self._new_action_id()
        payload = {"action": "click_xy", "x": x, "y": y}
        self._log_start(aid, "click_xy", payload)
        start = time.time()

        last_exc = None
        for attempt in range(attempts):
            try:
                if attempt > 0:
                    log("DEBUG","action_retry_wait","Waiting before retry", session_id=self.session_id, action_id=aid, attempt=attempt)
                    await asyncio.sleep(0.5 * (2 ** attempt))

                await self._ensure_page()
                
                # Get context to detect new tabs
                context = self.page.context
                pages_before = len(context.pages)
                
                await self.page.mouse.move(x, y)
                await self.page.mouse.click(x, y)
                
                # Wait a bit for potential new tab to open
                if handle_new_tab:
                    await asyncio.sleep(0.5)
                    pages_after = context.pages
                    
                    # If a new tab was opened, switch to it
                    if len(pages_after) > pages_before:
                        new_page = pages_after[-1]  # Get the newest page
                        log("INFO", "new_tab_detected", "New tab opened, switching to it", 
                            session_id=self.session_id, new_url=new_page.url[:80])
                        self.page = new_page
                        # Wait for the new page to load
                        try:
                            await new_page.wait_for_load_state("domcontentloaded", timeout=5000)
                        except:
                            pass  # Continue even if timeout
                
                duration = time.time() - start
                self._log_success(aid, "click_xy", payload, duration)
                return {"action_id": aid, "status": "success", "duration": duration, "new_tab": len(context.pages) > pages_before}
            except Exception as e:
                last_exc = e

        duration = time.time() - start
        self._log_failure(aid, "click_xy", payload, str(last_exc), attempt=attempts)
        raise ActionExecutionError(f"click_xy failed: {last_exc}")

    # Type text at selector
    async def type_selector(self, selector: str, text: str, clear_first: bool = True, attempts: int = DEFAULT_RETRY_ATTEMPTS) -> Dict[str, Any]:
        aid = self._new_action_id()
        payload = {"action": "type_selector", "selector": selector, "text_length": len(text)}
        self._log_start(aid, "type_selector", payload)
        start = time.time()

        last_exc = None
        for attempt in range(attempts):
            try:
                if attempt > 0:
                    log("DEBUG","action_retry_wait","Waiting before retry", session_id=self.session_id, action_id=aid, attempt=attempt)
                    await asyncio.sleep(0.5 * (2 ** attempt))

                await self._ensure_page()
                el = await self.page.wait_for_selector(selector, timeout=DEFAULT_ACTION_TIMEOUT)
                if clear_first:
                    await el.fill("")  # clear
                await el.type(text, delay=20)
                
                duration = time.time() - start
                self._log_success(aid, "type_selector", payload, duration)
                return {"action_id": aid, "status": "success", "duration": duration}
            except Exception as e:
                last_exc = e

        duration = time.time() - start
        self._log_failure(aid, "type_selector", payload, str(last_exc), attempt=attempts)
        raise ActionExecutionError(f"type_selector failed: {last_exc}")

    # Type at coordinates: click then type
    async def type_xy(self, x: int, y: int, text: str, attempts: int = DEFAULT_RETRY_ATTEMPTS) -> Dict[str, Any]:
        aid = self._new_action_id()
        payload = {"action": "type_xy", "x": x, "y": y, "text_length": len(text)}
        self._log_start(aid, "type_xy", payload)
        start = time.time()

        last_exc = None
        for attempt in range(attempts):
            try:
                if attempt > 0:
                    log("DEBUG","action_retry_wait","Waiting before retry", session_id=self.session_id, action_id=aid, attempt=attempt)
                    await asyncio.sleep(0.5 * (2 ** attempt))

                await self._ensure_page()
                await self.page.mouse.move(x, y)
                await self.page.mouse.click(x, y)
                await self.page.keyboard.type(text, delay=20)
                
                duration = time.time() - start
                self._log_success(aid, "type_xy", payload, duration)
                return {"action_id": aid, "status": "success", "duration": duration}
            except Exception as e:
                last_exc = e

        duration = time.time() - start
        self._log_failure(aid, "type_xy", payload, str(last_exc), attempt=attempts)
        raise ActionExecutionError(f"type_xy failed: {last_exc}")

    async def hover(self, x: int, y: int, attempts: int = 2):
        aid = self._new_action_id()
        payload = {"action": "hover", "x": x, "y": y}
        self._log_start(aid, "hover", payload)
        start = time.time()
        try:
            await self._ensure_page()
            await self.page.mouse.move(x, y)
            duration = time.time() - start
            self._log_success(aid, "hover", payload, duration)
            return {"action_id": aid, "status": "success", "duration": duration}
        except Exception as e:
            duration = time.time() - start
            self._log_failure(aid, "hover", payload, str(e), attempt=0)
            raise ActionExecutionError(f"hover failed: {e}")

    async def scroll(self, delta_x: int = 0, delta_y: int = 500):
        aid = self._new_action_id()
        payload = {"action": "scroll", "delta_x": delta_x, "delta_y": delta_y}
        self._log_start(aid, "scroll", payload)
        start = time.time()
        try:
            await self._ensure_page()
            await self.page.mouse.wheel(delta_x, delta_y)
            duration = time.time() - start
            self._log_success(aid, "scroll", payload, duration)
            return {"action_id": aid, "status": "success", "duration": duration}
        except Exception as e:
            duration = time.time() - start
            self._log_failure(aid, "scroll", payload, str(e), attempt=0)
            raise ActionExecutionError(f"scroll failed: {e}")

    async def press_key(self, key: str = "Enter"):
        aid = self._new_action_id()
        payload = {"action": "press_key", "key": key}
        self._log_start(aid, "press_key", payload)
        start = time.time()
        try:
            await self._ensure_page()
            await self.page.keyboard.press(key)
            duration = time.time() - start
            self._log_success(aid, "press_key", payload, duration)
            return {"action_id": aid, "status": "success", "duration": duration}
        except Exception as e:
            duration = time.time() - start
            self._log_failure(aid, "press_key", payload, str(e), attempt=0)
            raise ActionExecutionError(f"press_key failed: {e}")

    # Generic executor for action sequences (useful for replay)
    async def execute_sequence(self, actions: list) -> list:
        """
        actions: list of dicts like:
        {"type": "navigate", "url": "..."}
        {"type": "click_xy", "x": 200, "y": 300}
        {"type": "type_selector", "selector": "#q", "text": "hello"}
        Returns list of results for each action (status/duration or exception raised).
        """
        results = []
        for a in actions:
            typ = a.get("type")
            try:
                if typ == "navigate":
                    res = await self.navigate(a["url"])
                elif typ == "click_selector":
                    res = await self.click_selector(a["selector"], attempts=a.get("attempts") or DEFAULT_RETRY_ATTEMPTS)
                elif typ == "click_xy":
                    res = await self.click_xy(a["x"], a["y"], attempts=a.get("attempts") or DEFAULT_RETRY_ATTEMPTS)
                elif typ == "type_selector":
                    res = await self.type_selector(a["selector"], a["text"], clear_first=a.get("clear_first", True), attempts=a.get("attempts") or DEFAULT_RETRY_ATTEMPTS)
                elif typ == "type_xy":
                    res = await self.type_xy(a["x"], a["y"], a["text"], attempts=a.get("attempts") or DEFAULT_RETRY_ATTEMPTS)
                elif typ == "scroll":
                    res = await self.scroll(a.get("dx") or 0, a.get("dy") or 500)
                elif typ == "press_key":
                    res = await self.press_key(a.get("key") or "Enter")
                elif typ == "hover":
                    res = await self.hover(a["x"], a["y"])
                elif typ == "wait_for_selector":
                    res = await self.wait_for_selector(a["selector"], timeout_ms=a.get("timeout_ms"))
                else:
                    raise ActionExecutionError(f"Unknown action type: {typ}")
                results.append({"type": typ, "result": res})
            except Exception as e:
                results.append({"type": typ, "error": str(e)})
                # stop on first failure (configurable later)
                break
        return results
