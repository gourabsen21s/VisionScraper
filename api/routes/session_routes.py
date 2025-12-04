# api/routes/session_routes.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from ..deps import get_session_manager, get_browser_manager
from runner.errors import BrowserHealthError, ActionExecutionError
from runner.action_executor import ActionExecutor

router = APIRouter()

class CreateSessionRequest(BaseModel):
    video: Optional[bool] = False
    keep_artifacts: Optional[bool] = False
    context_kwargs: Optional[Dict[str, Any]] = None

class ActionItem(BaseModel):
    type: str
    # flexible, used by different action types
    x: Optional[int] = None
    y: Optional[int] = None
    selector: Optional[str] = None
    text: Optional[str] = None
    attempts: Optional[int] = None
    url: Optional[str] = None
    dx: Optional[int] = None
    dy: Optional[int] = None
    key: Optional[str] = None

class ExecuteActionsRequest(BaseModel):
    actions: List[ActionItem]
    stop_on_failure: Optional[bool] = True

@router.post("/sessions", status_code=201)
async def create_session(req: CreateSessionRequest, sm = Depends(get_session_manager)):
    try:
        sid = await sm.create_session(video=req.video, context_kwargs=req.context_kwargs, keep_artifacts=req.keep_artifacts)
        return {"session_id": sid}
    except BrowserHealthError as e:
        raise HTTPException(status_code=503, detail=f"Browser not available: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sessions/{session_id}/actions")
async def execute_actions(session_id: str, req: ExecuteActionsRequest, sm = Depends(get_session_manager)):
    meta = sm.get_session(session_id)
    if not meta:
        raise HTTPException(status_code=404, detail="session not found")
    page = meta.page
    if not page:
        raise HTTPException(status_code=500, detail="session page missing")
    ae = ActionExecutor(page, session_id=session_id)

    # convert ActionItem -> internal dict
    actions_payload = []
    for it in req.actions:
        d = it.dict()
        # normalize action types for executor
        if not d.get("type"):
            raise HTTPException(status_code=400, detail="action must contain 'type'")
        actions_payload.append(d)
    
    print(f"DEBUG: execute_actions payload: {actions_payload}", flush=True)

    try:
        results = await ae.execute_sequence(actions_payload)
        return {"session_id": session_id, "results": results}
    except ActionExecutionError as ae_err:
        raise HTTPException(status_code=500, detail=str(ae_err))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sessions/{session_id}")
def get_session(session_id: str, sm = Depends(get_session_manager)):
    meta = sm.get_session(session_id)
    if not meta:
        raise HTTPException(status_code=404, detail="session not found")
    return {
        "session_id": meta.session_id,
        "created_at": meta.created_at,
        "status": meta.status,
        "session_dir": meta.session_dir,
        "video_enabled": meta.video_enabled,
        "last_update": meta.last_update
    }

@router.post("/sessions/{session_id}/snapshot")
async def session_snapshot(session_id: str, filename: Optional[str] = "screenshot.png", sm = Depends(get_session_manager)):
    meta = sm.get_session(session_id)
    if not meta:
        raise HTTPException(status_code=404, detail="session not found")
    try:
        path = await sm.snapshot(session_id, filename)
        return {"path": path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/sessions/{session_id}")
async def close_session(session_id: str, keep_artifacts: Optional[bool] = False, sm = Depends(get_session_manager)):
    ok = await sm.close_session(session_id, keep_artifacts=keep_artifacts)
    if not ok:
        raise HTTPException(status_code=404, detail="session not found or already closed")
    return {"closed": True, "session_id": session_id}
