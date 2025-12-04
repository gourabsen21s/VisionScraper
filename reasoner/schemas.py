# reasoner/schemas.py
from pydantic import BaseModel, Field, validator
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

    @validator("target", always=True)
    def validate_target_for_action(cls, v, values):
        act = values.get("action")
        if act in ("click", "type", "hover", "press_key") and v is None:
            raise ValueError(f"action '{act}' requires a target")
        if act == "navigate" and (values.get("value") is None or values.get("value") == ""):
            raise ValueError("navigate action requires 'value' (url)")
        return v
