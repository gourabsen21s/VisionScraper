from runner.browser_manager import BrowserManager
from runner.session_manager import SessionManager

_bm = None
_sm = None

async def init_services(app):
    global _bm, _sm
    _bm = BrowserManager()
    await _bm.start()
    _sm = SessionManager(_bm)
    
    @app.on_event("shutdown")
    async def shutdown():
        if _bm:
            await _bm.stop()

def get_session_manager():
    return _sm

def get_browser_manager():
    return _bm
