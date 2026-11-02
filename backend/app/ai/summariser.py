"""AI summary module: public entry point.

PLACEHOLDER for build step 1 (backend core). Step 2 replaces this with the real
pipeline: clean -> pre-check -> prompt -> Gemini with schema -> ground.
"""

from datetime import datetime, timezone
from typing import Any


def summarise(resume_text: str, cover_letter_text: str) -> dict[str, Any]:
    return {"status": "disabled", "generated_at": datetime.now(timezone.utc)}
