"""Core rules: filtering, sorting, notes, archive, and when to (re)generate the AI summary.

The service doesn't know how summaries are made. It's given a `summarise` function
(the AI module in production, a fake in tests).
"""

from datetime import datetime, timezone
from typing import Any, Callable, Literal

from app.candidates.repository import CandidateRepository
from app.candidates.schemas import STAGE_ORDER, CandidateCreate, CandidateUpdate, Stage

SummariseFn = Callable[[str, str], dict[str, Any]]


class CandidateNotFound(Exception):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _failed_summary(reason: str) -> dict[str, Any]:
    return {"status": "failed", "generated_at": _now(), "error": reason}


class CandidateService:
    def __init__(self, repo: CandidateRepository, summarise: SummariseFn):
        self.repo = repo
        self._summarise = summarise

    # --- summary -----------------------------------------------------------

    def _make_summary(self, resume_text: str, cover_letter_text: str) -> dict[str, Any]:
        # The AI module is built never to raise, but a failure here must never
        # stop a candidate being saved, so guard anyway.
        try:
            return self._summarise(resume_text, cover_letter_text)
        except Exception:  # noqa: BLE001
            return _failed_summary("Unexpected error while generating summary")

    # --- reads -------------------------------------------------------------

    def list_candidates(
        self,
        stage: Stage | None = None,
        role: str | None = None,
        include_archived: bool = False,
        sort: Literal["created", "stage"] = "created",
        order: Literal["asc", "desc"] = "desc",
    ) -> list[dict[str, Any]]:
        query: dict[str, Any] = {}
        if stage:
            query["stage"] = stage.value
        if role:
            query["role"] = role
        if not include_archived:
            query["archived"] = False

        docs = self.repo.find(query)
        reverse = order == "desc"

        # MongoDB stores times to the millisecond, so two candidates can share a
        # created_at. ObjectIds always increase, so they break the tie.
        def date_added(d):
            return (d["created_at"], d["_id"])

        if sort == "stage":
            # Pipeline order (Applied..Rejected), not alphabetical. Newest first within a stage.
            docs.sort(key=date_added, reverse=True)
            docs.sort(key=lambda d: STAGE_ORDER[Stage(d["stage"])], reverse=reverse)
        else:
            docs.sort(key=date_added, reverse=reverse)
        return docs

    def get(self, candidate_id: str) -> dict[str, Any]:
        doc = self.repo.get(candidate_id)
        if not doc:
            raise CandidateNotFound(candidate_id)
        return doc

    def roles(self) -> list[str]:
        return self.repo.distinct_roles()

    # --- writes ------------------------------------------------------------

    def create(self, data: CandidateCreate) -> dict[str, Any]:
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

    def update(self, candidate_id: str, data: CandidateUpdate) -> dict[str, Any]:
        current = self.get(candidate_id)
        changes = data.model_dump(mode="json", exclude_unset=True)
        # Required fields can be omitted but not cleared.
        for required in ("name", "email", "role"):
            if required in changes and changes[required] is None:
                changes.pop(required)
        for text_field in ("resume_text", "cover_letter_text"):
            if text_field in changes and changes[text_field] is None:
                changes[text_field] = ""

        resume = changes.get("resume_text", current["resume_text"])
        cover = changes.get("cover_letter_text", current["cover_letter_text"])
        text_changed = resume != current["resume_text"] or cover != current["cover_letter_text"]
        if text_changed:
            # Only resume/cover-letter edits cost an AI call; editing a phone number doesn't.
            changes["ai_summary"] = self._make_summary(resume, cover)

        changes["updated_at"] = _now()
        return self.repo.update_fields(candidate_id, changes)

    def change_stage(self, candidate_id: str, stage: Stage) -> dict[str, Any]:
        # No workflow rules: any stage can move to any stage (per the brief).
        return self._update_or_404(candidate_id, {"stage": stage.value, "updated_at": _now()})

    def add_note(self, candidate_id: str, text: str) -> dict[str, Any]:
        now = _now()
        doc = self.repo.push_note(candidate_id, {"text": text, "created_at": now}, updated_at=now)
        if not doc:
            raise CandidateNotFound(candidate_id)
        return doc

    def archive(self, candidate_id: str) -> dict[str, Any]:
        now = _now()
        return self._update_or_404(
            candidate_id, {"archived": True, "archived_at": now, "updated_at": now}
        )

    def unarchive(self, candidate_id: str) -> dict[str, Any]:
        return self._update_or_404(
            candidate_id, {"archived": False, "archived_at": None, "updated_at": _now()}
        )

    def delete(self, candidate_id: str) -> None:
        if not self.repo.delete(candidate_id):
            raise CandidateNotFound(candidate_id)

    def regenerate_summary(self, candidate_id: str) -> dict[str, Any]:
        current = self.get(candidate_id)
        summary = self._make_summary(current["resume_text"], current["cover_letter_text"])
        return self._update_or_404(candidate_id, {"ai_summary": summary, "updated_at": _now()})

    def _update_or_404(self, candidate_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        doc = self.repo.update_fields(candidate_id, fields)
        if not doc:
            raise CandidateNotFound(candidate_id)
        return doc
