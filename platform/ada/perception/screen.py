"""
Screen Reader - Screenshot and OCR capabilities
"""

import base64
import io
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

# Try to import screenshot libraries
try:
    import gi
    gi.require_version('Gtk', '4.0')
    from gi.repository import Gdk, GdkPixbuf
    GTK_AVAILABLE = True
except ImportError:
    GTK_AVAILABLE = False
    logger.warning("GTK not available for screenshots")

# Try to import OCR
try:
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    logger.warning("pytesseract not available for OCR")

# Try to import PIL
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


@dataclass
class ScreenRegion:
    """A region of the screen"""
    x: int
    y: int
    width: int
    height: int

    def to_dict(self) -> Dict[str, int]:
        return {"x": self.x, "y": self.y, "width": self.width, "height": self.height}


@dataclass
class OCRResult:
    """Result of OCR processing"""
    text: str
    confidence: float
    bbox: ScreenRegion
    language: str = "unknown"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "confidence": self.confidence,
            "bbox": self.bbox.to_dict(),
            "language": self.language,
        }


class ScreenReader:
    """
    Screen capture and OCR capabilities.

    Provides screenshot and text extraction functionality
    for visual UI understanding.
    """

    def __init__(self):
        self._display = None
        self._initialized = False

    @property
    def is_available(self) -> bool:
        """Check if screen capture is available"""
        return GTK_AVAILABLE

    async def initialize(self) -> bool:
        """Initialize screen capture"""
        if not GTK_AVAILABLE:
            logger.error("GTK not available")
            return False

        try:
            self._display = Gdk.Display.get_default()
            if self._display:
                self._initialized = True
                logger.info("Screen capture initialized")
                return True
        except Exception as e:
            logger.error(f"Failed to initialize screen capture: {e}")

        return False

    async def capture_screen(self, monitor_index: int = 0) -> Optional[bytes]:
        """
        Capture screenshot of a monitor.

        Args:
            monitor_index: Monitor to capture (0 = primary)

        Returns:
            PNG image bytes or None on failure
        """
        if not self._initialized or not self._display:
            return None

        try:
            # Get monitor
            monitors = self._display.get_monitors()
            if monitor_index >= monitors.get_n_items():
                monitor_index = 0

            monitor = monitors.get_item(monitor_index)
            if not monitor:
                return None

            # Get geometry
            geometry = monitor.get_geometry()

            # Take screenshot
            # Note: In GTK4, direct screenshots require portal integration
            # This is a simplified version that may need adjustment
            root = self._display.get_default_screen().get_root_window()
            if root:
                pixbuf = Gdk.pixbuf_get_from_window(
                    root,
                    geometry.x,
                    geometry.y,
                    geometry.width,
                    geometry.height
                )

                if pixbuf:
                    # Convert to PNG bytes
                    buffer = io.BytesIO()
                    pixbuf.save_to_buffer(buffer, "png")
                    return buffer.getvalue()

        except Exception as e:
            logger.error(f"Screenshot failed: {e}")

        return None

    async def capture_region(self, region: ScreenRegion) -> Optional[bytes]:
        """
        Capture a specific region of the screen.

        Args:
            region: Screen region to capture

        Returns:
            PNG image bytes or None on failure
        """
        if not self._initialized or not self._display:
            return None

        try:
            root = self._display.get_default_screen().get_root_window()
            if root:
                pixbuf = Gdk.pixbuf_get_from_window(
                    root,
                    region.x,
                    region.y,
                    region.width,
                    region.height
                )

                if pixbuf:
                    buffer = io.BytesIO()
                    pixbuf.save_to_buffer(buffer, "png")
                    return buffer.getvalue()

        except Exception as e:
            logger.error(f"Region capture failed: {e}")

        return None

    async def capture_active_window(self) -> Optional[bytes]:
        """
        Capture the currently active window.

        Returns:
            PNG image bytes or None on failure
        """
        # This requires integration with AT-SPI to find active window bounds
        # Simplified implementation
        return await self.capture_screen()

    async def ocr(self, image_data: bytes, language: str = "eng+chi_sim") -> List[OCRResult]:
        """
        Perform OCR on image data.

        Args:
            image_data: PNG image bytes
            language: OCR language(s)

        Returns:
            List of OCR results
        """
        if not OCR_AVAILABLE or not PIL_AVAILABLE:
            logger.warning("OCR not available")
            return []

        try:
            # Load image
            image = Image.open(io.BytesIO(image_data))

            # Perform OCR
            data = pytesseract.image_to_data(
                image,
                lang=language,
                output_type=pytesseract.Output.DICT
            )

            # Process results
            results = []
            n_boxes = len(data["text"])

            for i in range(n_boxes):
                text = data["text"][i].strip()
                if not text:
                    continue

                confidence = float(data["conf"][i]) / 100.0  # Normalize to 0-1
                if confidence < 0.1:  # Skip low confidence
                    continue

                bbox = ScreenRegion(
                    x=data["left"][i],
                    y=data["top"][i],
                    width=data["width"][i],
                    height=data["height"][i],
                )

                results.append(OCRResult(
                    text=text,
                    confidence=confidence,
                    bbox=bbox,
                    language=language,
                ))

            return results

        except Exception as e:
            logger.error(f"OCR failed: {e}")
            return []

    async def find_text_on_screen(self, search_text: str) -> List[ScreenRegion]:
        """
        Find text on screen and return its locations.

        Args:
            search_text: Text to search for

        Returns:
            List of regions where text was found
        """
        # Capture screen
        screenshot = await self.capture_screen()
        if not screenshot:
            return []

        # Perform OCR
        ocr_results = await self.ocr(screenshot)

        # Find matching text
        matches = []
        search_lower = search_text.lower()

        for result in ocr_results:
            if search_lower in result.text.lower():
                matches.append(result.bbox)

        return matches

    async def get_text_content(self) -> str:
        """
        Get all visible text on screen.

        Returns:
            Concatenated text from OCR
        """
        screenshot = await self.capture_screen()
        if not screenshot:
            return ""

        ocr_results = await self.ocr(screenshot)
        return " ".join(r.text for r in ocr_results)

    def image_to_base64(self, image_data: bytes) -> str:
        """Convert image bytes to base64 string"""
        return base64.b64encode(image_data).decode("utf-8")

    def base64_to_image(self, base64_str: str) -> bytes:
        """Convert base64 string to image bytes"""
        return base64.b64decode(base64_str.encode("utf-8"))
