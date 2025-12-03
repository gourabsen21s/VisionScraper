from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict

class ViewportSize(BaseModel):
    width: int = 1280
    height: int = 720

class BrowserProfile(BaseModel):
    """
    Configuration for the browser session.
    """
    model_config = ConfigDict(extra='ignore')

    headless: bool = False
    user_agent: Optional[str] = None
    viewport: ViewportSize = Field(default_factory=ViewportSize)
    
    # Security & Anti-detection
    disable_security: bool = True
    
    # Network
    proxy: Optional[Dict[str, str]] = None
    
    # Downloads
    downloads_path: Optional[str] = None
    
    # Chrome Args
    extra_args: List[str] = Field(default_factory=list)

    def get_playwright_args(self) -> List[str]:
        args = [
            '--no-sandbox',
            '--disable-blink-features=AutomationControlled',
            '--disable-infobars',
            '--disable-background-timer-throttling',
            '--disable-popup-blocking',
            '--disable-renderer-backgrounding',
        ]
        if self.disable_security:
            args.extend([
                '--disable-web-security',
                '--disable-site-isolation-trials',
                '--ignore-certificate-errors',
            ])
        args.extend(self.extra_args)
        return args
