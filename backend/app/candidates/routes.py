"""HTTP endpoints. Thin: validate input, call the service, shape the output."""

from typing import Any, Literal

from fastapi import APIRouter, Depends, Request, Response, status

from app.candidates.schemas import (
    Candidate,
    CandidateCreate,
    CandidateListItem,
    CandidateUpdate,
    NoteCreate,
    Stage,
    StageUpdate,
)
from app.candidates.service import CandidateService

router = APIRouter(prefix="/api")


def get_service(request: Request) -> CandidateService:
    return request.app.state.candidate_service


def _with_id(doc: dict[str, Any]) -> dict[str, Any]:
    """MongoDB's `_id` (ObjectId) -> API's `id` (string)."""
    out = {k: v for k, v in doc.items() if k != "_id"}
    out["id"] = str(doc["_id"])
    return out


@router.get("/candidates", response_model=list[CandidateListItem])
def list_candidates(
    stage: Stage | None = None,
    role: str | None = None,
    include_archived: bool = False,
    sort: Literal["created", "stage"] = "created",
    order: Literal["asc", "desc"] = "desc",
    service: CandidateService = Depends(get_service),
):
    docs = service.list_candidates(stage=stage, role=role, include_archived=include_archived, sort=sort, order=order)
    return [_with_id(d) for d in docs]


@router.post("/candidates", response_model=Candidate, status_code=status.HTTP_201_CREATED)
def create_candidate(data: CandidateCreate, service: CandidateService = Depends(get_service)):
    return _with_id(service.create(data))


@router.get("/candidates/{candidate_id}", response_model=Candidate)
def get_candidate(candidate_id: str, service: CandidateService = Depends(get_service)):
    return _with_id(service.get(candidate_id))


@router.patch("/candidates/{candidate_id}", response_model=Candidate)
def update_candidate(
    candidate_id: str, data: CandidateUpdate, service: CandidateService = Depends(get_service)
):
    return _with_id(service.update(candidate_id, data))


@router.patch("/candidates/{candidate_id}/stage", response_model=Candidate)
def change_stage(candidate_id: str, data: StageUpdate, service: CandidateService = Depends(get_service)):
    return _with_id(service.change_stage(candidate_id, data.stage))


@router.post("/candidates/{candidate_id}/notes", response_model=Candidate, status_code=status.HTTP_201_CREATED)
def add_note(candidate_id: str, data: NoteCreate, service: CandidateService = Depends(get_service)):
    return _with_id(service.add_note(candidate_id, data.text))


@router.post("/candidates/{candidate_id}/archive", response_model=Candidate)
def archive(candidate_id: str, service: CandidateService = Depends(get_service)):
    return _with_id(service.archive(candidate_id))


@router.post("/candidates/{candidate_id}/unarchive", response_model=Candidate)
def unarchive(candidate_id: str, service: CandidateService = Depends(get_service)):
    return _with_id(service.unarchive(candidate_id))


@router.delete("/candidates/{candidate_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_candidate(candidate_id: str, service: CandidateService = Depends(get_service)):
    service.delete(candidate_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/candidates/{candidate_id}/summary", response_model=Candidate)
def regenerate_summary(candidate_id: str, service: CandidateService = Depends(get_service)):
    return _with_id(service.regenerate_summary(candidate_id))


@router.get("/roles", response_model=list[str])
def list_roles(service: CandidateService = Depends(get_service)):
    return service.roles()


@router.get("/health")
def health():
    return {"status": "ok"}
