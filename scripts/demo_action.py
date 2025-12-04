# scripts/demo_actions.py
import time
from runner.browser_manager import BrowserManager
from runner.session_manager import SessionManager
from runner.action_executor import ActionExecutor

def main():
    bm = BrowserManager()
    bm.start()

    sm = SessionManager(bm)
    sid = sm.create_session(video=False)
    page = sm.get_page(sid)

    ae = ActionExecutor(page, session_id=sid)
    ae.navigate("https://example.com")
    time.sleep(1)
    ae.snapshot = lambda *a, **k: None  # session snapshot through SessionManager if needed
    # click roughly center (example.com simple layout)
    ae.click_xy(300, 300)
    # type example (note: example.com has no input; for real tests use google.com)
    # ae.type_xy(100, 200, "hello world")
    res = ae.execute_sequence([
        {"type": "navigate", "url": "https://google.com"},
        {"type": "click_selector", "selector": "input[name=q]"},
        {"type": "type_selector", "selector": "input[name=q]", "text": "playwright python"},
        {"type": "press_key", "key": "Enter"}
    ])
    print("Sequence results:", res)

    sm.close_session(sid, keep_artifacts=False)
    bm.stop()

if __name__ == "__main__":
    main()
