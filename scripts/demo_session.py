# scripts/demo_session.py
import time
from runner.browser_manager import BrowserManager
from runner.session_manager import SessionManager

def main():
    bm = BrowserManager()
    bm.start()

    sm = SessionManager(bm)

    # create session with video enabled
    sid = sm.create_session(video=True)
    print("Created session:", sid)

    page = sm.get_page(sid)
    page.goto("https://example.com")
    time.sleep(1)

    shot = sm.snapshot(sid, "example.png")
    print("Screenshot saved:", shot)

    # close session and keep artifacts for inspection
    sm.close_session(sid, keep_artifacts=True)
    print("Closed session (artifacts kept) at:", sm.get_session(sid))

    bm.stop()

if __name__ == "__main__":
    main()
