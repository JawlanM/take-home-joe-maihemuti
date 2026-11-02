"""Request/response shapes for the candidates API, and the Stage enum."""

from datetime import datetime
from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, EmailStr, Field, StringConstraints


class Stage(str, Enum):
    # Declaration order IS the pipeline order; sorting by stage relies on it.
    APPLIED = "Applied"
    SCREENING = "Screening"
    INTERVIEW = "Interview"
    OFFER = "Offer"
    REJECTED = "Rejected"


STAGE_ORDER = {stage: index for index, stage in enumerate(Stage)}

# Reusable field types: whitespace trimmed, length-limited.
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
ShortText = Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)]
# Stored in full (up to 100k chars); the AI module applies its own smaller cap.
LongText = Annotated[str, StringConstraints(max_length=100_000)]
NoteText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=5_000)]


class CandidateCreate(BaseModel):
    name: Name
    email: EmailStr
    phone: ShortText | None = None
    role: Name
    source: ShortText | None = None
    stage: Stage = Stage.APPLIED
    resume_text: LongText = ""
    cover_letter_text: LongText = ""


class CandidateUpdate(BaseModel):
    """Every field optional: only the fields sent are changed. Stage has its own endpoint."""

    name: Name | None = None
    email: EmailStr | None = None
    phone: ShortText | None = None
    role: Name | None = None
    source: ShortText | None = None
    resume_text: LongText | None = None
    cover_letter_text: LongText | None = None


class StageUpdate(BaseModel):
    stage: Stage


class NoteCreate(BaseModel):
    text: NoteText


class Note(BaseModel):
    text: str
    created_at: datetime


class SummaryFlags(BaseModel):
    insufficient_info: bool = False
    suspicious_content: bool = False
    truncated: bool = False


class AISummary(BaseModel):
    status: Literal["ok", "failed", "insufficient_input", "disabled"]
    summary: str | None = None
    skills: list[str] = Field(default_factory=list)
    highlights: list[str] = Field(default_factory=list)
    flags: SummaryFlags = Field(default_factory=SummaryFlags)
    dropped_skills: int = 0
    model: str | None = None
    generated_at: datetime
    error: str | None = None


class CandidateListItem(BaseModel):
    """Lighter shape for the list view: no resume text, notes or summary."""

    id: str
    name: str
    email: str
    role: str
    stage: Stage
    source: str | None
    archived: bool
    created_at: datetime


class Candidate(CandidateListItem):
    phone: str | None
    resume_text: str
    cover_letter_text: str
    notes: list[Note]
    archived_at: datetime | None
    updated_at: datetime
    ai_summary: AISummary | None
