"""Shared fixtures: an in-memory MongoDB (mongomock) and a fake summariser.

No real database or Gemini key is needed to run the tests.
"""

from datetime import datetime, timezone

import mongomock
import pytest
from fastapi.testclient import TestClient

from app.main import create_app


class FakeSummariser:
    """Records every call so tests can assert when the AI was (or wasn't) used."""

    def __init__(self):
        self.calls: list[tuple[str, str]] = []
        self.raise_error = False

    def __call__(self, resume_text: str, cover_letter_text: str) -> dict:
        self.calls.append((resume_text, cover_letter_text))
        if self.raise_error:
            raise RuntimeError("Gemini exploded")
        return {
            "status": "ok",
            "summary": f"Summary of {len(resume_text)} chars",
            "skills": ["Python"],
            "highlights": [],
            "generated_at": datetime.now(timezone.utc),
        }


@pytest.fixture
def summariser():
    return FakeSummariser()


@pytest.fixture
def client(summariser):
    collection = mongomock.MongoClient(tz_aware=True)["test"]["candidates"]
    return TestClient(create_app(collection=collection, summarise=summariser))


@pytest.fixture
def make_candidate(client):
    """POST a candidate with sensible defaults; override any field by keyword."""

    def _make(**overrides):
        body = {
            "name": "Priya Raman",
            "email": "priya@example.com",
            "role": "Graduate Full-Stack Engineer",
            "resume_text": "React and Python developer.",
            **overrides,
        }
        response = client.post("/api/candidates", json=body)
        assert response.status_code == 201, response.text
        return response.json()

    return _make
