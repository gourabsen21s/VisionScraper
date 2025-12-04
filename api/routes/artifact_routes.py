# api/routes/artifact_routes.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from ..deps import get_session_manager
import os

router = APIRouter()

@router.get("/sessions/{session_id}/artifacts/{filename}")
def get_artifact(session_id: str, filename: str, sm = Depends(get_session_manager)):
    meta = sm.get_session(session_id)
    if not meta:
        raise HTTPException(status_code=404, detail="session not found")
    path = os.path.join(meta.session_dir, filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="artifact not found")
    return FileResponse(path, filename=filename)
