"""AI summary module: the ONE public entry point.

    summarise(resume_text, cover_letter_text) -> dict (matches schemas.AISummary)

Pipeline:
    1. sanitise.prepare_input   clean, label, combine, cap length
    2. pre-check                too little content -> no model call
    3. prompt                   system rules + wrapped untrusted text
    4. gemini.GeminiClient      structured JSON output
    5. validate + ground        parse strictly, drop skills not in the text, cap sizes

Never raises: every failure becomes {"status": "failed", ...} so saving a candidate
can't be broken by the AI. Only resume/cover-letter text is ever sent; the candidate's
name, email and phone fields never reach the model.
"""

import logging
from datetime import UTC, datetime
from functools import lru_cache
from typing import Any, Protocol

from pydantic import ValidationError

from app.ai.gemini import GeminiClient
from app.ai.grounding import MAX_HIGHLIGHTS, cap_items, cap_text, ground_skills
from app.ai.prompt import SYSTEM_INSTRUCTION, ModelOutput, build_user_content
from app.ai.sanitise import MIN_LETTERS, prepare_input
from app.config import settings

logger = logging.getLogger(__name__)


class TextGenerator(Protocol):
    model: str

    def generate(self, system_instruction: str, user_content: str) -> str: ...


@lru_cache
def _default_client() -> TextGenerator:
    return GeminiClient(api_key=settings.gemini_api_key, model=settings.gemini_model)


def _summary_result(status: str, **fields: Any) -> dict[str, Any]:
    return {"status": status, "generated_at": datetime.now(UTC), **fields}


def summarise(
    resume_text: str, cover_letter_text: str, client: TextGenerator | None = None
) -> dict[str, Any]:
    if client is None and not settings.gemini_api_key:
        return _summary_result("disabled", error="No Gemini API key configured")

    # 1. Clean
    cleaned = prepare_input(resume_text, cover_letter_text)
    flags = {"truncated": cleaned.truncated}

    # 2. Pre-check: nothing worth summarising, so don't spend a model call on it
    if cleaned.letter_count < MIN_LETTERS:
        return _summary_result(
            "insufficient_input",
            summary="No readable resume or cover letter text to summarise.",
            flags={**flags, "insufficient_info": True},
        )

    # 3 + 4. Prompt and call the model. Creating the client is inside the try too:
    # a bad key or config must produce "failed", not an exception.
    model_name = client.model if client else settings.gemini_model
    try:
        generator = client or _default_client()
        raw = generator.generate(SYSTEM_INSTRUCTION, build_user_content(cleaned.text))
    except Exception as exc:  # network, timeout, quota, auth, safety block...
        logger.warning("Gemini call failed: %s", exc)
        return _summary_result(
            "failed", model=model_name, flags=flags, error="The AI service could not be reached"
        )

    # 5. Validate strictly, then ground
    try:
        output = ModelOutput.model_validate_json(raw)
    except ValidationError as exc:
        logger.warning("Gemini returned invalid output: %s", exc)
        return _summary_result(
            "failed", model=model_name, flags=flags, error="The AI returned an unusable response"
        )

    skills, dropped = ground_skills(output.skills, cleaned.text)
    return _summary_result(
        "ok",
        summary=cap_text(output.summary),
        skills=skills,
        highlights=cap_items(output.highlights, MAX_HIGHLIGHTS),
        flags={
            **flags,
            "insufficient_info": output.insufficient_info,
            "suspicious_content": output.suspicious_content,
        },
        dropped_skills=dropped,
        model=model_name,
    )
