from dataclasses import dataclass, field
from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_serializer

from src.dom.views import SerializedDOMState, DOMInteractedElement

# Known placeholder image data for about:blank pages - a 4x4 white PNG
PLACEHOLDER_4PX_SCREENSHOT = (
    'iVBORw0KGgoAAAANSUhEUgAAAAQAAAAECAIAAAAmkwkpAAAAFElEQVR4nGP8//8/AwwwMSAB3BwAlm4DBfIlvvkAAAAASUVORK5CYII='
)

class TabInfo(BaseModel):
    """Represents information about a browser tab"""
    model_config = ConfigDict(extra='ignore')

    url: str
    title: str
    page_id: int # Using int ID for simplicity in Playwright mapping

@dataclass
class PageInfo:
    """Comprehensive page size and scroll information"""
    viewport_width: int
    viewport_height: int
    page_width: int
    page_height: int
    scroll_x: int
    scroll_y: int
    pixels_above: int
    pixels_below: int
    pixels_left: int
    pixels_right: int

@dataclass
class BrowserStateSummary:
    """The summary of the browser's current state designed for an LLM to process"""
    dom_state: SerializedDOMState
    url: str
    title: str
    tabs: List[TabInfo]
    screenshot: Optional[str] = field(default=None, repr=False)
    page_info: Optional[PageInfo] = None
    
    # Legacy/Convenience fields
    pixels_above: int = 0
    pixels_below: int = 0
    browser_errors: List[str] = field(default_factory=list)

@dataclass
class BrowserStateHistory:
    """The summary of the browser's state at a past point in time"""
    url: str
    title: str
    tabs: List[TabInfo]
    interacted_element: List[Optional[DOMInteractedElement]]
    screenshot: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "title": self.title,
            "tabs": [tab.model_dump() for tab in self.tabs],
            "interacted_element": [el.to_dict() if el else None for el in self.interacted_element],
            "screenshot": "..." if self.screenshot else None
        }

@dataclass
class BrowserState:
    """Legacy wrapper for backward compatibility if needed"""
    url: str
    title: str
    tabs: List[TabInfo]
    screenshot: Optional[str] = None
    dom_state: Optional[SerializedDOMState] = None
    pixels_above: int = 0
    pixels_below: int = 0
