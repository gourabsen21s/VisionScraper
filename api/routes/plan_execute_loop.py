# api/routes/plan_execute_loop.py
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from ..deps import get_session_manager
from runner.session_manager import SessionManager
from runner.action_executor import ActionExecutor
from runner.perception.yolo_perception import YOLOPerception
from reasoner.reasoner import Reasoner
from reasoner.schemas import ActionSchema
from runner.logger import log
import os
import time
import asyncio
import traceback

router = APIRouter()
_perception = YOLOPerception()
_reasoner = Reasoner()

# Config defaults (override with env vars)
DEFAULT_MAX_STEPS = int(os.getenv("PLAN_LOOP_MAX_STEPS", "25"))  # Increased from 8 for complex tasks
CONFIDENCE_THRESHOLD = float(os.getenv("REASONER_CONFIDENCE_THRESHOLD", "0.35"))  # Slightly lowered
POST_ACTION_WAIT_SEC = float(os.getenv("POST_ACTION_WAIT_SEC", "2.0"))  # Wait after page-changing actions

class PlanLoopRequest(BaseModel):
    goal: str
    max_steps: Optional[int] = DEFAULT_MAX_STEPS
    stop_on_low_confidence: Optional[bool] = True
    force: Optional[bool] = False  # if true, always execute regardless of confidence
    # optional user-provided callback id, request id etc. (for audit)
    request_id: Optional[str] = None

class StepResult(BaseModel):
    step: int
    action: Dict[str, Any]
    executed: bool
    execution_result: Optional[Dict[str, Any]] = None
    reasoner_raw: Optional[Dict[str, Any]] = None

class PlanLoopResponse(BaseModel):
    session_id: str
    goal: str
    completed: bool
    steps: List[StepResult]
    reason: Optional[str] = None

def _append_executed_action_to_session(meta, action_dict):
    """
    Store executed action summary into session metadata to prevent repeats.
    """
    hist = meta.metadata.get("executed_actions", [])
    hist.append({"ts": time.time(), "action": action_dict})
    meta.metadata["executed_actions"] = hist

def _is_action_duplicate(meta, action_dict) -> bool:
    """
    Very simple duplicate detection: check last N actions for same action dict.
    """
    hist = meta.metadata.get("executed_actions", [])
    if not hist:
        return False
    # compare to last 5 actions
    for past in hist[-5:]:
        if past.get("action") == action_dict:
            return True
    return False

def _target_to_executor_call(target: Optional[Dict[str,str]], elements: list, executor: ActionExecutor):
    """
    Same mapping helper used in one-step endpoint. Raises HTTPException for invalid mapping.
    """
    if target is None:
        raise HTTPException(status_code=400, detail="Action target required for this action")
    by = target.get("by")
    val = target.get("value")

    if by == "id":
        for el in elements:
            if el.get("id") == val:
                bbox = el.get("bbox")
                x1, y1, x2, y2 = bbox
                cx = int((x1 + x2) / 2)
                cy = int((y1 + y2) / 2)
                return ("click_xy", {"x": cx, "y": cy})
        raise HTTPException(status_code=400, detail=f"Element with id '{val}' not found")

    elif by == "coords":
        try:
            x_str, y_str = val.split(",")
            x = int(float(x_str.strip()))
            y = int(float(y_str.strip()))
            return ("click_xy", {"x": x, "y": y})
        except Exception:
            raise HTTPException(status_code=400, detail=f"Invalid coords format: {val}")

    elif by == "selector":
        return ("click_selector", {"selector": val})
    else:
        raise HTTPException(status_code=400, detail=f"Unknown target.by: {by}")

@router.post("/sessions/{session_id}/plan_execute_loop", response_model=PlanLoopResponse)
async def plan_execute_loop(session_id: str, body: PlanLoopRequest, sm: SessionManager = Depends(get_session_manager)):
    """
    Multi-step plan & execute loop:
    - capture screenshot
    - perception
    - reasoner -> action
    - safety check
    - execute action
    - repeat until:
        * reasoner returns 'noop', OR
        * max_steps reached, OR
        * low-confidence and stop_on_low_confidence True

    Returns the list of steps attempted and whether loop completed (reasoner returned noop).
    """
    log("INFO", "plan_loop_start", "Plan loop started", session_id=session_id, goal=body.goal, max_steps=body.max_steps)
    meta = sm.get_session(session_id)
    if not meta:
        raise HTTPException(status_code=404, detail="session not found")

    steps: List[StepResult] = []
    completed = False
    try:
        for step in range(1, (body.max_steps or DEFAULT_MAX_STEPS) + 1):
            # 1) snapshot
            screenshot_name = f"loop_{int(time.time())}.png"
            screenshot_path = await sm.snapshot(session_id, screenshot_name)

            # 2) perception
            elements = _perception.analyze(screenshot_path)
            elements_list = [e.dict() for e in elements]

            # 3) Get page context for better reasoning
            page = meta.page
            current_url = page.url if page else ""
            try:
                page_title = await page.title() if page else ""
            except:
                page_title = ""
            
            prev_element_count = meta.metadata.get("prev_element_count", 0)
            element_count_change = len(elements_list) - prev_element_count
            meta.metadata["prev_element_count"] = len(elements_list)
            
            page_context = {
                "current_url": current_url,
                "page_title": page_title,
                "element_count": len(elements_list),
                "prev_element_count": prev_element_count,
                "element_count_change": element_count_change,
                "step_number": step
            }
            log("DEBUG", "plan_loop_page_context", "Page context", session_id=session_id, url=current_url[:80], element_change=element_count_change)
            
            # 4) reasoning with page context
            try:
                action_schema: ActionSchema = _reasoner.plan_one(
                    body.goal, 
                    elements_list, 
                    last_actions=meta.metadata.get("executed_actions", []),
                    page_context=page_context
                )
            except Exception as re:
                # if reasoner fails outright, stop loop
                log("ERROR", "plan_loop_reasoner_error", "Reasoner failed mid-loop", session_id=session_id, step=step, error=str(re))
                return PlanLoopResponse(session_id=session_id, goal=body.goal, completed=False, steps=steps, reason=f"Reasoner error: {re}")

            action_dict = action_schema.dict()
            log("DEBUG", "plan_loop_reasoned", "Step reasoned action", step=step, action=action_dict)

            # 4) termination condition: noop => done (but prevent premature noop)
            if action_schema.action == "noop":
                executed_count = len([s for s in steps if s.executed])
                if executed_count < 3:
                    # Premature noop - skip and continue
                    log("WARN", "plan_loop_premature_noop", "Noop returned too early, continuing", 
                        session_id=session_id, step=step, executed_count=executed_count, reason=action_schema.reason)
                    await asyncio.sleep(2)  # Wait for page to potentially change
                    continue
                
                log("INFO", "plan_loop_noop", "Reasoner returned noop — stopping loop", session_id=session_id, step=step, reason=action_schema.reason)
                steps.append(StepResult(step=step, action=action_dict, executed=False, execution_result=None, reasoner_raw=action_dict))
                completed = True
                break

            # 5) confidence check
            if (not body.force) and (body.stop_on_low_confidence and action_schema.confidence < CONFIDENCE_THRESHOLD):
                log("WARN", "plan_loop_low_confidence", "Low confidence action — stopping loop", session_id=session_id, step=step, confidence=action_schema.confidence)
                steps.append(StepResult(step=step, action=action_dict, executed=False, execution_result=None, reasoner_raw=action_dict))
                completed = False
                break

            # 6) idempotency check
            if _is_action_duplicate(meta, action_dict):
                log("WARN", "plan_loop_duplicate", "Duplicate action detected — skipping execution", session_id=session_id, step=step, action=action_dict)
                steps.append(StepResult(step=step, action=action_dict, executed=False, execution_result={"skipped":"duplicate"}, reasoner_raw=action_dict))
                # mark as executed to avoid loops and continue
                _append_executed_action_to_session(meta, action_dict)
                continue

            # 7) execute the action
            page = meta.page
            if not page:
                raise HTTPException(status_code=500, detail="session page missing")
            executor = ActionExecutor(page, session_id=session_id)

            exec_result = None
            try:
                a = action_schema.action
                target = action_schema.target.dict() if action_schema.target else None

                if a == "click":
                    method, kwargs = _target_to_executor_call(target, elements_list, executor)
                    exec_result = await getattr(executor, method)(**kwargs)
                elif a == "type":
                    method, kwargs = _target_to_executor_call(target, elements_list, executor)
                    text_val = action_schema.value or ""
                    if method == "click_selector":
                        exec_result = await executor.type_selector(kwargs["selector"], text_val)
                    else:
                        exec_result = await executor.type_xy(kwargs["x"], kwargs["y"], text_val)
                elif a == "navigate":
                    exec_result = await executor.navigate(action_schema.value)
                elif a == "scroll":
                    if target and target.get("by") == "coords":
                        x_str, y_str = target.get("value").split(",")
                        exec_result = await executor.scroll(0, int(float(y_str.strip())))
                    else:
                        exec_result = await executor.scroll(0, 500)
                elif a == "hover":
                    method, kwargs = _target_to_executor_call(target, elements_list, executor)
                    if method == "click_xy":
                        exec_result = await executor.hover(kwargs["x"], kwargs["y"])
                    else:
                        raise HTTPException(status_code=400, detail="Unsupported hover mapping")
                elif a == "press_key":
                    key = action_schema.value or "Enter"
                    exec_result = await executor.press_key(key)
                else:
                    raise HTTPException(status_code=400, detail=f"Unsupported action type: {a}")

                # 8) record executed action to prevent repeats
                _append_executed_action_to_session(meta, action_dict)

                steps.append(StepResult(step=step, action=action_dict, executed=True, execution_result=exec_result, reasoner_raw=action_dict))
                log("INFO", "plan_loop_step_success", "Step executed", session_id=session_id, step=step, exec_result=exec_result)

                # 9) Wait after page-changing actions to allow page to stabilize
                if a in ("click", "navigate", "press_key", "type"):
                    log("DEBUG", "plan_loop_wait", f"Waiting {POST_ACTION_WAIT_SEC}s for page to stabilize", session_id=session_id)
                    await asyncio.sleep(POST_ACTION_WAIT_SEC)
                    # Try to wait for network idle (non-blocking)
                    try:
                        await page.wait_for_load_state("networkidle", timeout=3000)
                    except Exception:
                        pass  # Continue even if timeout

            except Exception as exec_e:
                log("ERROR", "plan_loop_step_failed", "Execution error", session_id=session_id, step=step, error=str(exec_e), tb=traceback.format_exc())
                steps.append(StepResult(step=step, action=action_dict, executed=False, execution_result={"error": str(exec_e)}, reasoner_raw=action_dict))
                # stop loop on execution failure
                completed = False
                break

        # loop end
        if not completed and len(steps) > 0 and steps[-1].action.get("action") == "noop":
            completed = True

        overall_reason = None
        if len(steps) == 0:
            overall_reason = "No steps executed"
        elif not completed:
            overall_reason = "Stopped (max steps / low confidence / execution error)"

        return PlanLoopResponse(session_id=session_id, goal=body.goal, completed=completed, steps=steps, reason=overall_reason)

    except HTTPException:
        raise
    except Exception as e:
        log("ERROR", "plan_loop_unexpected", "Unexpected error in plan loop", session_id=session_id, error=str(e), tb=traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
