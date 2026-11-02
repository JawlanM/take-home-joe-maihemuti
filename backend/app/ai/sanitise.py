"""Step 1 of the AI pipeline: clean the input before it goes anywhere near the model.

Pure functions, no I/O, so they're easy to test with the seed's junk and oversized resumes.
"""

import re
import unicodedata
from dataclasses import dataclass

# ~20k characters is roughly 5k tokens: far more than any real resume needs,
# small enough to keep cost and latency predictable (seed case C10 is ~60k).
MAX_INPUT_CHARS = 20_000

# Below this many letters there is nothing worth summarising (seed case C9).
MIN_LETTERS = 20

# Control characters except tab (\x09), newline (\x0a) and carriage return (\x0d).
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
# Our own wrapper tag. Removing it means resume text can't "close" the wrapper
# early and pretend what follows is outside the untrusted section.
_WRAPPER_TAG = re.compile(r"<\s*/?\s*resume\s*>", re.IGNORECASE)
_SPACES = re.compile(r"[ \t]+")
_BLANK_LINES = re.compile(r"\n{3,}")


@dataclass
class CleanedInput:
    text: str           # labelled, combined, capped text that will be sent to the model
    letter_count: int   # letters in the actual resume/cover-letter content (labels excluded)
    truncated: bool


def clean_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _CONTROL_CHARS.sub("", text)
    text = _WRAPPER_TAG.sub("", text)
    text = _SPACES.sub(" ", text)
    text = _BLANK_LINES.sub("\n\n", text)
    return text.strip()


def prepare_input(resume_text: str, cover_letter_text: str) -> CleanedInput:
    """Clean each part, label it, combine, and cap the total length."""
    parts = []
    letters = 0
    for label, raw in (("Resume", resume_text), ("Cover letter", cover_letter_text)):
        cleaned = clean_text(raw)
        if cleaned:
            parts.append(f"{label}:\n{cleaned}")
            letters += sum(ch.isalpha() for ch in cleaned)

    combined = "\n\n".join(parts)
    truncated = len(combined) > MAX_INPUT_CHARS
    return CleanedInput(text=combined[:MAX_INPUT_CHARS], letter_count=letters, truncated=truncated)
