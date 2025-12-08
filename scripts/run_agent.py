import asyncio
import os
import sys
# Add project root to path
sys.path.append(os.getcwd())

from dotenv import load_dotenv
load_dotenv()

from runner.browser_manager import BrowserManager
from runner.session_manager import SessionManager
from runner.perception.yolo_perception import YOLOPerception
from reasoner.reasoner import Reasoner
from reasoner.schemas import ActionSchema
from runner.action_executor import ActionExecutor
from runner.logger import log

# Re-implementing the loop logic locally to avoid API overhead for CLI usage
async def run_agent(goal: str, url: str = None):
    print(f"Starting agent with goal: {goal}")
    
    # Init services
    bm = BrowserManager()
    await bm.start()
    sm = SessionManager(bm)
    perception = YOLOPerception() # Uses config default or env var
    reasoner = Reasoner()
    
    try:
        # Create session
        session_id = await sm.create_session(video=True)
        print(f"Session created: {session_id}")
        
        meta = sm.get_session(session_id)
        page = meta.page
        executor = ActionExecutor(page, session_id=session_id)
        
        # Initial navigation if provided
        if url:
            print(f"Navigating to {url}...")
            await executor.navigate(url, timeout_ms=30000)
        
        # Loop
        max_steps = 25  # Increased from 10 for complex multi-step tasks
        history = []
        prev_element_count = 0
        
        for step in range(1, max_steps + 1):
            print(f"\n--- Step {step} ---")
            
            # 1. Snapshot
            screenshot_path = await sm.snapshot(session_id, f"step_{step}.png")
            
            # 2. Perception
            elements = perception.analyze(screenshot_path)
            elements_list = [e.dict() for e in elements]
            current_element_count = len(elements)
            print(f"Perception: Found {current_element_count} elements")
            
            # 3. Get page context for better reasoning
            current_url = page.url
            page_title = await page.title()
            element_count_change = current_element_count - prev_element_count
            
            page_context = {
                "current_url": current_url,
                "page_title": page_title,
                "element_count": current_element_count,
                "prev_element_count": prev_element_count,
                "element_count_change": element_count_change,
                "step_number": step
            }
            print(f"Page: {current_url[:80]}... | Elements: {prev_element_count} → {current_element_count} ({element_count_change:+d})")
            
            # Update for next iteration
            prev_element_count = current_element_count
            
            # 4. Reasoner with page context
            print("Reasoning...")
            action_schema = reasoner.plan_one(goal, elements_list, last_actions=history, page_context=page_context)
            print(f"Action: {action_schema.action} {action_schema.target} {action_schema.value or ''}")
            
            if action_schema.action == "noop":
                high_confidence = action_schema.confidence >= 0.9
                
                # For complex multi-step tasks, require more actions before trusting noop
                if len(history) < 2:
                    print(f"Warning: Noop returned too early (only {len(history)} actions). Continuing...")
                    await asyncio.sleep(2)
                    continue
                elif high_confidence and len(history) >= 3:
                    print(f"Goal achieved! (confidence: {action_schema.confidence}, actions: {len(history)})")
                    break
                else:
                    print("Goal achieved or no action possible.")
                    break
                
            # 4. Execute
            # (Simplified execution logic matching plan_execute.py)
            # ... (I'll implement the mapping logic here briefly or import if possible, 
            # but for a standalone script it's safer to copy the critical bits or refactor. 
            # I'll copy the mapping logic for now to keep it self-contained)
            
            # ... execution logic ...
            # For brevity in this thought process, I will assume the user wants to see it run.
            # I will implement the basic execution mapping.
            
            target = action_schema.target
            val = action_schema.value
            
            if action_schema.action == "navigate":
                await executor.navigate(val)
            elif action_schema.action == "click":
                click_result = None
                if target.by == "coords":
                    x, y = map(int, target.value.split(","))
                    click_result = await executor.click_xy(x, y)
                elif target.by == "id":
                    # find element
                    el = next((e for e in elements_list if e["id"] == target.value), None)
                    if el:
                        x1, y1, x2, y2 = el["bbox"]
                        click_result = await executor.click_xy((x1+x2)//2, (y1+y2)//2)
                elif target.by == "selector":
                    await executor.click_selector(target.value)
                
                # Sync page reference if executor switched to new tab
                if click_result and click_result.get("new_tab"):
                    page = executor.page
                    print(f"Switched to new tab: {page.url[:60]}...")
            elif action_schema.action == "type":
                if target.by == "selector":
                    await executor.type_selector(target.value, val)
                elif target.by == "id":
                     el = next((e for e in elements_list if e["id"] == target.value), None)
                     if el:
                        x1, y1, x2, y2 = el["bbox"]
                        await executor.type_xy((x1+x2)//2, (y1+y2)//2, val)
            elif action_schema.action == "scroll":
                await executor.scroll(0, 500)
            elif action_schema.action == "press_key":
                key = val or "Enter"
                await executor.press_key(key)
            elif action_schema.action == "hover":
                if target and target.by == "id":
                    el = next((e for e in elements_list if e["id"] == target.value), None)
                    if el:
                        x1, y1, x2, y2 = el["bbox"]
                        await executor.hover((x1+x2)//2, (y1+y2)//2)
            
            history.append({"action": action_schema.dict()})
            
            # Wait for page to stabilize after page-changing actions
            if action_schema.action in ("click", "navigate", "press_key", "type"):
                print("Waiting for page to stabilize...")
                await asyncio.sleep(2.0)  # Allow time for page transitions
                try:
                    await page.wait_for_load_state("networkidle", timeout=3000)
                except:
                    pass  # Continue even if timeout
            else:
                await asyncio.sleep(0.5)  # Brief pause for other actions
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("Stopping BrowserManager...")
        try:
            if 'sm' in locals():
                await sm.close_session(session_id, keep_artifacts=True)
            if 'bm' in locals():
                await bm.stop()
        except RuntimeError:
            # Ignore event loop closed errors during cleanup
            pass
        except Exception as e:
            print(f"Error during cleanup: {e}")
        print("Session closed.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("goal", help="Goal for the agent")
    parser.add_argument("--url", help="Starting URL")
    args = parser.parse_args()
    
    try:
        asyncio.run(run_agent(args.goal, args.url))
    except RuntimeError as e:
        if str(e) == "Event loop is closed":
            pass
        else:
            raise
