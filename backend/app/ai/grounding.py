"""Step 5 of the AI pipeline: check the model's output against the text it was given.

Grounding rule: a skill is kept only if it literally appears in the (cleaned) input.
This catches skills the model invented. It does NOT catch false claims that are copied
from the input itself (e.g. an injected "10 years at Google"); the prompt rules, the
suspicious_content flag and display-only output cover that case.
"""

import re

MAX_SKILLS = 15
MAX_HIGHLIGHTS = 5
MAX_ITEM_CHARS = 200
MAX_SUMMARY_CHARS = 800


def _normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().casefold()


def ground_skills(skills: list[str], source_text: str) -> tuple[list[str], int]:
    """Return (skills found in the source, number dropped). Also de-duplicates."""
    source = _normalise(source_text)
    kept: list[str] = []
    seen: set[str] = set()
    dropped = 0
    for skill in skills:
        key = _normalise(skill)
        if not key or key in seen:
            continue
        if key in source:
            seen.add(key)
            kept.append(skill.strip()[:MAX_ITEM_CHARS])
        else:
            dropped += 1
    return kept[:MAX_SKILLS], dropped


def cap_items(items: list[str], max_items: int) -> list[str]:
    cleaned = [i.strip()[:MAX_ITEM_CHARS] for i in items if i and i.strip()]
    return cleaned[:max_items]


def cap_text(text: str, max_chars: int = MAX_SUMMARY_CHARS) -> str:
    text = text.strip()
    return text if len(text) <= max_chars else text[: max_chars - 1].rstrip() + "…"
