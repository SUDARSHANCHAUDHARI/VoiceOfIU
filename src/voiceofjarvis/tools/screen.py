"""Screen reading — screenshot + OCR via pytesseract."""

import logging

log = logging.getLogger(__name__)


def read_screen() -> str | None:
    try:
        import pytesseract
        from PIL import ImageGrab
        img = ImageGrab.grab()
        text = pytesseract.image_to_string(img).strip()
        # Trim to reasonable size
        if len(text) > 1500:
            text = text[:1500] + "..."
        return text or None
    except ImportError:
        log.warning("pytesseract or Pillow not installed — screen reading unavailable")
        return None
    except Exception as e:
        log.warning(f"Screen capture failed: {e}")
        return None
