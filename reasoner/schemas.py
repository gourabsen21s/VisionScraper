# reasoner/schemas.py
from pydantic import BaseModel, Field, model_validator
from typing import Literal, Optional, Dict, Any

class Target(BaseModel):
    by: Literal["id", "selector", "coords"]
    value: str  # coords are "x,y"

class ActionSchema(BaseModel):
    action: Literal["click", "type", "navigate", "scroll", "hover", "press_key", "noop"]
    target: Optional[Target] = None
    value: Optional[str] = None
    confidence: float = Field(..., ge=0.0, le=1.0)
    reason: str

    @model_validator(mode='after')
    def validate_action_requirements(self):
        act = self.action
        if act in ("click", "type", "hover", "press_key") and self.target is None:
            raise ValueError(f"action '{act}' requires a target")
        if act == "navigate" and (self.value is None or self.value == ""):
            raise ValueError("navigate action requires 'value' (url)")
        return self
