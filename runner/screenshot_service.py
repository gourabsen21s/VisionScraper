import base64
import io
from typing import Optional, Tuple
from PIL import Image
from playwright.async_api import Page
from runner.logger import log

class ScreenshotService:
    """
    Service for capturing and optimizing screenshots for Vision LLMs.
    """
    
    def __init__(self, max_width: int = 1920, max_height: int = 1080, quality: int = 80):
        self.max_width = max_width
        self.max_height = max_height
        self.quality = quality

    async def capture_and_optimize(self, page: Page, full_page: bool = False) -> str:
        """
        Captures a screenshot, optimizes it (resize & compress), and returns base64 string.
        """
        try:
            # Capture raw PNG screenshot
            png_bytes = await page.screenshot(full_page=full_page, type='png')
            
            # Open with Pillow
            img = Image.open(io.BytesIO(png_bytes))
            
            # Convert to RGB (in case of RGBA) for JPEG compatibility
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            
            # Resize if needed
            img = self._resize_image(img)
            
            # Compress to JPEG and encode to base64
            base64_str = self._image_to_base64(img)
            
            log("DEBUG", "screenshot_captured", f"Captured and optimized screenshot: {img.size[0]}x{img.size[1]}")
            return base64_str
            
        except Exception as e:
            log("ERROR", "screenshot_failed", "Failed to capture screenshot", error=str(e))
            raise e

    async def capture_to_file(self, page: Page, path: str, full_page: bool = False) -> str:
        """
        Captures a screenshot, optimizes it, and saves to file (JPEG).
        Returns the path.
        """
        try:
            # Capture raw PNG screenshot
            png_bytes = await page.screenshot(full_page=full_page, type='png')
            
            # Open with Pillow
            img = Image.open(io.BytesIO(png_bytes))
            
            # Convert to RGB (in case of RGBA) for JPEG compatibility
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            
            # Resize if needed
            img = self._resize_image(img)
            
            # Save as JPEG
            img.save(path, format="JPEG", quality=self.quality, optimize=True)
            
            log("DEBUG", "screenshot_saved", f"Saved optimized screenshot to {path} ({img.size[0]}x{img.size[1]})")
            return path
            
        except Exception as e:
            log("ERROR", "screenshot_save_failed", "Failed to save screenshot", path=path, error=str(e))
            raise e

    def _resize_image(self, img: Image.Image) -> Image.Image:
        """
        Resizes image to fit within max dimensions while maintaining aspect ratio.
        """
        width, height = img.size
        
        # Check if resize is needed
        if width <= self.max_width and height <= self.max_height:
            return img
            
        # Calculate new dimensions
        aspect_ratio = width / height
        
        if width > self.max_width:
            width = self.max_width
            height = int(width / aspect_ratio)
            
        if height > self.max_height:
            height = self.max_height
            width = int(height * aspect_ratio)
            
        return img.resize((width, height), Image.Resampling.LANCZOS)

    def _image_to_base64(self, img: Image.Image) -> str:
        """
        Converts Pillow Image to base64 encoded JPEG string.
        """
        buffered = io.BytesIO()
        img.save(buffered, format="JPEG", quality=self.quality, optimize=True)
        return base64.b64encode(buffered.getvalue()).decode('utf-8')
