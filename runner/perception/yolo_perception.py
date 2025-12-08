import time
import cv2
import numpy as np
from typing import List
from ultralytics import YOLO
from runner.logger import log
from runner.perception.ui_element import UIElement
from runner.config import YOLO_MODEL_PATH

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    log("WARN", "tesseract_missing", "OCR not available - install tesseract for text extraction")

# Allowlist of YOLO classes for which OCR should be applied.
# Initially matched the original behavior (field, button, link) and now includes
# additional text-heavy classes observed in real tasks.
OCR_CLASSES = {"field", "button", "link", "heading", "text"}

class YOLOPerception:
    def __init__(self, model_path: str = None):
        self.model_path = model_path or YOLO_MODEL_PATH
        log("INFO", "yolo_init", "Initializing YOLO model", model_path=self.model_path)
        try:
            self.model = YOLO(self.model_path)
        except Exception as e:
            log("ERROR", "yolo_init_failed", "Failed to load YOLO model", error=str(e))
            raise

    def _extract_text_from_region(self, img, bbox: List[int]) -> str:
        """Extract text from a specific region using OCR."""
        if not TESSERACT_AVAILABLE:
            return ""

        try:
            if img is None:
                return ""

            # Extract region
            x1, y1, x2, y2 = bbox
            region = img[y1:y2, x1:x2]

            # Convert to grayscale for better OCR
            gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)

            # Apply threshold for better text extraction
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

            # Extract text
            # Try different OCR configurations for better results
            try:
                # Try standard mode first
                text = pytesseract.image_to_string(thresh, config='--psm 6').strip()
                if not text:
                    # Try single character mode
                    text = pytesseract.image_to_string(thresh, config='--psm 7').strip()
                if not text:
                    # Try word mode
                    text = pytesseract.image_to_string(thresh, config='--psm 8').strip()
            except:
                text = pytesseract.image_to_string(thresh).strip()

            return text
        except Exception as e:
            log("DEBUG", "ocr_failed", "OCR extraction failed", error=str(e))
            return ""

    def analyze(self, screenshot_path: str) -> List[UIElement]:
        """
        Run inference on the screenshot and return detected UI elements with OCR text.
        """
        start = time.time()
        log("INFO", "perception_yolo_start", "Analyzing screenshot with YOLO", screenshot_path=screenshot_path)

        try:
            # Run inference
            # conf=0.2 is a reasonable default, can be tuned
            results = self.model(screenshot_path, conf=0.2, verbose=False)

            elements = []
            img = None
            if TESSERACT_AVAILABLE:
                img = cv2.imread(screenshot_path)
                if img is None:
                    log("WARN", "ocr_image_load_failed", "Failed to load image for OCR", screenshot_path=screenshot_path)

            if results:
                result = results[0]  # We only process one image
                boxes = result.boxes
                class_names = set()

                for i, box in enumerate(boxes):
                    # xyxy coordinates
                    coords = box.xyxy[0].tolist() # [x1, y1, x2, y2]
                    x1, y1, x2, y2 = map(int, coords)
                    
                    # Confidence
                    conf = float(box.conf[0])
                    
                    # Class
                    cls_id = int(box.cls[0])
                    cls_name = result.names[cls_id]
                    class_names.add(cls_name)
                    
                    # Extract text using OCR for certain element types
                    text = ""
                    if cls_name in OCR_CLASSES and TESSERACT_AVAILABLE and img is not None:
                        text = self._extract_text_from_region(img, [x1, y1, x2, y2])
                    
                    # Create UIElement with OCR text
                    element = UIElement(
                        id=f"yolo-{i}",
                        bbox=[x1, y1, x2, y2],
                        text=text, # Now includes OCR text
                        type=cls_name,
                        metadata={"confidence": conf}
                    )
                    elements.append(element)

                if class_names:
                    log("INFO", "perception_yolo_classes", "YOLO detected classes", classes=sorted(class_names))

            duration = time.time() - start
            log("INFO", "perception_yolo_done", "YOLO perception complete", duration_ms=int(duration * 1000), count=len(elements))
            return elements

        except Exception as e:
            log("ERROR", "perception_yolo_failed", "YOLO inference failed", error=str(e))
            raise
