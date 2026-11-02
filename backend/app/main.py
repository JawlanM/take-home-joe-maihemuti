"""App factory. Wires the database and the AI summariser into the candidate service."""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pymongo.collection import Collection

from app.ai.summariser import summarise as ai_summarise
from app.candidates.repository import CandidateRepository
from app.candidates.routes import router
from app.candidates.service import CandidateNotFound, CandidateService, SummariseFn
from app.config import settings
from app.db import get_candidates_collection


def create_app(collection: Collection | None = None, summarise: SummariseFn | None = None) -> FastAPI:
    """Tests pass in a mock collection and a fake summariser; production uses the real ones."""
    service = CandidateService(
        CandidateRepository(collection if collection is not None else get_candidates_collection()),
        summarise or ai_summarise,
    )

    app = FastAPI(title="Candidate Tracker API")
    app.state.candidate_service = service

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(CandidateNotFound)
    def not_found(_: Request, exc: CandidateNotFound):
        return JSONResponse(status_code=404, content={"detail": "Candidate not found"})

    app.include_router(router)
    return app
