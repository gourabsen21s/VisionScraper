# tests/test_action_executor.py
import os
from runner.action_executor import ActionExecutor
from runner.session_manager import SessionManager

class DummyPage:
    def __init__(self):
        self._mouse = type("M", (), {"move": lambda *a, **k: None, "click": lambda *a, **k: None, "wheel": lambda *a, **k: None})()
        self.mouse = self._mouse
        self.keyboard = type("K", (), {"type": lambda *a, **k: None, "press": lambda *a, **k: None})()

    def evaluate(self, js):
        return 2
    def goto(self, url, timeout=None, wait_until=None):
        return
    def click(self, selector, timeout=None):
        return
    def wait_for_selector(self, selector, timeout=None):
        return type("E", (), {"fill": lambda t: None, "type": lambda t, delay=None: None})()
    def screenshot(self, path):
        open(path, "wb").write(b"ok")
    def close(self):
        return

class DummyContext:
    def new_page(self):
        return DummyPage()
    def close(self):
        pass

class DummyBM:
    def ensure_browser(self): pass
    def new_context(self, **kwargs): return DummyContext()

def test_type_and_click(tmp_path):
    bm = DummyBM()
    sm = SessionManager(bm, artifacts_root=str(tmp_path))
    sid = sm.create_session(video=False)
    page = sm.get_page(sid)
    # patch real page with dummy for actions
    page_obj = DummyPage()
    # monkeypatch underlying page
    sm._sessions[sid].page = page_obj
    ae = ActionExecutor(page_obj, session_id=sid)
    r1 = ae.click_xy(10, 10)
    assert r1["status"] == "success"
    r2 = ae.type_xy(10, 10, "hello")
    assert r2["status"] == "success"
    sm.close_session(sid)
