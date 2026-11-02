"""Load the seed candidates into MongoDB.

    python -m seed.load_seed            # add seed candidates (skips emails that already exist)
    python -m seed.load_seed --reset    # delete ALL candidates first, then load

Goes through CandidateService, so each candidate gets a real AI summary
(or "disabled" when no GEMINI_API_KEY is set), exactly as if added in the UI.
"""

import argparse
import json
import time
from datetime import datetime
from pathlib import Path

from app.ai.summariser import summarise
from app.candidates.repository import CandidateRepository
from app.candidates.schemas import CandidateCreate
from app.candidates.service import CandidateService
from app.config import settings
from app.db import get_candidates_collection

SEED_FILE = Path(__file__).with_name("seed.json")


def expand_resume(entry: dict) -> str:
    """C10 is ~60k characters; it's generated here rather than stored in the JSON."""
    text = entry["resume_text"]
    paragraph = entry.get("repeat_paragraph")
    if paragraph:
        while len(text) < entry["repeat_until_chars"]:
            text += paragraph
    return text


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--reset", action="store_true", help="delete all candidates before loading")
    parser.add_argument(
        "--pause",
        type=float,
        default=13.0,
        help="seconds between candidates when AI is on (Gemini free tier allows 5 requests/minute)",
    )
    args = parser.parse_args()

    collection = get_candidates_collection()
    repo = CandidateRepository(collection)
    service = CandidateService(repo, summarise)

    if args.reset:
        deleted = collection.delete_many({}).deleted_count
        print(f"Deleted {deleted} existing candidate(s).")

    pause = args.pause if settings.gemini_api_key else 0
    entries = json.loads(SEED_FILE.read_text(encoding="utf-8"))["candidates"]
    for index, entry in enumerate(entries):
        if index and pause:
            time.sleep(pause)
        if collection.find_one({"email": entry["email"]}):
            print(f"skip  {entry['name']} (already exists)")
            continue
        data = CandidateCreate(
            name=entry["name"],
            email=entry["email"],
            phone=entry["phone"],
            role=entry["role"],
            source=entry["source"],
            stage=entry["stage"],
            resume_text=expand_resume(entry),
            cover_letter_text=entry["cover_letter_text"],
        )
        doc = service.create(data)
        for note in entry["notes"]:
            repo.push_note(
                str(doc["_id"]),
                {"text": note["text"], "created_at": datetime.fromisoformat(note["created_at"])},
                updated_at=doc["updated_at"],
            )
        print(f"added {entry['name']:<15} summary: {doc['ai_summary']['status']}")


if __name__ == "__main__":
    main()
