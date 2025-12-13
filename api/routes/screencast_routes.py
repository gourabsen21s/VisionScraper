# api/routes/screencast_routes.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from ..deps import get_session_manager
from runner.session_manager import SessionManager
from runner.logger import log
import asyncio
import base64

router = APIRouter()

@router.websocket("/sessions/{session_id}/screencast")
async def screencast_websocket(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for CDP screencast streaming.
    Streams browser frames as base64 JPEG images.
    """
    await websocket.accept()
    log("INFO", "screencast_connect", "Screencast WebSocket connected", session_id=session_id)
    
    sm = get_session_manager()
    
    if not sm:
        await websocket.close(code=1011, reason="Session manager not initialized")
        return
    
    meta = sm.get_session(session_id)
    if not meta:
        await websocket.close(code=1008, reason="Session not found")
        return
    
    page = meta.page
    if not page:
        await websocket.close(code=1011, reason="Session page not available")
        return
    
    cdp_session = None
    screencast_started = False
    frame_queue = asyncio.Queue(maxsize=10)
    
    async def handle_screencast_frame(params):
        frame_data = params.get("data")
        session_id_param = params.get("sessionId")
        if frame_data:
            try:
                frame_queue.put_nowait({
                    "type": "frame",
                    "data": frame_data,
                    "metadata": {
                        "timestamp": params.get("metadata", {}).get("timestamp"),
                        "sessionId": session_id_param
                    }
                })
            except asyncio.QueueFull:
                pass
            
            if cdp_session:
                try:
                    await cdp_session.send("Page.screencastFrameAck", {"sessionId": session_id_param})
                except Exception:
                    pass
    
    try:
        cdp_session = await page.context.new_cdp_session(page)
        
        cdp_session.on("Page.screencastFrame", handle_screencast_frame)
        
        await cdp_session.send("Page.startScreencast", {
            "format": "jpeg",
            "quality": 60,
            "maxWidth": 1280,
            "maxHeight": 720,
            "everyNthFrame": 1
        })
        screencast_started = True
        log("INFO", "screencast_started", "CDP screencast started", session_id=session_id)
        
        await websocket.send_json({"type": "started", "session_id": session_id})
        
        while True:
            try:
                send_task = asyncio.create_task(frame_queue.get())
                recv_task = asyncio.create_task(websocket.receive_text())
                
                done, pending = await asyncio.wait(
                    [send_task, recv_task],
                    return_when=asyncio.FIRST_COMPLETED
                )
                
                for task in pending:
                    task.cancel()
                
                for task in done:
                    if task == send_task:
                        frame = task.result()
                        await websocket.send_json(frame)
                    elif task == recv_task:
                        msg = task.result()
                        if msg == "ping":
                            await websocket.send_json({"type": "pong"})
                        elif msg == "stop":
                            break
                            
            except asyncio.CancelledError:
                break
                
    except WebSocketDisconnect:
        log("INFO", "screencast_disconnect", "Screencast WebSocket disconnected", session_id=session_id)
    except Exception as e:
        log("ERROR", "screencast_error", "Screencast error", session_id=session_id, error=str(e))
        try:
            await websocket.close(code=1011, reason=str(e))
        except:
            pass
    finally:
        if screencast_started and cdp_session:
            try:
                await cdp_session.send("Page.stopScreencast")
                log("INFO", "screencast_stopped", "CDP screencast stopped", session_id=session_id)
            except Exception:
                pass
        if cdp_session:
            try:
                await cdp_session.detach()
            except Exception:
                pass

