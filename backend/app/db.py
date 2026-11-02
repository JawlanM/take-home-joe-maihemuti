"""MongoDB connection. The only place a MongoClient is created."""

from typing import Any

from pymongo import MongoClient
from pymongo.collection import Collection

from app.config import settings


def get_candidates_collection() -> Collection:
    # tz_aware=True so datetimes come back as UTC-aware, matching what we store.
    # MongoClient connects lazily, so this doesn't block startup if MongoDB is slow.
    client: MongoClient[dict[str, Any]] = MongoClient(
        settings.mongodb_uri, tz_aware=True, serverSelectionTimeoutMS=5000
    )
    return client[settings.mongodb_db]["candidates"]
