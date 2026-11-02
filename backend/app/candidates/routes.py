"""HTTP endpoints. Thin: validate input, call the service, shape the output."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Request, Response, status

from app.candidates.schemas import (
    Candidate,
    CandidateCreate,
    CandidateListItem,
    CandidateUpdate,
    ListQuery,
    NoteCreate,
    StageUpdate,
)
from app.candidates.service import CandidateService

router = APIRouter(prefix="/api")


def get_service(request: Request) -> CandidateService:
    return request.app.state.candidate_service


ServiceDep = Annotated[CandidateService, Depends(get_service)]


def _to_response(doc: dict[str, Any]) -> dict[str, Any]:
    """MongoDB's `_id` (ObjectId) -> the API's `id` (string)."""
    response = {key: value for key, value in doc.items() if key != "_id"}
    response["id"] = str(doc["_id"])
    return response


@router.get("/candidates", response_model=list[CandidateListItem])
def list_candidates(query: Annotated[ListQuery, Query()], service: ServiceDep):
    return [_to_response(doc) for doc in service.list_candidates(query)]


@router.post("/candidates", response_model=Candidate, status_code=status.HTTP_201_CREATED)
def create_candidate(data: CandidateCreate, service: ServiceDep):
    return _to_response(service.create(data))


@router.get("/candidates/{candidate_id}", response_model=Candidate)
def get_candidate(candidate_id: str, service: ServiceDep):
    return _to_response(service.get(candidate_id))


@router.patch("/candidates/{candidate_id}", response_model=Candidate)
def update_candidate(candidate_id: str, data: CandidateUpdate, service: ServiceDep):
    return _to_response(service.update(candidate_id, data))


@router.patch("/candidates/{candidate_id}/stage", response_model=Candidate)
def change_stage(candidate_id: str, data: StageUpdate, service: ServiceDep):
    return _to_response(service.change_stage(candidate_id, data.stage))


@router.post(
    "/candidates/{candidate_id}/notes", response_model=Candidate, status_code=status.HTTP_201_CREATED
)
def add_note(candidate_id: str, data: NoteCreate, service: ServiceDep):
    return _to_response(service.add_note(candidate_id, data.text))


@router.post("/candidates/{candidate_id}/archive", response_model=Candidate)
def archive(candidate_id: str, service: ServiceDep):
    return _to_response(service.archive(candidate_id))


@router.post("/candidates/{candidate_id}/unarchive", response_model=Candidate)
def unarchive(candidate_id: str, service: ServiceDep):
    return _to_response(service.unarchive(candidate_id))


@router.delete("/candidates/{candidate_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_candidate(candidate_id: str, service: ServiceDep):
    service.delete(candidate_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/candidates/{candidate_id}/summary", response_model=Candidate)
def regenerate_summary(candidate_id: str, service: ServiceDep):
    return _to_response(service.regenerate_summary(candidate_id))


@router.get("/roles", response_model=list[str])
def list_roles(service: ServiceDep):
    return service.roles()


@router.get("/health")
def health():
    return {"status": "ok"}
