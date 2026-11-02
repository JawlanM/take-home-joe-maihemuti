"""Step 4 of the AI pipeline: the only file that talks to the Gemini SDK (google-genai).

Kept deliberately thin so it can be swapped for a fake in tests, or another provider later.
Returns raw text; parsing and validation happen in summariser.py, where we control them.
"""

from google import genai
from google.genai import types

from app.ai.prompt import ModelOutput


class GeminiClient:
    def __init__(self, api_key: str, model: str, timeout_seconds: float = 30):
        self.model = model
        self._client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(timeout=int(timeout_seconds * 1000)),  # milliseconds
        )

    def generate(self, system_instruction: str, user_content: str) -> str:
        response = self._client.models.generate_content(
            model=self.model,
            contents=user_content,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                # Structured output: Gemini is constrained to this JSON schema.
                response_mime_type="application/json",
                response_schema=ModelOutput,
                temperature=0.2,          # summarising, not creative writing
                max_output_tokens=2048,   # hard cap on response size / cost
                thinking_config=types.ThinkingConfig(thinking_level="low"),
            ),
        )
        return response.text or ""
