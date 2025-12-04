# perception/ui_element.py
from pydantic import BaseModel
from typing import List

class UIElement(BaseModel):
    id: str
    bbox: List[int]  # [x1, y1, x2, y2]
    text: str
    type: str   # "button", "input", "link", "image", etc.
