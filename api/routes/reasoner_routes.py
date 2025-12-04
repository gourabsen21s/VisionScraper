# api/routes/reasoner_routes.py (new)
from fastapi import APIRouter, Depends, HTTPException
from ..deps import get_session_manager
from reasoner.reasoner import Reasoner
from pydantic import BaseModel
from typing import Optional

router = APIRouter()
r = Reasoner()

class PlanRequest(BaseModel):
    goal: str
    last_actions: Optional[list] = None

@router.post("/sessions/{session_id}/plan")
def plan(session_id: str, body: PlanRequest, sm = Depends(get_session_manager)):
    meta = sm.get_session(session_id)
    if not meta:
        raise HTTPException(404, "session not found")
    # take a fresh screenshot for context
    sm.snapshot(session_id, "latest.png")
    # For now we pass perception_stub elements; in future call actual perception
    # Simple integration: call perception endpoint or import perception module
    from perception.perception_stub import PerceptionStub
    stub = PerceptionStub()
    elements = stub.analyze(meta.session_dir + "/latest.png")
    elements_list = [e.dict() for e in elements]
    try:
        action = r.plan_one(body.goal, elements_list, last_actions=body.last_actions or [])
        return {"action": action.dict()}
    except Exception as e:
        raise HTTPException(500, str(e))
