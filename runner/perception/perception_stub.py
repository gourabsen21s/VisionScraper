# perception/perception_stub.py
import time
from typing import List
from .ui_element import UIElement
from runner.logger import log
import os

class PerceptionStub:

    def __init__(self):
        pass

    def analyze(self, screenshot_path: str) -> List[UIElement]:
        """
        Simulates perception by returning mock UI elements
        depending on known patterns (e.g., google.com).
        """
        start = time.time()
        log("INFO", "perception_stub_start", "Analyzing screenshot", screenshot_path=screenshot_path)

        # Simple rule-based detection based on file name or URL patterns later
        if "google" in screenshot_path.lower():
            elements = self._google_ui()
        elif "duck" in screenshot_path.lower():
            elements = self._duckduckgo_ui()
        else:
            elements = self._generic_ui()

        duration = time.time() - start
        log("INFO", "perception_stub_done", "Stub perception complete", duration_ms=int(duration * 1000))
        return elements

    def _google_ui(self) -> List[UIElement]:
        return [
            UIElement(id="search-box", bbox=[400, 250, 900, 300], text="", type="input"),
            UIElement(id="search-button", bbox=[920, 250, 1000, 300], text="Search", type="button"),
        ]

    def _duckduckgo_ui(self) -> List[UIElement]:
        return [
            UIElement(id="search-box", bbox=[420, 260, 880, 310], text="", type="input"),
        ]

    def _generic_ui(self) -> List[UIElement]:
        # Fallback detection
        return [
            UIElement(id="center-button", bbox=[500, 400, 780, 450], text="Click", type="button"),
        ]
