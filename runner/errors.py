# browser_manager/errors.py
class BrowserManagerError(Exception):
    pass

class BrowserStartError(BrowserManagerError):
    pass

class BrowserHealthError(BrowserManagerError):
    pass

class ActionExecutionError(BrowserManagerError):
    pass
