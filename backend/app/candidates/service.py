"""Core rules: filtering, sorting, notes, archive, and when to (re)generate the AI summary.

The service doesn't know how summaries are made. It's given a `summarise` function
(the AI module in production, a fake in tests).
"""

import logging
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from app.candidates.repository import CandidateRepository
from app.candidates.schemas import STAGE_ORDER, CandidateCreate, CandidateUpdate, ListQuery, Stage

logger = logging.getLogger(__name__)

SummariseFn = Callable[[str, str], dict[str, Any]]
Doc = dict[str, Any]


class CandidateNotFound(Exception):
    pass


def _now() -> datetime:
    return datetime.now(UTC)


def _date_added(doc: Doc) -> tuple:
    # MongoDB stores times to the millisecond, so two candidates can share a
    # created_at. ObjectIds always increase, so they break the tie.
    return (doc["created_at"], doc["_id"])


def _stage_position(doc: Doc) -> int:
    return STAGE_ORDER[Stage(doc["stage"])]


class CandidateService:
    def __init__(self, repo: CandidateRepository, summarise: SummariseFn):
        self.repo = repo
        self._summarise = summarise

    # --- reads -------------------------------------------------------------

    def list_candidates(self, query: ListQuery) -> list[Doc]:
        mongo_filter: dict[str, Any] = {}
        if query.stage:
            mongo_filter["stage"] = query.stage.value
        if query.role:
            mongo_filter["role"] = query.role
        if query.archived != "all":
            mongo_filter["archived"] = query.archived == "archived"

        docs = self.repo.find(mongo_filter)
        descending = query.order == "desc"
        if query.sort == "stage":
            # Pipeline order (Applied..Rejected), not alphabetical. Newest first within a stage.
            docs.sort(key=_date_added, reverse=True)
            docs.sort(key=_stage_position, reverse=descending)
        else:
            docs.sort(key=_date_added, reverse=descending)
        return docs

    def get(self, candidate_id: str) -> Doc:
        doc = self.repo.get(candidate_id)
        if not doc:
            raise CandidateNotFound(candidate_id)
        return doc

    def roles(self) -> list[str]:
        return self.repo.distinct_roles()

    # --- writes ------------------------------------------------------------

    def create(self, data: CandidateCreate) -> Doc:
        now = _now()
        doc = {
            **data.model_dump(mode="json"),
            "notes": [],
            "archived": False,
            "archived_at": None,
            "created_at": now,
            "updated_at": now,
            "ai_summary": self._make_summary(data.resume_text, data.cover_letter_text),
        }
        return self.repo.insert(doc)

    def update(self, candidate_id: str, data: CandidateUpdate) -> Doc:
        current = self.get(candidate_id)
        changes = data.model_dump(mode="json", exclude_unset=True)

        updated = {**current, **changes}
        resume, cover_letter = updated["resume_text"], updated["cover_letter_text"]
        # Only resume/cover-letter edits cost an AI call; editing a phone number doesn't.
        if (resume, cover_letter) != (current["resume_text"], current["cover_letter_text"]):
            changes["ai_summary"] = self._make_summary(resume, cover_letter)

        changes["updated_at"] = _now()
        return self._update_or_404(candidate_id, changes)

    def change_stage(self, candidate_id: str, stage: Stage) -> Doc:
        # No workflow rules: any stage can move to any stage (per the brief).
        return self._update_or_404(candidate_id, {"stage": stage.value, "updated_at": _now()})

    def add_note(self, candidate_id: str, text: str) -> Doc:
        now = _now()
        doc = self.repo.push_note(candidate_id, {"text": text, "created_at": now}, updated_at=now)
        if not doc:
            raise CandidateNotFound(candidate_id)
        return doc

    def archive(self, candidate_id: str) -> Doc:
        now = _now()
        return self._update_or_404(candidate_id, {"archived": True, "archived_at": now, "updated_at": now})

    def unarchive(self, candidate_id: str) -> Doc:
        return self._update_or_404(
            candidate_id, {"archived": False, "archived_at": None, "updated_at": _now()}
        )

    def delete(self, candidate_id: str) -> None:
        if not self.repo.delete(candidate_id):
            raise CandidateNotFound(candidate_id)

    def regenerate_summary(self, candidate_id: str) -> Doc:
        current = self.get(candidate_id)
        summary = self._make_summary(current["resume_text"], current["cover_letter_text"])
        return self._update_or_404(candidate_id, {"ai_summary": summary, "updated_at": _now()})

    # --- helpers -----------------------------------------------------------

    def _make_summary(self, resume_text: str, cover_letter_text: str) -> Doc:
        # The AI module is built never to raise. This guard is a last line of
        # defence so a summary bug can never stop a candidate being saved; the
        # error is logged, not hidden.
        try:
            return self._summarise(resume_text, cover_letter_text)
        except Exception:
            logger.exception("Summariser raised unexpectedly")
            return {
                "status": "failed",
                "generated_at": _now(),
                "error": "Unexpected error while generating summary",
            }

    def _update_or_404(self, candidate_id: str, fields: Doc) -> Doc:
        doc = self.repo.update_fields(candidate_id, fields)
        if not doc:
            raise CandidateNotFound(candidate_id)
        return doc
