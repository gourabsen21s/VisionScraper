from runner.browser_manager import BrowserManager
from runner.session_manager import SessionManager

_bm = None
_sm = None

async def init_services(app):
    global _bm, _sm
    _bm = BrowserManager()
    try:
        await _bm.start()
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"CRITICAL WARNING: BrowserManager failed to start: {e}. Application will start without browser capabilities.")

    _sm = SessionManager(_bm)
    
    @app.on_event("shutdown")
    async def shutdown():
        if _bm:
            await _bm.stop()

def get_session_manager():
    return _sm

def get_browser_manager():
    return _bm
